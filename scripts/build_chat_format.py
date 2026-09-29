#!/usr/bin/env python3
"""Convert processed JSONL to chat format for SFT training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from tutor.prompts import format_sft_user_content


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def to_chat(row: dict) -> dict:
    user_content = format_sft_user_content(row["instruction"], row.get("input", ""))
    return {
        "id": row["id"],
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": row["output"]},
        ],
    }


def convert_file(input_path: Path, output_path: Path) -> int:
    rows = load_jsonl(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(to_chat(row), ensure_ascii=False) + "\n")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build chat-format JSONL for training")
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "processed" / "chat")
    args = parser.parse_args()

    for split in ("train", "val", "test"):
        count = convert_file(
            args.input_dir / f"{split}.jsonl",
            args.output_dir / f"{split}.jsonl",
        )
        print(f"{split}: {count} chat records")


if __name__ == "__main__":
    main()
