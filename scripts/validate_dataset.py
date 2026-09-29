#!/usr/bin/env python3
"""Validate dataset records against schema and quality rules."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MYANMAR_RE = re.compile(r"[\u1000-\u109F]")
LANG_SUFFIX = "မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ"

VALID_TASK_TYPES = {"concept_qa", "explain_code", "debug_explain"}
VALID_DOMAINS = {
    "programming_basic",
    "database",
    "javascript",
    "php",
    "react",
    "laravel",
    "api",
    "bootstrap",
    "pwd",
    "dsa",
}
VALID_SPLITS = {"train", "val", "test"}

LEFTOVER_RE = re.compile(
    r"(flowchart|flow chart|flow chat|အထက်ပါ|အောက်မှာ ဖော်ပြ|"
    r"discord|telegram|လေ့ကျင့်ခန်း|A\.\s|B\.\s|"
    r"https://discord|https://t\.me)",
    re.IGNORECASE,
)
BROKEN_Q_RE = re.compile(r".{25,}ဆိုတာ ဘာလဲ")
INCOMPLETE_END_RE = re.compile(
    r"(ပြီးလျှင်|ဆိုပြီး|Programming မှာတော့|စသည်ဖြင့်|စသည်တို့|"
    r"အောက်ကလို|အောက်မှာ)$"
)

REQUIRED_FIELDS = [
    "id",
    "task_type",
    "domain",
    "instruction",
    "input",
    "output",
    "source_book",
    "source_chapter",
    "terms",
    "split",
]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no} invalid JSON: {exc}") from exc
    return rows


def myanmar_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(MYANMAR_RE.findall(text)) / max(len(text.replace(" ", "")), 1)


def validate_record(row: dict, seen_ids: set[str]) -> list[str]:
    errors: list[str] = []
    rid = row.get("id", "<missing>")

    for field in REQUIRED_FIELDS:
        if field not in row:
            errors.append(f"{rid}: missing field '{field}'")

    if row.get("id") in seen_ids:
        errors.append(f"{rid}: duplicate id")
    seen_ids.add(row.get("id", ""))

    if row.get("task_type") not in VALID_TASK_TYPES:
        errors.append(f"{rid}: invalid task_type '{row.get('task_type')}'")

    if row.get("domain") not in VALID_DOMAINS:
        errors.append(f"{rid}: invalid domain '{row.get('domain')}'")

    if row.get("split") not in VALID_SPLITS:
        errors.append(f"{rid}: invalid split '{row.get('split')}'")

    instruction = row.get("instruction", "")
    output = row.get("output", "")

    if LANG_SUFFIX not in instruction:
        errors.append(f"{rid}: instruction missing language suffix")

    if len(output) < 80:
        errors.append(f"{rid}: output too short ({len(output)} chars)")

    if myanmar_ratio(output) < 0.10:
        errors.append(f"{rid}: output Myanmar ratio too low ({myanmar_ratio(output):.2f})")

    if row.get("task_type") in {"explain_code", "debug_explain"} and not row.get("input", "").strip():
        errors.append(f"{rid}: code task missing input code")

    if BROKEN_Q_RE.search(instruction):
        errors.append(f"{rid}: instruction looks like a glued book fragment")

    if "လေ့ကျင့်ခန်း" in instruction:
        errors.append(f"{rid}: instruction is an exercise title")

    if LEFTOVER_RE.search(instruction) or LEFTOVER_RE.search(output):
        errors.append(f"{rid}: book leftover text")

    last_line = output.splitlines()[-1].strip() if output else ""
    if INCOMPLETE_END_RE.search(last_line):
        errors.append(f"{rid}: output ends mid-sentence")

    if output and not output.endswith(("။", "```")):
        errors.append(f"{rid}: output must end with ။ or a code fence")

    sentence_count = len(re.findall(r"[။.!?]", output))
    if sentence_count < 2:
        errors.append(f"{rid}: output has fewer than 2 sentences")

    if row.get("task_type") == "debug_explain":
        match = re.search(r"မှန်ကန်သော code:\s*(.*)$", output, re.DOTALL)
        fix = match.group(1).strip() if match else ""
        code = (row.get("input") or "").strip()
        if not match:
            errors.append(f"{rid}: debug output missing corrected code")
        elif fix == code:
            errors.append(f"{rid}: debug fix equals broken input")

    if row.get("task_type") == "concept_qa" and (row.get("input") or "").strip():
        errors.append(f"{rid}: concept_qa must have empty input")

    terms = row.get("terms")
    if not isinstance(terms, list) or not terms:
        errors.append(f"{rid}: terms must be non-empty list")

    return errors


def validate_files(paths: list[Path]) -> int:
    all_errors: list[str] = []
    seen_ids: set[str] = set()
    total = 0

    for path in paths:
        rows = load_jsonl(path)
        total += len(rows)
        for row in rows:
            all_errors.extend(validate_record(row, seen_ids))

    if all_errors:
        print("Validation FAILED:", file=sys.stderr)
        for err in all_errors[:50]:
            print(f"  - {err}", file=sys.stderr)
        if len(all_errors) > 50:
            print(f"  ... and {len(all_errors) - 50} more", file=sys.stderr)
        return 1

    print(f"Validation OK: {total} records across {len(paths)} file(s)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate processed dataset JSONL files")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[
            ROOT / "data" / "processed" / "train.jsonl",
            ROOT / "data" / "processed" / "val.jsonl",
            ROOT / "data" / "processed" / "test.jsonl",
        ],
    )
    args = parser.parse_args()
    sys.exit(validate_files(args.paths))


if __name__ == "__main__":
    main()
