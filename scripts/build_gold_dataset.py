#!/usr/bin/env python3
"""Assemble gold catalogs into processed JSONL records."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gold_samples import (  # noqa: E402
    api,
    bootstrap,
    database,
    dsa,
    javascript,
    laravel,
    php,
    programming_basic,
    pwd,
    react,
)
from gold_samples.common import BOOKS, PREFIX, SPLIT_QUOTA  # noqa: E402

QUOTAS = {
    "programming_basic": 180,
    "database": 60,
    "javascript": 50,
    "php": 50,
    "react": 40,
    "laravel": 40,
    "api": 30,
    "bootstrap": 25,
    "pwd": 25,
    "dsa": 40,
}

CATALOGS = {
    "programming_basic": programming_basic.samples,
    "database": database.samples,
    "javascript": javascript.samples,
    "php": php.samples,
    "react": react.samples,
    "laravel": laravel.samples,
    "api": api.samples,
    "bootstrap": bootstrap.samples,
    "pwd": pwd.samples,
    "dsa": dsa.samples,
}

CODE_TOKEN_RE = re.compile(r"[A-Za-z_]{3,}")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def ensure_complete_ending(output: str, task: str) -> str:
    text = output.strip()
    if text.endswith("။"):
        return text
    if task == "debug_explain":
        return text + "\n\nဒီလို ပြင်ရင် အမှား ပျောက်ပါတယ်။"
    return text + " ဒီအချက်ကို မှတ်ထားပါ။"


def ensure_code_overlap(output: str, code: str) -> str:
    tokens = []
    seen = set()
    for token in CODE_TOKEN_RE.findall(code):
        key = token.lower()
        if key not in seen:
            seen.add(key)
            tokens.append(token)
    if not tokens:
        return output
    hits = sum(1 for token in tokens if token.lower() in output.lower())
    if hits > 0:
        return output
    shown = ", ".join(tokens[:6])
    return output.rstrip() + f"\n\nဒီ code မှာ {shown} ကို သုံးထားပါတယ်။"


def assign_split(index: int, total: int, test_n: int, val_n: int) -> str:
    test_start = total - test_n
    val_start = test_start - val_n
    if index >= test_start:
        return "test"
    if index >= val_start:
        return "val"
    return "train"


def build_domain(domain: str) -> list[dict]:
    quota = QUOTAS[domain]
    raw = CATALOGS[domain]()[:quota]
    if len(raw) < quota:
        raise ValueError(f"{domain} has {len(raw)} samples, need {quota}")

    book, _author = BOOKS[domain]
    prefix = PREFIX[domain]
    test_n, val_n = SPLIT_QUOTA[domain]
    rows = []
    for index, sample in enumerate(raw):
        output = sample["output"]
        if sample["task_type"] == "explain_code":
            output = ensure_code_overlap(output, sample.get("input", ""))
        output = ensure_complete_ending(output, sample["task_type"])
        code = sample.get("input", "") or ""
        if sample["task_type"] == "concept_qa":
            code = ""
        rows.append(
            {
                "id": f"{prefix}_{index + 1:04d}",
                "task_type": sample["task_type"],
                "domain": domain,
                "instruction": sample["instruction"],
                "input": code,
                "output": output,
                "source_book": book,
                "source_chapter": sample["source_chapter"],
                "terms": sample["terms"],
                "split": assign_split(index, quota, test_n, val_n),
            }
        )
    return rows


def main() -> None:
    all_rows: list[dict] = []
    for domain in QUOTAS:
        all_rows.extend(build_domain(domain))

    train = [row for row in all_rows if row["split"] == "train"]
    val = [row for row in all_rows if row["split"] == "val"]
    test = [row for row in all_rows if row["split"] == "test"]

    gold_dir = ROOT / "data" / "gold"
    proc_dir = ROOT / "data" / "processed"
    write_jsonl(gold_dir / "all.jsonl", all_rows)
    write_jsonl(gold_dir / "train.jsonl", train)
    write_jsonl(gold_dir / "val.jsonl", val)
    write_jsonl(gold_dir / "test.jsonl", test)
    write_jsonl(proc_dir / "all.jsonl", all_rows)
    write_jsonl(proc_dir / "train.jsonl", train)
    write_jsonl(proc_dir / "val.jsonl", val)
    write_jsonl(proc_dir / "test.jsonl", test)

    by_task: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    for row in all_rows:
        by_task[row["task_type"]] = by_task.get(row["task_type"], 0) + 1
        by_domain[row["domain"]] = by_domain.get(row["domain"], 0) + 1

    print(
        f"Gold dataset: train={len(train)} val={len(val)} test={len(test)} total={len(all_rows)}"
    )
    print("domains:", by_domain)
    print("tasks:", by_task)


if __name__ == "__main__":
    main()
