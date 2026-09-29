#!/usr/bin/env python3
"""GPU smoke for decode health (no topic-specific fail strings)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.decode import _is_near_duplicate, _split_units
from tutor.env_bootstrap import load_project_env

load_project_env()

from tutor.engine import TutorEngine

QUESTIONS = (
    "Python ဆိုတာ ဘာလဲ?",
    "React ဆိုတာ ဘာလဲ?",
)


def decode_health_fail(answer: str) -> str | None:
    units = _split_units(answer)
    if len(units) > 4:
        return "too many paragraphs"
    for index, unit in enumerate(units):
        if any(_is_near_duplicate(unit, units[prior]) for prior in range(index)):
            return "near-duplicate paragraph"
    last = next((line.strip() for line in reversed(answer.splitlines()) if line.strip()), "")
    if last and not last.endswith(("။", ".", "```", "`")) and "```" not in last:
        return "truncated last line"
    return None


def main() -> int:
    engine = TutorEngine(use_adapter=True)
    try:
        for question in QUESTIONS:
            answer = engine.answer(question)
            paras = [p for p in answer.split("\n\n") if p.strip()]
            print("Q:", question)
            print("N_PARAS:", len(paras))
            print(answer)
            print("---")
            fail = decode_health_fail(answer)
            if fail:
                print(f"FAIL: {fail}", file=sys.stderr)
                return 1
    finally:
        engine.unload()
    print("SPOT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
