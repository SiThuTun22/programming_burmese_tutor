#!/usr/bin/env python3
"""Greedy before/after inference on the 50 held-out test prompts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

import torch
from peft import PeftModel

from tutor.config import ADAPTER_PATH, BASE_MODEL, MAX_NEW_TOKENS
from tutor.model import (
    generate_text,
    load_base_model,
    load_tokenizer,
    ready_for_generate,
    require_cuda,
    resolve_model_id,
    setup_inference_env,
)
from tutor.prompts import build_messages_from_row

DEFAULT_TEST = ROOT / "data" / "processed" / "test.jsonl"
DEFAULT_RESULTS = ROOT / "results"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def already_done_ids(out_path: Path) -> set[str]:
    done = set()
    if not out_path.exists():
        return done
    with open(out_path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("prediction", "").strip():
                done.add(row["id"])
    return done


def run_inference(
    model,
    tokenizer,
    test_rows: list[dict],
    label: str,
    out_path: Path,
    max_new_tokens: int,
    resume: bool = False,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = already_done_ids(out_path) if resume else set()
    mode = "a" if resume and out_path.exists() else "w"
    pending = [row for row in test_rows if row["id"] not in done]
    if resume:
        print(f"{label}: skip {len(done)}, run {len(pending)}", flush=True)
    if not pending:
        print(f"{label}: nothing left to generate")
        return
    with open(out_path, mode, encoding="utf-8") as handle:
        for index, row in enumerate(pending, start=1):
            messages = build_messages_from_row(row)
            prediction = generate_text(model, tokenizer, messages, max_new_tokens)
            record = {
                "id": row["id"],
                "model": label,
                "task_type": row.get("task_type", ""),
                "domain": row.get("domain", ""),
                "instruction": row.get("instruction", ""),
                "prompt": messages[0]["content"],
                "reference": row["output"],
                "prediction": prediction,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            print(f"{label} {index}/{len(pending)} {row['id']}", flush=True)
    print(f"Saved {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Base vs LoRA greedy eval")
    parser.add_argument("--test", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--adapter", type=Path, default=ADAPTER_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--max-new-tokens", type=int, default=MAX_NEW_TOKENS)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip prompts that already have a non-empty prediction",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    require_cuda()
    setup_inference_env()
    if not args.adapter.exists():
        print(f"Adapter not found: {args.adapter}", file=sys.stderr)
        raise SystemExit(1)

    model_id = resolve_model_id(args.model)
    test_rows = load_jsonl(args.test)
    tokenizer = load_tokenizer(model_id)
    print("Inference quantization: 4bit")

    base_path = args.results / "predictions_base.jsonl"
    ft_path = args.results / "predictions_finetuned.jsonl"

    if (not args.resume) or (len(already_done_ids(base_path)) < len(test_rows)):
        base_model = ready_for_generate(load_base_model(model_id, "4bit"))
        run_inference(
            base_model,
            tokenizer,
            test_rows,
            "base",
            base_path,
            args.max_new_tokens,
            resume=args.resume,
        )
        del base_model
        torch.cuda.empty_cache()
    else:
        print("base: already complete, skip load")

    if args.resume and len(already_done_ids(ft_path)) >= len(test_rows):
        print("finetuned: already complete, skip load")
        return

    base_model = ready_for_generate(load_base_model(model_id, "4bit"))
    ft_model = PeftModel.from_pretrained(base_model, str(args.adapter))
    ft_model.eval()
    run_inference(
        ft_model,
        tokenizer,
        test_rows,
        "finetuned",
        ft_path,
        args.max_new_tokens,
        resume=args.resume,
    )
    del ft_model, base_model
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
