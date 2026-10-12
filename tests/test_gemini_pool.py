"""Gemini key pool (no live API)."""

from tutor.gemini_pool import GeminiKeyPool, resolved_gemini_api_keys


def test_round_robin_order() -> None:
    pool = GeminiKeyPool(["a", "b", "c"], cooling_seconds=60)
    assert [pool.acquire() for _ in range(6)] == ["a", "b", "c", "a", "b", "c"]


def test_quota_cools_key_and_skips() -> None:
    pool = GeminiKeyPool(["a", "b"], cooling_seconds=60)
    assert pool.acquire() == "a"
    pool.mark_cooling("a")
    assert pool.acquire() == "b"
    assert pool.acquire() == "b"


def test_resolved_keys_aaa_order(monkeypatch) -> None:
    monkeypatch.setattr("tutor.gemini_pool.GEMINI_API_KEYS", ["k1", "k2"])
    monkeypatch.setattr("tutor.gemini_pool.GEMINI_API_KEY", "legacy")
    monkeypatch.setattr("tutor.gemini_pool.GEMINI_API_KEY_FALLBACK", "fb")
    assert resolved_gemini_api_keys() == ["k1", "k2", "fb"]


def test_resolved_keys_falls_back_to_single_key(monkeypatch) -> None:
    monkeypatch.setattr("tutor.gemini_pool.GEMINI_API_KEYS", [])
    monkeypatch.setattr("tutor.gemini_pool.GEMINI_API_KEY", "only,second")
    monkeypatch.setattr("tutor.gemini_pool.GEMINI_API_KEY_FALLBACK", "")
    assert resolved_gemini_api_keys() == ["only", "second"]


def test_tts_names_key_not_in_pool(monkeypatch) -> None:
    monkeypatch.setattr("tutor.gemini_pool.GEMINI_API_KEYS", ["chat-a"])
    monkeypatch.setattr("tutor.gemini_pool.GEMINI_API_KEY", "")
    monkeypatch.setattr("tutor.gemini_pool.GEMINI_API_KEY_FALLBACK", "")
    keys = resolved_gemini_api_keys()
    assert keys == ["chat-a"]
    assert "tts-only" not in keys
