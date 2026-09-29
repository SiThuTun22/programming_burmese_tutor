#!/usr/bin/env python3
"""Merge raw candidates, apply QC, assign splits, write processed JSONL."""

from __future__ import annotations

import argparse
import json
import hashlib
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANG_SUFFIX = "မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ"
MYANMAR_RE = re.compile(r"[\u1000-\u109F]")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def myanmar_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(MYANMAR_RE.findall(text)) / max(len(text.replace(" ", "")), 1)


def dedupe_key(row: dict) -> str:
    payload = f"{row.get('instruction','')}|{row.get('input','')}|{row.get('output','')[:200]}"
    return hashlib.md5(payload.encode()).hexdigest()


def normalize_row(row: dict, new_id: str) -> dict:
    instruction = row.get("instruction", "").strip()
    if LANG_SUFFIX not in instruction:
        instruction = f"{instruction} {LANG_SUFFIX}".strip()

    output = row.get("output", "").strip()
    output = re.sub(r"\n{3,}", "\n\n", output)

    return {
        "id": new_id,
        "task_type": row["task_type"],
        "domain": row["domain"],
        "instruction": instruction,
        "input": row.get("input", "") or "",
        "output": output,
        "source_book": row["source_book"],
        "source_chapter": row["source_chapter"],
        "terms": row.get("terms") or ["programming"],
        "split": row.get("split", "train"),
    }


LEFTOVER_RE = re.compile(
    r"(flowchart|flow chart|အထက်ပါ|discord|telegram|လေ့ကျင့်ခန်း)",
    re.IGNORECASE,
)


def quality_score(row: dict) -> float:
    """Score completeness and language — not raw length."""
    score = 0.0
    output = row.get("output", "").strip()
    if myanmar_ratio(output) >= 0.12:
        score += 2.0
    if output.endswith("။"):
        score += 1.0
    if len(re.findall(r"[။.!?]", output)) >= 2:
        score += 1.0
    if LEFTOVER_RE.search(output) or LEFTOVER_RE.search(row.get("instruction", "")):
        score -= 5.0
    if row.get("task_type") == "explain_code" and row.get("input"):
        score += 1.0
    if row.get("task_type") == "debug_explain":
        if "မှန်ကန်သော code" in output:
            fix = output.split("မှန်ကန်သော code:", 1)[-1].strip()
            if fix and fix != (row.get("input") or "").strip():
                score += 1.5
            else:
                score -= 3.0
    return score


