from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.ai.errors import LlmUnavailableError
from app.lib.config import get_gemini_api_keys, get_gemini_cooling_seconds


@dataclass
class _Worker:
    api_key: str
    cooling_until: float


class GeminiKeyPool:
    def __init__(self) -> None:
        keys = get_gemini_api_keys()
        if len(keys) == 0:
            raise LlmUnavailableError('GEMINI_API_KEYS is not set.')
        workers: list[_Worker] = []
        for key in keys:
            worker = _Worker(api_key=key, cooling_until=0.0)
            workers.append(worker)
        self._workers = workers
        self._index = 0
        self._lock = threading.Lock()

    def worker_count(self) -> int:
        count = len(self._workers)
        return count

    def acquire(self) -> str:
        now = time.monotonic()
        with self._lock:
            count = len(self._workers)
            attempt = 0
            while attempt < count:
                index = self._index % count
                worker = self._workers[index]
                next_index = index + 1
                self._index = next_index
                if worker.cooling_until <= now:
                    return worker.api_key
                attempt = attempt + 1
            soonest = self._workers[0]
            for worker in self._workers:
                if worker.cooling_until < soonest.cooling_until:
                    soonest = worker
            return soonest.api_key

    def mark_cooling(self, api_key: str) -> None:
        now = time.monotonic()
        cooling_seconds = get_gemini_cooling_seconds()
        until = now + cooling_seconds
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
            created = GeminiKeyPool()
            _pool = created
        return _pool


def is_not_found_error(error: BaseException) -> bool:
    message = str(error)
    if '(404)' in message:
        return True
    lowered = message.lower()
    if 'not_found' in lowered:
        return True
    if 'not found' in lowered:
        return True
    return False


def is_quota_error(error: BaseException) -> bool:
    message = str(error)
    lowered = message.lower()
    if '429' in lowered:
        return True
    if 'resource exhausted' in lowered:
        return True
    if 'resourceexhausted' in lowered:
        return True
    if 'quota' in lowered:
        return True
    if 'rate limit' in lowered:
        return True
    if 'rate_limit' in lowered:
        return True
    if 'too many requests' in lowered:
        return True
    return False


def is_overloaded_error(error: BaseException) -> bool:
    code = getattr(error, 'code', None)
    if code is not None:
        try:
            status = int(code)
        except (TypeError, ValueError):
            status = None
        if status == 503:
            return True
        if status is not None and 500 <= status < 600 and status != 501:
            return True
    message = str(error).lower()
    return (
        '503' in message
        or 'unavailable' in message
        or 'high demand' in message
        or 'overloaded' in message
    )


def should_rotate_pool_key(error: BaseException) -> bool:
    return is_quota_error(error) or is_overloaded_error(error)
