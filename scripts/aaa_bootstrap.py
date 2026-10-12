#!/usr/bin/env python3
"""Run AAA Alembic migrations and optional knowledge ingest (pgvector)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()


def _migrate() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    print("AAA migrations: head", flush=True)


async def _ingest() -> None:
    from app.knowledge.store import ingest_knowledge

    await ingest_knowledge()
    print("AAA knowledge ingest: done", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="AAA Postgres bootstrap")
    parser.add_argument(
        "action",
        choices=("migrate", "ingest", "all"),
        help="migrate schema, ingest knowledge, or both",
    )
    args = parser.parse_args()
    try:
        if args.action in ("migrate", "all"):
            _migrate()
        if args.action in ("ingest", "all"):
            asyncio.run(_ingest())
    except Exception as exc:
        print(f"aaa_bootstrap failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
