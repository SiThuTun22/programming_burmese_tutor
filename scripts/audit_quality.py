#!/usr/bin/env python3
"""Audit gold-spec failures on processed JSONL records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from terminology_lint import lint_record as terminology_fails

MYANMAR_RE = re.compile(r"[\u1000-\u109F]")

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
TRUNCATED_WORD_RE = re.compile(r"[က-အ]{1,3}\s+ဆိုတာ ဘာလဲ")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def myanmar_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(MYANMAR_RE.findall(text)) / max(len(text.replace(" ", "")), 1)


def sentence_count(text: str) -> int:
    return len(re.findall(r"[။.!?]", text))


def extract_fix_block(output: str) -> str:
    match = re.search(r"မှန်ကန်သော code:\s*(.*)$", output, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def audit_record(row: dict) -> list[str]:
    fails: list[str] = []
    instruction = row.get("instruction", "")
    output = row.get("output", "").strip()
    code = row.get("input", "") or ""
    task = row.get("task_type", "")

    if BROKEN_Q_RE.search(instruction):
        fails.append("broken_question_glue")
    if TRUNCATED_WORD_RE.search(instruction):
        fails.append("truncated_instruction")
    if "လေ့ကျင့်ခန်း" in instruction:
        fails.append("exercise_title_instruction")

    if LEFTOVER_RE.search(output) or LEFTOVER_RE.search(instruction):
        fails.append("book_leftover")

    last_line = output.splitlines()[-1].strip() if output else ""
    if INCOMPLETE_END_RE.search(last_line):
        fails.append("truncated_output")
    if output and not output.endswith(("။", ".", "```", ")")):
        if not output.endswith("`"):
            fails.append("incomplete_ending")

    if sentence_count(output) < 2:
        fails.append("too_few_sentences")
    if myanmar_ratio(output) < 0.12:
        fails.append("low_myanmar_ratio")

    if task in {"explain_code", "debug_explain"} and not code.strip():
        fails.append("missing_code")

    if task == "explain_code" and code.strip():
        tokens = []
        seen: set[str] = set()
        for token in re.findall(r"[A-Za-z_]{3,}", code):
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            tokens.append(token)
        if tokens:
            hits = sum(1 for t in tokens if t.lower() in output.lower())
            if hits == 0:
                fails.append("code_explanation_mismatch")
        if "မှန်ကန်သော code" in output or "ဘာမှားနေလဲ" in output:
            fails.append("debug_leftover_in_explain")

    if task == "concept_qa" and "မှန်ကန်သော code" in output:
        fails.append("debug_leftover_in_concept")
    if "နောက်လာမယ့် အခန်း" in output:
        fails.append("chapter_nav_leftover")

    routing_q = bool(
        re.search(
            r"(route|routing|router|/posts|/hello|web\.php)",
            instruction,
            re.IGNORECASE,
        )
    )
    if "လမ်းကြောင်း" in output and not routing_q:
        fails.append("invented_calque_path")

    ui_calque = bool(re.search(r"UI.{0,20}လျော့ချ|လျော့ချ.{0,20}UI", output))
    if ui_calque and re.search(r"svelte|react", instruction, re.IGNORECASE):
        fails.append("invented_calque_ui")

    if task == "debug_explain":
        fix = extract_fix_block(output)
        if fix and fix.strip() == code.strip():
            fails.append("fake_debug_fix")
        if "မှန်ကန်သော code" not in output:
            fails.append("debug_missing_fix")

    if task == "concept_qa" and code.strip():
        fails.append("concept_has_code")

    fails.extend(terminology_fails(row))

    return fails


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit gold-spec quality failures")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "data" / "processed",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "qc" / "audit_report.json",
    )
    args = parser.parse_args()

    rows: list[dict] = []
    for name in ("train.jsonl", "val.jsonl", "test.jsonl"):
        path = args.input_dir / name
        if path.exists():
            rows.extend(load_jsonl(path))

    fail_counts: Counter[str] = Counter()
    failed_ids: list[dict] = []
    for row in rows:
        fails = audit_record(row)
        if fails:
            fail_counts.update(fails)
            failed_ids.append({"id": row.get("id"), "fails": fails})

    report = {
        "total": len(rows),
        "failed": len(failed_ids),
        "passed": len(rows) - len(failed_ids),
        "fail_rate": round(len(failed_ids) / max(len(rows), 1), 4),
        "fail_counts": dict(fail_counts),
        "failed_ids": failed_ids[:200],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps({k: report[k] for k in ("total", "failed", "passed", "fail_rate", "fail_counts")}, ensure_ascii=False, indent=2))
    print(f"Wrote {args.output}")
    return 1 if failed_ids else 0


if __name__ == "__main__":
    raise SystemExit(main())
