#!/usr/bin/env python3
"""Check Gemini keys and backend prerequisites before starting the tutor app."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

from tutor.config import (
    GEMINI_API_KEY,
    GEMINI_API_KEYS,
    GEMINI_PREFLIGHT_PROBE,
    GEMINI_TTS_NAMES_API_KEY,
    HYBRID_CHAT_PROVIDER,
    MIIT_INDEX_PATH,
    MIIT_RETRIEVAL,
    TTS_ENABLED,
    TUTOR_BACKEND,
)
from tutor.gemini_client import network_error_in_chain, probe_gemini_connectivity
from tutor.gemini_pool import resolved_gemini_api_keys


def check_gemini_keys() -> list[str]:
    errors: list[str] = []
    if HYBRID_CHAT_PROVIDER != "gemini":
        errors.append(
            f"HYBRID_CHAT_PROVIDER={HYBRID_CHAT_PROVIDER!r} is not supported. Use gemini."
        )
    if not GEMINI_API_KEY.strip() and not GEMINI_API_KEYS:
        errors.append("GEMINI_API_KEY or GEMINI_API_KEYS is missing.")
    return errors


def check_hybrid_index() -> list[str]:
    errors: list[str] = []
    if MIIT_RETRIEVAL == "embed" and not MIIT_INDEX_PATH.is_file():
        errors.append(
            f"MIIT index missing at {MIIT_INDEX_PATH}. Run make miit-index."
        )
    return errors


def check_aaa_jwt() -> list[str]:
    from app.lib.config import DEFAULT_JWT_SECRET, get_jwt_secret

    if get_jwt_secret() == DEFAULT_JWT_SECRET:
        return [
            "JWT_SECRET is unset or empty; using dev default. "
            "Set JWT_SECRET in .env before production.",
        ]
    return []


def check_aaa() -> list[str]:
    errors: list[str] = []
    knowledge = ROOT / "knowledge"
    if not knowledge.is_dir():
        errors.append(
            f"AAA knowledge layout missing at {knowledge}. "
            "See docs/WORKFLOW.md (knowledge/ symlinks)."
        )
    return errors


def main() -> int:
    if TUTOR_BACKEND not in ("hybrid", "aaa"):
        print(
            f"preflight: TUTOR_BACKEND={TUTOR_BACKEND!r} is not supported. "
            "Use hybrid or aaa.",
            file=sys.stderr,
        )
        return 1

    errors = check_gemini_keys()
    if TUTOR_BACKEND == "hybrid":
        errors.extend(check_hybrid_index())
    else:
        errors.extend(check_aaa())
        for msg in check_aaa_jwt():
            print(f"preflight: warning: {msg}", file=sys.stderr)

    if errors:
        for msg in errors:
            print(f"preflight: {msg}", file=sys.stderr)
        return 1

    pool_keys = resolved_gemini_api_keys()
    if len(pool_keys) == 1:
        print(
            "preflight: warning: only one Gemini API key in the pool. "
            "Set comma-separated GEMINI_API_KEYS to spread free-tier quota.",
            file=sys.stderr,
        )
    if TTS_ENABLED and not GEMINI_TTS_NAMES_API_KEY.strip() and len(pool_keys) < 2:
        print(
            "preflight: tip: add more keys to GEMINI_API_KEYS so router and TTS "
            "maps share the pool without exhausting one key.",
            file=sys.stderr,
        )
    if GEMINI_PREFLIGHT_PROBE:
        try:
            probe_gemini_connectivity()
        except Exception as exc:
            if network_error_in_chain(exc):
                print(
                    "preflight: cannot reach Google Gemini API (SSL/connect timeout). "
                    "Use a VPN if Google is blocked, check firewall/proxy, and verify "
                    "GEMINI_API_KEYS from Google AI Studio (keys usually start with AIza).",
                    file=sys.stderr,
                )
                return 1
            print(f"preflight: Gemini probe failed: {exc}", file=sys.stderr)
            return 1
    if TUTOR_BACKEND == "aaa":
        print(
            "preflight: OK (backend=aaa). Start Postgres: make db-up; "
            "then make db-migrate && make db-ingest if first run. "
            "Then: make api (port 8001) and make web (http://localhost:5173).",
        )
    else:
        print(f"preflight: OK (backend=hybrid, chat={HYBRID_CHAT_PROVIDER})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
