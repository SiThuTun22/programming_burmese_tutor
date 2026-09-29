#!/usr/bin/env python3
"""One short generation to verify GPU + adapter (skip if unavailable)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

import torch

from tutor.config import ADAPTER_PATH
from tutor.engine import TutorEngine


def main() -> int:
    if not torch.cuda.is_available():
        print("SKIP: no CUDA")
        return 0
    if not ADAPTER_PATH.exists():
        print(f"SKIP: adapter missing at {ADAPTER_PATH}")
        return 0
    try:
        engine = TutorEngine(use_adapter=True, max_new_tokens=64)
        answer = engine.answer("Variable ဆိုတာ ဘာလဲ?")
        engine.unload()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if not answer.strip():
        print("FAIL: empty answer", file=sys.stderr)
        return 1
    print("OK:", answer[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
