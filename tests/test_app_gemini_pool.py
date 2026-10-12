"""AAA app Gemini pool helpers."""

from app.ai.gemini_pool import is_overloaded_error, should_rotate_pool_key


def test_should_rotate_on_503_message() -> None:
    err = RuntimeError(
        "503 UNAVAILABLE. {'error': {'code': 503, 'message': 'high demand'}}"
    )
    assert is_overloaded_error(err)
    assert should_rotate_pool_key(err)


def test_should_rotate_on_429_message() -> None:
    err = RuntimeError("429 RESOURCE_EXHAUSTED quota")
    assert should_rotate_pool_key(err)
