"""Round-robin Gemini API keys with cooldown on 429 (AAA-style)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from tutor.config import (
    GEMINI_API_KEY,
    GEMINI_API_KEY_FALLBACK,
    GEMINI_API_KEYS,
    GEMINI_COOLING_SECONDS,
)


def _split_key_field(raw: str) -> list[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def resolved_gemini_api_keys(
    extra: list[str] | None = None,
) -> list[str]:
    """Same order as AAA: GEMINI_API_KEYS, else GEMINI_API_KEY; plus legacy fallback."""
    if GEMINI_API_KEYS:
        source = list(GEMINI_API_KEYS)
    else:
        source = _split_key_field(GEMINI_API_KEY)
    keys: list[str] = []
    seen: set[str] = set()
    for raw in source + list(extra or []) + _split_key_field(GEMINI_API_KEY_FALLBACK):
        if raw in seen:
            continue
        keys.append(raw)
        seen.add(raw)
    return keys


@dataclass
class _Worker:
    api_key: str
    cooling_until: float = 0.0


class GeminiKeyPool:
    def __init__(
        self,
        keys: list[str] | None = None,
        *,
        cooling_seconds: float | None = None,
    ) -> None:
        resolved = list(keys) if keys is not None else resolved_gemini_api_keys()
        if not resolved:
            raise RuntimeError(
                "GEMINI_API_KEY or GEMINI_API_KEYS is missing. "
                "Set it for Gemini chat or MIIT embeddings."
            )
        self._workers = [_Worker(api_key=key) for key in resolved]
        self._index = 0
        self._lock = threading.Lock()
        self._cooling_seconds = (
            GEMINI_COOLING_SECONDS if cooling_seconds is None else cooling_seconds
        )
        self.primary_key = resolved[0]

    def worker_count(self) -> int:
        return len(self._workers)

    def keys(self) -> list[str]:
        return [worker.api_key for worker in self._workers]

    def acquire(self) -> str:
        now = time.monotonic()
        with self._lock:
            count = len(self._workers)
            for _ in range(count):
                index = self._index % count
                worker = self._workers[index]
                self._index = index + 1
                if worker.cooling_until <= now:
                    return worker.api_key
            soonest = self._workers[0]
            for worker in self._workers:
                if worker.cooling_until < soonest.cooling_until:
                    soonest = worker
            return soonest.api_key

    def mark_cooling(self, api_key: str) -> None:
        until = time.monotonic() + float(self._cooling_seconds)
        with self._lock:
            for worker in self._workers:
                if worker.api_key == api_key:
                    worker.cooling_until = until
                    return


_pool: GeminiKeyPool | None = None
_pool_lock = threading.Lock()


def get_gemini_key_pool() -> GeminiKeyPool:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = GeminiKeyPool()
        return _pool
