#!/usr/bin/env python3
"""Interactive CLI chat with the Myanmar programming tutor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

import torch

from tutor.config import ADAPTER_PATH, BASE_MODEL, MAX_NEW_TOKENS
from tutor.engine import TutorEngine


def read_optional_code() -> str:
    print("Code (optional): paste lines, then press Enter on an empty line to continue.")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip() and lines:
            break
        if not line.strip() and not lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Myanmar programming tutor CLI")
    parser.add_argument("--base", action="store_true", help="Use base model without LoRA")
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--adapter", type=Path, default=ADAPTER_PATH)
    parser.add_argument("--max-new-tokens", type=int, default=MAX_NEW_TOKENS)
    parser.add_argument("--question", help="Single question (non-interactive)")
    parser.add_argument("--code", default="", help="Optional code for --question")
    parser.add_argument(
        "--code-file",
        type=Path,
        help="Read optional code from a file for --question",
    )
    return parser.parse_args()


def generate_answer(engine: TutorEngine, question: str, code: str) -> str:
    print("Generating answer…", flush=True)
    return engine.answer(question, code)


def main() -> None:
    args = parse_args()
    code_from_file = ""
    if args.code_file:
        code_from_file = args.code_file.read_text(encoding="utf-8")

    try:
        engine = TutorEngine(
            base_model=args.model,
            adapter_path=args.adapter,
            max_new_tokens=args.max_new_tokens,
            use_adapter=not args.base,
        )
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if args.question:
        code = code_from_file or args.code
        print(generate_answer(engine, args.question, code))
        return

    print("Myanmar programming tutor (empty question to quit)")
    while True:
        try:
            question = input("\nQuestion: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            break
        code = read_optional_code()
        try:
            print("\n" + generate_answer(engine, question, code) + "\n")
        except KeyboardInterrupt:
            print("\n(cancelled)\n", flush=True)
            continue
        except torch.OutOfMemoryError:
            print("GPU out of memory.", file=sys.stderr)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
