#!/usr/bin/env python3
"""Batch inference helper for base vs fine-tuned model comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_prompt(row: dict) -> str:
    instruction = row["instruction"]
    code = row.get("input", "").strip()
    if code:
        return f"{instruction}\n\n```\n{code}\n```"
    return instruction


def write_prediction_template(test_path: Path, output_path: Path, model_label: str) -> None:
    """Write prediction file template for manual or notebook fill-in."""
    rows = load_jsonl(test_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            record = {
                "id": row["id"],
                "model": model_label,
                "prompt": build_prompt(row),
                "reference": row["output"],
                "prediction": "",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} prediction templates to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare batch inference templates")
    parser.add_argument("--test", type=Path, default=ROOT / "data" / "processed" / "test.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-label", default="base")
    args = parser.parse_args()
    write_prediction_template(args.test, args.output, args.model_label)


if __name__ == "__main__":
    main()
