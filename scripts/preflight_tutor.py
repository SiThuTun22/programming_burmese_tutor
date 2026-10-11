#!/usr/bin/env python3
"""Check the Gemini key before starting the tutor app."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

from tutor.config import (
    GEMINI_API_KEY,
    GEMINI_TTS_NAMES_API_KEY,
    HYBRID_CHAT_PROVIDER,
    MIIT_INDEX_PATH,
    MIIT_RETRIEVAL,
    TTS_ENABLED,
    TUTOR_BACKEND,
)


def check_hybrid() -> list[str]:
    errors: list[str] = []
    if HYBRID_CHAT_PROVIDER != "gemini":
        errors.append(
            f"HYBRID_CHAT_PROVIDER={HYBRID_CHAT_PROVIDER!r} is not supported. Use gemini."
        )
    if not GEMINI_API_KEY.strip():
        errors.append("GEMINI_API_KEY is missing. Set it for hybrid chat.")
    return errors


def main() -> int:
    if TUTOR_BACKEND != "hybrid":
        print(
            "preflight: only TUTOR_BACKEND=hybrid is supported.",
            file=sys.stderr,
        )
        return 1

    errors = check_hybrid()
    if errors:
        for msg in errors:
            print(f"preflight: {msg}", file=sys.stderr)
        return 1
    if MIIT_RETRIEVAL == "embed" and not MIIT_INDEX_PATH.is_file():
        print(
            f"preflight: MIIT index missing at {MIIT_INDEX_PATH}. "
            "Run make miit-index.",
            file=sys.stderr,
        )
        return 1
    if TTS_ENABLED and not GEMINI_TTS_NAMES_API_KEY.strip():
        print(
            "preflight: warning: GEMINI_TTS_NAMES_API_KEY is empty. "
            "Q&A uses GEMINI_API_KEY only; unknown English names will not be "
            "rewritten for speech.",
            file=sys.stderr,
        )
    print(f"preflight: OK (backend=hybrid, chat={HYBRID_CHAT_PROVIDER})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
