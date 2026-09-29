"""Terminology lint for gold/processed JSONL (v0.4)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LAYOUT_HINTS = (
    "bootstrap",
    "responsive",
    "grid",
    "column",
    "layout",
    "breakpoint",
    "sm",
    "md",
    "lg",
)


def allows_taing_context(row: dict) -> bool:
    meta = " ".join(
        [
            row.get("instruction", ""),
            row.get("domain", ""),
        ]
    ).lower()
    if any(hint in meta for hint in LAYOUT_HINTS):
        return True
    if "တစ်တန်း" in row.get("instruction", "") or "နှစ်တန်း" in row.get("instruction", ""):
        return True
    out = row.get("output", "")
    if "ဖုန်းမှာ တစ်တန်း" in out or "ကွန်ပျူတာမှာ နှစ်တန်း" in out:
        return True
    return False


def lint_record(row: dict) -> list[str]:
    fails: list[str] = []
    output = row.get("output", "")
    if not allows_taing_context(row):
        if "တစ်တန်း" in output or "တစ်တန်းပဲ" in output:
            fails.append("term_taing_misuse")
        if "နှစ်တန်း" in output:
            fails.append("term_hnaing_taing_misuse")
    return fails


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint terminology on processed JSONL")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "data" / "processed",
    )
    args = parser.parse_args()

    rows: list[dict] = []
    for name in ("train.jsonl", "val.jsonl", "test.jsonl"):
        path = args.input_dir / name
        if path.exists():
            rows.extend(load_jsonl(path))

    failed = []
    for row in rows:
        fails = lint_record(row)
        if fails:
            failed.append({"id": row.get("id"), "fails": fails})

    print(f"terminology lint: {len(rows) - len(failed)}/{len(rows)} passed")
    if failed:
        for item in failed[:20]:
            print(item)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
