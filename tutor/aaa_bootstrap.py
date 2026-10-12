"""One-shot AAA DB migrate + knowledge ingest for Gradio startup."""

from __future__ import annotations

import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_ready = False
_failed: str | None = None


def _migrate_sync() -> None:
    """Alembic must run outside a running asyncio loop (env.py uses asyncio.run)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


async def _ingest_async() -> None:
    from app.knowledge.store import ingest_knowledge

    await ingest_knowledge()


def ensure_aaa_ready() -> None:
    """Idempotent; logs and continues on failure (n-gram RAG fallback)."""
    global _ready, _failed
    with _lock:
        if _ready:
            return
        if _failed is not None:
            return
    try:
        _migrate_sync()
        asyncio.run(_ingest_async())
        with _lock:
            _ready = True
    except Exception as exc:
        logger.warning("AAA bootstrap skipped (%s); using file/n-gram fallback.", exc)
        with _lock:
            _failed = str(exc)
