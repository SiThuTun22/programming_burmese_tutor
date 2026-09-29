#!/usr/bin/env python3
"""QLoRA SFT for the Myanmar programming tutor on this SSH GPU server.

Uses gold chat JSONL. Does not run extractors or process_dataset.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

import matplotlib.pyplot as plt
import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)

from tutor.model import cached_snapshot_path, resolve_model_id
DEFAULT_TRAIN = ROOT / "data" / "processed" / "chat" / "train.jsonl"
DEFAULT_VAL = ROOT / "data" / "processed" / "chat" / "val.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "lora_adapter"
MODEL_NAME = "google/gemma-3-4b-it"
FALLBACK_MODEL_NAME = "unsloth/gemma-3-4b-it"
TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]
LORA_R = 16
LORA_ALPHA = 32
FALLBACK_LORA_R = 16
FALLBACK_LORA_ALPHA = 32


def load_chat_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"No rows in {path}")
    return rows


def require_gpu() -> None:
    if not torch.cuda.is_available():
        print(
            "CUDA is not available. This script will not train on CPU.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    props = torch.cuda.get_device_properties(0)
    print(f"GPU: {props.name}, {props.total_memory / 1024 ** 3:.1f} GB, CC {props.major}.{props.minor}")


def hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")


def resolve_model_name(requested: str) -> str:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import GatedRepoError

    for name in (requested, FALLBACK_MODEL_NAME):
        try:
            hf_hub_download(name, "config.json", token=hf_token())
            if name != requested:
                print(f"{requested} is gated. Using equivalent weights: {name}")
            return name
        except GatedRepoError:
            print(f"No download access for {name}")
            continue
    raise SystemExit(
        "Cannot download Gemma-3-4B. Accept the license at "
        "https://huggingface.co/google/gemma-3-4b-it or set --model to an open copy."
    )


def load_tokenizer(model_name: str) -> AutoTokenizer:
    tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token())
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return tokenizer


def tokenize_completion_only(rows: list[dict], tokenizer, max_length: int) -> Dataset:
    records = []
    skipped = 0
    for row in rows:
        messages = row["messages"]
        if len(messages) < 2:
            skipped += 1
            continue
        full_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
        prompt_text = tokenizer.apply_chat_template(
            messages[:-1],
            tokenize=False,
            add_generation_prompt=True,
        )
        full_ids = tokenizer(
            full_text,
            add_special_tokens=False,
            truncation=True,
            max_length=max_length,
        )["input_ids"]
        prompt_ids = tokenizer(
            prompt_text,
            add_special_tokens=False,
            truncation=True,
            max_length=max_length,
        )["input_ids"]
        prompt_len = min(len(prompt_ids), len(full_ids))
        if prompt_len >= len(full_ids):
            skipped += 1
            continue
        labels = [-100] * prompt_len + full_ids[prompt_len:]
        records.append(
            {
                "input_ids": full_ids,
                "attention_mask": [1] * len(full_ids),
                "labels": labels,
            }
        )
    if not records:
        raise SystemExit("No tokenized training rows. Check chat templates.")
    print(f"Tokenized {len(records)} rows (skipped {skipped})")
    return Dataset.from_list(records)


class CausalCollator:
    def __init__(self, pad_token_id: int):
        self.pad_token_id = pad_token_id

    def __call__(self, features: list[dict]) -> dict:
        max_len = max(len(item["input_ids"]) for item in features)
        batch_input = []
        batch_mask = []
        batch_labels = []
        for item in features:
            pad = max_len - len(item["input_ids"])
            batch_input.append(item["input_ids"] + [self.pad_token_id] * pad)
            batch_mask.append(item["attention_mask"] + [0] * pad)
            batch_labels.append(item["labels"] + [-100] * pad)
        return {
            "input_ids": torch.tensor(batch_input, dtype=torch.long),
            "attention_mask": torch.tensor(batch_mask, dtype=torch.long),
            "labels": torch.tensor(batch_labels, dtype=torch.long),
        }


def bitsandbytes_config(mode: str) -> BitsAndBytesConfig:
    if mode == "4bit":
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    return BitsAndBytesConfig(load_in_8bit=True)


def load_base_model(model_name: str, mode: str):
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    quant = bitsandbytes_config(mode)
    kwargs = {
        "quantization_config": quant,
        "device_map": {"": 0},
        "dtype": torch.float16,
        "attn_implementation": "eager",
    }
    try:
        return AutoModelForCausalLM.from_pretrained(
            model_name, token=hf_token(), **kwargs
        )
    except ValueError:
        raise
    except (OSError, TypeError):
        from transformers import AutoModelForImageTextToText

        return AutoModelForImageTextToText.from_pretrained(
            model_name, token=hf_token(), **kwargs
        )


def attach_lora(model, rank: int, alpha: int):
    model = prepare_model_for_kbit_training(model)
    if hasattr(model, "config"):
        model.config.use_cache = False
    lora = LoraConfig(
        r=rank,
        lora_alpha=alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=TARGET_MODULES,
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()
    return model


def try_load_trainable_model(model_name: str):
    attempts = [
        ("4bit", LORA_R, LORA_ALPHA),
        ("8bit", FALLBACK_LORA_R, FALLBACK_LORA_ALPHA),
    ]
    last_error = None
    for mode, rank, alpha in attempts:
        print(f"Loading {model_name} with {mode} quantization, LoRA r={rank}")
        try:
            model = load_base_model(model_name, mode)
            model = attach_lora(model, rank, alpha)
            print(f"Using {mode} QLoRA/LoRA")
            return model, mode
        except Exception as error:
            last_error = error
            print(f"{mode} load failed: {error}")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    print(
        "4-bit and 8-bit loads both failed. Will not fall back to CPU.",
        file=sys.stderr,
    )
    raise SystemExit(str(last_error))


def plot_loss(log_history: list[dict], plot_path: Path) -> None:
    losses = [row["loss"] for row in log_history if "loss" in row]
    eval_losses = [row["eval_loss"] for row in log_history if "eval_loss" in row]
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4))
    if losses:
        plt.plot(range(len(losses)), losses, label="train")
    if eval_losses:
        plt.plot(range(len(eval_losses)), eval_losses, label="eval")
    plt.title("Training Loss")
    plt.xlabel("Logged step index")
    plt.ylabel("Loss")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {plot_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Server QLoRA SFT")
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--val", type=Path, default=DEFAULT_VAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    has_token = bool(hf_token())
    has_cache = cached_snapshot_path() is not None
    if not has_token and not has_cache:
        print(
            "Set HF_TOKEN or cache unsloth/gemma-3-4b-it under ~/.cache/huggingface/hub",
            file=sys.stderr,
        )
        raise SystemExit(1)
    require_gpu()
    set_seed(args.seed)
    try:
        args.model = resolve_model_id(args.model)
    except RuntimeError:
        args.model = resolve_model_name(args.model)

    tokenizer = load_tokenizer(args.model)
    train_rows = load_chat_jsonl(args.train)
    val_rows = load_chat_jsonl(args.val)
    train_ds = tokenize_completion_only(train_rows, tokenizer, args.max_seq_length)
    val_ds = tokenize_completion_only(val_rows, tokenizer, args.max_seq_length)

    model, mode = try_load_trainable_model(args.model)
    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = args.output.parent / "sft_checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(checkpoint_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=8,
        logging_steps=5,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=2,
        fp16=True,
        bf16=False,
        optim="adamw_bnb_8bit",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to="none",
        seed=args.seed,
        data_seed=args.seed,
        remove_unused_columns=False,
        dataloader_pin_memory=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=CausalCollator(tokenizer.pad_token_id),
        processing_class=tokenizer,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=1)],
    )

    try:
        result = trainer.train()
    except torch.OutOfMemoryError:
        print("Out of memory during training. Stopping. No CPU fallback.", file=sys.stderr)
        raise SystemExit(1)

    trainer.save_model(str(args.output))
    tokenizer.save_pretrained(str(args.output))
    plot_loss(trainer.state.log_history, args.output.parent / "training_loss.png")
    print(result)
    print(f"Quantization mode: {mode}")
    print(f"Saved adapter to {args.output}")


if __name__ == "__main__":
    main()
