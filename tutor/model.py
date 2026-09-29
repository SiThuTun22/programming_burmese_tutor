"""Model load and greedy generation (4-bit Gemma + optional LoRA)."""

from __future__ import annotations

import os
from pathlib import Path

from tutor.env_bootstrap import load_project_env

load_project_env()

import torch
from peft import prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from tutor.config import (
    FALLBACK_BASE_MODEL,
    NO_REPEAT_NGRAM,
    REPETITION_PENALTY,
    inference_device_map,
)
from tutor.decode import collapse_repeated_paragraphs

_VRAM_HINT = (
    " Free GPU memory: stop other tutor jobs (make app, serve-api, chat, train), "
    "then run `fuser -v /dev/nvidia0` and kill stale processes."
)


def hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")


def cached_snapshot_path() -> str | None:
    cached = Path.home() / ".cache/huggingface/hub/models--unsloth--gemma-3-4b-it"
    if not cached.exists():
        return None
    snapshots = list(cached.glob("snapshots/*/config.json"))
    if not snapshots:
        return None
    return str(snapshots[0].parent)


def resolve_model_id(requested: str) -> str:
    if Path(requested).exists():
        return requested
    if hf_token():
        return resolve_model_name_remote(requested)
    snapshot = cached_snapshot_path()
    if snapshot:
        print(f"No HF_TOKEN; using cached weights at {snapshot}")
        return snapshot
    raise RuntimeError(
        "Set HF_TOKEN or ensure unsloth/gemma-3-4b-it is cached under ~/.cache/huggingface/hub"
    )


def resolve_model_name_remote(requested: str) -> str:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import GatedRepoError

    for name in (requested, FALLBACK_BASE_MODEL):
        try:
            hf_hub_download(name, "config.json", token=hf_token())
            if name != requested:
                print(f"{requested} is gated. Using equivalent weights: {name}")
            return name
        except GatedRepoError:
            print(f"No download access for {name}")
            continue
    raise RuntimeError(
        "Cannot download Gemma-3-4B. Accept the license at "
        "https://huggingface.co/google/gemma-3-4b-it or use a cached snapshot."
    )


def bitsandbytes_config(mode: str = "4bit") -> BitsAndBytesConfig:
    if mode == "4bit":
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    return BitsAndBytesConfig(load_in_8bit=True)


def load_base_model(
    model_id: str,
    mode: str = "4bit",
    device_map: str | dict[str, int] | None = None,
):
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    quant = bitsandbytes_config(mode)
    map_spec = device_map if device_map is not None else inference_device_map()
    kwargs = {
        "quantization_config": quant,
        "device_map": map_spec,
        "dtype": torch.float16,
        "attn_implementation": "eager",
    }
    try:
        return AutoModelForCausalLM.from_pretrained(model_id, token=hf_token(), **kwargs)
    except ValueError as exc:
        raise ValueError(f"{exc}{_VRAM_HINT}") from exc
    except (OSError, TypeError):
        from transformers import AutoModelForImageTextToText

        return AutoModelForImageTextToText.from_pretrained(
            model_id, token=hf_token(), **kwargs
        )


def load_tokenizer(model_id: str) -> AutoTokenizer:
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=hf_token())
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def ready_for_generate(model):
    model = prepare_model_for_kbit_training(model)
    if hasattr(model, "gradient_checkpointing_disable"):
        model.gradient_checkpointing_disable()
    if hasattr(model, "config"):
        model.config.use_cache = True
    model.eval()
    return model


def model_device(model) -> torch.device:
    return next(model.parameters()).device


def generate_text(
    model,
    tokenizer,
    messages: list[dict],
    max_new_tokens: int,
) -> str:
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt")
    device = model_device(model)
    inputs = {key: value.to(device) for key, value in inputs.items()}
    prompt_len = inputs["input_ids"].shape[1]
    gen_kwargs: dict = {
        "max_new_tokens": max_new_tokens,
        "do_sample": False,
        "use_cache": True,
        "pad_token_id": tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
        "repetition_penalty": REPETITION_PENALTY,
    }
    if NO_REPEAT_NGRAM > 0:
        gen_kwargs["no_repeat_ngram_size"] = NO_REPEAT_NGRAM
    with torch.no_grad():
        out = model.generate(**inputs, **gen_kwargs)
    new_ids = out[0][prompt_len:]
    raw = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
    return collapse_repeated_paragraphs(raw)


def setup_inference_env() -> None:
    os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
    if torch.cuda.is_available():
        torch._dynamo.config.disable = True


def require_cuda() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available. This tutor requires a GPU.")
