"""JWT secret from environment."""

from app.lib.config import DEFAULT_JWT_SECRET, get_jwt_secret


def test_jwt_secret_empty_env_uses_default(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "")
    assert get_jwt_secret() == DEFAULT_JWT_SECRET


def test_jwt_secret_whitespace_uses_default(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "   ")
    assert get_jwt_secret() == DEFAULT_JWT_SECRET
