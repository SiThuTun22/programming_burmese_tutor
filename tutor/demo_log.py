"""Session log, human scores, and answer language metrics for the demo."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from tutor.config import ROOT

MYANMAR_RE = re.compile(r"[\u1000-\u109F]")
ENGLISH_WORD_RE = re.compile(r"\b[A-Za-z]{4,}\b")
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)

SESSIONS_PATH = ROOT / "results" / "tutor_sessions.jsonl"
SCORES_PATH = ROOT / "results" / "human_scores.jsonl"


def strip_code_blocks(text: str) -> str:
    text = CODE_BLOCK_RE.sub(" ", text)
    return re.sub(r"`[^`]+`", " ", text)


def myanmar_script_ratio(text: str) -> float:
    text = strip_code_blocks(text)
    if not text.strip():
        return 0.0
    myanmar_count = len(MYANMAR_RE.findall(text))
    total = len(re.sub(r"\s+", "", text))
    return myanmar_count / max(total, 1)


def mix_penalty(text: str) -> float:
    """Higher means more English words outside code blocks."""
    text = strip_code_blocks(text)
    english_words = ENGLISH_WORD_RE.findall(text)
    myanmar_chars = len(MYANMAR_RE.findall(text))
    if myanmar_chars == 0:
        return 1.0
    return min(len(english_words) / max(myanmar_chars / 8, 1), 1.0)


def answer_metrics(text: str) -> dict:
    stripped = text.rstrip()
    return {
        "myanmar_script_ratio": round(myanmar_script_ratio(text), 4),
        "mix_penalty": round(mix_penalty(text), 4),
        "ends_with_period": stripped.endswith("။"),
    }


def format_answer_metrics(text: str) -> str:
    metrics = answer_metrics(text)
    ended = "yes" if metrics["ends_with_period"] else "no"
    return (
        f"Myanmar-script ratio: {metrics['myanmar_script_ratio']:.3f}. "
        f"English-mix penalty: {metrics['mix_penalty']:.3f}. "
        f"Ends with ။: {ended}."
    )


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def log_session(
    *,
    turn_id: str,
    question: str,
    code: str,
    answer: str,
    prior_turns: int,
    path: Path | None = None,
) -> dict:
    row = {
        "time": datetime.now(timezone.utc).isoformat(),
        "turn_id": turn_id,
        "question": question,
        "code": code,
        "answer": answer,
        "metrics": answer_metrics(answer),
        "prior_turns": prior_turns,
    }
    append_jsonl(path or SESSIONS_PATH, row)
    return row


def log_human_score(
    *,
    turn_id: str,
    fluency: int,
    correctness: int,
    beginner: int,
    path: Path | None = None,
) -> dict:
    row = {
        "time": datetime.now(timezone.utc).isoformat(),
        "turn_id": turn_id,
        "fluency": fluency,
        "correctness": correctness,
        "beginner": beginner,
    }
    append_jsonl(path or SCORES_PATH, row)
    return row