def assign_splits(rows: list[dict], test_count: int = 50, val_count: int = 30) -> list[dict]:
    """Assign chapter-level splits with balanced domain representation in test/val."""
    by_domain_chapter: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        key = (row["domain"], row["source_chapter"])
        by_domain_chapter[key].append(row)

    domain_chapters: dict[str, list[str]] = defaultdict(list)
    for domain, chapter in by_domain_chapter:
        if chapter not in domain_chapters[domain]:
            domain_chapters[domain].append(chapter)

    # Mark last chapter per domain as test pool, second-to-last as val pool
    test_chapters: set[tuple[str, str]] = set()
    val_chapters: set[tuple[str, str]] = set()

    for domain, chapters in domain_chapters.items():
        chapters_sorted = sorted(chapters)
        if chapters_sorted:
            test_chapters.add((domain, chapters_sorted[-1]))
        if len(chapters_sorted) >= 2:
            val_chapters.add((domain, chapters_sorted[-2]))

    for row in rows:
        row["split"] = "train"

    # Select best-scoring samples from each domain's held-out chapter(s)
    test_per_domain = max(4, test_count // max(len(domain_chapters), 1))
    val_per_domain = max(2, val_count // max(len(domain_chapters), 1))

    test_selected: list[dict] = []
    val_selected: list[dict] = []

    for domain in sorted(domain_chapters):
        test_pool = []
        for key in test_chapters:
            if key[0] == domain:
                test_pool.extend(by_domain_chapter[key])
        test_pool.sort(key=quality_score, reverse=True)
        test_selected.extend(test_pool[:test_per_domain])

        val_pool = []
        for key in val_chapters:
            if key[0] == domain:
                val_pool.extend(by_domain_chapter[key])
        val_pool.sort(key=quality_score, reverse=True)
        val_selected.extend(val_pool[:val_per_domain])

    # Trim or pad to exact targets without breaking chapter integrity
    test_selected.sort(key=quality_score, reverse=True)
    val_selected.sort(key=quality_score, reverse=True)
    test_selected = test_selected[:test_count]
    val_selected = val_selected[:val_count]

    if len(test_selected) < test_count:
        extra = [r for r in rows if r not in test_selected and r not in val_selected]
        extra.sort(key=quality_score, reverse=True)
        test_selected.extend(extra[: test_count - len(test_selected)])

    if len(val_selected) < val_count:
        extra = [r for r in rows if r not in test_selected and r not in val_selected]
        extra.sort(key=quality_score, reverse=True)
        val_selected.extend(extra[: val_count - len(val_selected)])

    for row in test_selected:
        row["split"] = "test"
    for row in val_selected:
        row["split"] = "val"

    return rows


def cap_by_domain(rows: list[dict], quotas: dict[str, int]) -> list[dict]:
    by_domain: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_domain[row["domain"]].append(row)

    selected: list[dict] = []
    for domain, quota in quotas.items():
        domain_rows = by_domain.get(domain, [])
        domain_rows.sort(key=quality_score, reverse=True)
        selected.extend(domain_rows[:quota])
    return selected


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process raw extraction candidates (v0.1). "
        "v0.2 gold training data is built with scripts/build_gold_dataset.py"
    )
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "processed")
    args = parser.parse_args()

    quotas = {
        "programming_basic": 80,
        "database": 60,
        "javascript": 50,
        "php": 50,
        "react": 40,
        "laravel": 40,
        "api": 30,
        "bootstrap": 25,
        "pwd": 25,
    }

    raw_files = list(args.raw_dir.glob("*candidates*.jsonl"))
    all_rows: list[dict] = []
    for path in raw_files:
        all_rows.extend(load_jsonl(path))

    filtered = []
    seen = set()
    for row in all_rows:
        if row.get("task_type") not in {"concept_qa", "explain_code", "debug_explain"}:
            continue
        output = row.get("output", "")
        if len(output) < 80 or myanmar_ratio(output) < 0.08:
            continue
        key = dedupe_key(row)
        if key in seen:
            continue
        seen.add(key)
        filtered.append(row)

    capped = cap_by_domain(filtered, quotas)

    # Re-index IDs
    domain_counters: dict[str, int] = defaultdict(int)
    prefix_map = {
        "programming_basic": "pb",
        "database": "db",
        "javascript": "js",
        "php": "php",
        "react": "react",
        "laravel": "laravel",
        "api": "api",
        "bootstrap": "bs",
        "pwd": "pwd",
    }
    normalized = []
    for row in capped:
        prefix = prefix_map.get(row["domain"], "x")
        domain_counters[prefix] += 1
        new_id = f"{prefix}_{domain_counters[prefix]:04d}"
        normalized.append(normalize_row(row, new_id))

    normalized = assign_splits(normalized, test_count=50, val_count=30)

    train = [r for r in normalized if r["split"] == "train"]
    val = [r for r in normalized if r["split"] == "val"]
    test = [r for r in normalized if r["split"] == "test"]

    write_jsonl(args.output_dir / "train.jsonl", train)
    write_jsonl(args.output_dir / "val.jsonl", val)
    write_jsonl(args.output_dir / "test.jsonl", test)
    write_jsonl(args.output_dir / "all.jsonl", normalized)

    print(f"Processed dataset: train={len(train)} val={len(val)} test={len(test)} total={len(normalized)}")


if __name__ == "__main__":
    main()
