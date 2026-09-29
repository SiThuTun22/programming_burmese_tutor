#!/usr/bin/env python3
"""Compute automatic evaluation metrics for model predictions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from terminology_lint import lint_record  # noqa: E402

MYANMAR_RE = re.compile(r"[\u1000-\u109F]")
ENGLISH_WORD_RE = re.compile(r"\b[A-Za-z]{4,}\b")
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def strip_code_blocks(text: str) -> str:
    text = CODE_BLOCK_RE.sub(" ", text)
    text = re.sub(r"`[^`]+`", " ", text)
    return text


def myanmar_script_ratio(text: str) -> float:
    text = strip_code_blocks(text)
    if not text.strip():
        return 0.0
    myanmar_count = len(MYANMAR_RE.findall(text))
    total = len(re.sub(r"\s+", "", text))
    return myanmar_count / max(total, 1)


def mix_penalty(text: str) -> float:
    """Higher = more English leakage outside code blocks."""
    text = strip_code_blocks(text)
    english_words = ENGLISH_WORD_RE.findall(text)
    myanmar_chars = len(MYANMAR_RE.findall(text))
    if myanmar_chars == 0:
        return 1.0
    return min(len(english_words) / max(myanmar_chars / 8, 1), 1.0)


def instruction_follow_rate(text: str, threshold: float = 0.25) -> bool:
    return myanmar_script_ratio(text) >= threshold


def heuristic_rubric(text: str, reference: str = "") -> float:
    """Heuristic 1-5 rubric when LLM judge unavailable."""
    score = 1.0
    mr = myanmar_script_ratio(text)
    score += min(mr * 4, 2.0)
    mp = mix_penalty(text)
    score += max(0.0, 1.5 - mp * 2)
    if len(text) >= 120:
        score += 0.5
    if reference:
        ref_terms = set(re.findall(r"[\u1000-\u109F]{2,}", reference))
        out_terms = set(re.findall(r"[\u1000-\u109F]{2,}", text))
        overlap = len(ref_terms & out_terms) / max(len(ref_terms), 1)
        score += overlap * 1.0
    return min(max(score, 1.0), 5.0)


def evaluate_predictions(rows: list[dict]) -> dict:
    if not rows:
        return {}

    ratios = []
    penalties = []
    rubrics = []
    follow = 0

    for row in rows:
        pred = row.get("prediction", row.get("output", ""))
        ref = row.get("reference", row.get("gold", ""))
        ratios.append(myanmar_script_ratio(pred))
        penalties.append(mix_penalty(pred))
        rubrics.append(heuristic_rubric(pred, ref))
        if instruction_follow_rate(pred):
            follow += 1

    taing_misuse = 0
    explain_code_taing = 0
    explain_code_n = 0
    for row in rows:
        pred = row.get("prediction", row.get("output", ""))
        lint_row = {
            "instruction": row.get("instruction", ""),
            "domain": row.get("domain", ""),
            "output": pred,
        }
        if lint_record(lint_row):
            taing_misuse += 1
        if row.get("task_type") == "explain_code":
            explain_code_n += 1
            if lint_record(lint_row):
                explain_code_taing += 1

    n = len(rows)
    out = {
        "count": n,
        "myanmar_script_ratio": round(sum(ratios) / n, 4),
        "mix_penalty": round(sum(penalties) / n, 4),
        "heuristic_rubric_1_5": round(sum(rubrics) / n, 4),
        "instruction_follow_rate": round(follow / n, 4),
        "term_taing_misuse_count": taing_misuse,
    }
    if explain_code_n:
        out["explain_code_count"] = explain_code_n
        out["explain_code_term_taing_misuse_count"] = explain_code_taing
    return out


def compare(base_metrics: dict, ft_metrics: dict) -> dict:
    delta = {}
    for key in ("myanmar_script_ratio", "heuristic_rubric_1_5", "instruction_follow_rate"):
        if key in base_metrics and key in ft_metrics:
            delta[f"delta_{key}"] = round(ft_metrics[key] - base_metrics[key], 4)
    if "mix_penalty" in base_metrics and "mix_penalty" in ft_metrics:
        delta["delta_mix_penalty"] = round(ft_metrics["mix_penalty"] - base_metrics["mix_penalty"], 4)
    return delta


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate prediction JSONL files")
    parser.add_argument("--base", type=Path, default=ROOT / "results" / "predictions_base.jsonl")
    parser.add_argument("--finetuned", type=Path, default=ROOT / "results" / "predictions_finetuned.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "metrics_summary.json")
    args = parser.parse_args()

    summary = {}
    if args.base.exists():
        summary["base"] = evaluate_predictions(load_jsonl(args.base))
    if args.finetuned.exists():
        summary["finetuned"] = evaluate_predictions(load_jsonl(args.finetuned))
    if "base" in summary and "finetuned" in summary:
        summary["delta"] = compare(summary["base"], summary["finetuned"])

    summary["status"] = "real_ssh_eval"
    summary["note"] = (
        "Greedy inference on 50 held-out test prompts; finetuned adapter with inference guide in SFT user turns (LoRA r=16). "
        "term_taing_misuse_count uses terminology_lint on predictions (layout-only တစ်တန်း rule)."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
