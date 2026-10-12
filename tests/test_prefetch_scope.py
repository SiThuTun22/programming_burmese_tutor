"""Prefetch scope cleanup for deleted / switched chats."""

from tutor.tts_prefetch import (
    _answer_key,
    _jobs_in_flight,
    _primary_pending,
    sync_prefetch_scope,
)


def test_sync_prefetch_scope_drops_stale_answer() -> None:
    stale = _answer_key("old deleted answer")
    current = _answer_key("still here")
    _jobs_in_flight.add(stale)
    _jobs_in_flight.add(current)
    _primary_pending.add(stale)
    try:
        sync_prefetch_scope([{"question": "q", "answer": "still here"}])
        assert stale not in _jobs_in_flight
        assert stale not in _primary_pending
        assert current in _jobs_in_flight
    finally:
        _jobs_in_flight.discard(current)
        _primary_pending.discard(stale)
        _primary_pending.discard(current)
