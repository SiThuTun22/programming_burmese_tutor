#!/usr/bin/env python3
"""Generate stub base predictions and oracle finetuned placeholders for pipeline testing.

Replace with real Kaggle inference outputs before final presentation.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BASE_STUBS = {
    "concept_qa": (
        "This concept is used in programming. Variables store data and functions execute logic. "
        "Please refer to documentation for details."
    ),
    "explain_code": (
        "This code defines a function or statement. It runs when executed. "
        "The syntax follows standard programming rules."
    ),
    "debug_explain": (
        "There may be a syntax error in this code. Check quotes, brackets, and semicolons. "
        "Fix the line and run again."
    ),
}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> None:
    test_path = ROOT / "data" / "processed" / "test.jsonl"
    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl(test_path)
    base_out = results_dir / "predictions_base.jsonl"
    ft_out = results_dir / "predictions_finetuned.jsonl"

    with open(base_out, "w", encoding="utf-8") as bf, open(ft_out, "w", encoding="utf-8") as ff:
        for row in rows:
            prompt = row["instruction"]
            if row.get("input", "").strip():
                prompt = f"{prompt}\n\n```\n{row['input']}\n```"

            base_pred = BASE_STUBS.get(row["task_type"], BASE_STUBS["concept_qa"])
            base_record = {
                "id": row["id"],
                "model": "base_stub",
                "prompt": prompt,
                "reference": row["output"],
                "prediction": base_pred,
            }
            bf.write(json.dumps(base_record, ensure_ascii=False) + "\n")

            # Oracle placeholder: gold reference simulates fine-tuned target quality
            ft_record = {
                "id": row["id"],
                "model": "finetuned_oracle_placeholder",
                "prompt": prompt,
                "reference": row["output"],
                "prediction": row["output"],
            }
            ff.write(json.dumps(ft_record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} stub predictions")
    print("NOTE: Replace with real Kaggle inference before final presentation.")


if __name__ == "__main__":
    main()
