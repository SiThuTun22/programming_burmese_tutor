"""Litestar API tests with a mocked engine (no GPU)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from litestar import Litestar
from litestar.testing import TestClient

from tutor.api import create_app


class _MockEngine:
    def answer(self, question: str, code: str = "") -> str:
        return f"mock:{question}:{code}"


@asynccontextmanager
async def _mock_lifespan(app: Litestar) -> AsyncIterator[None]:
    app.state.engine = _MockEngine()
    yield


def test_health() -> None:
    app = create_app(lifespan_handlers=[_mock_lifespan])
    with TestClient(app=app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "cuda" in body
        assert "adapter" in body


def test_chat() -> None:
    app = create_app(lifespan_handlers=[_mock_lifespan])
    with TestClient(app=app) as client:
        resp = client.post(
            "/v1/chat",
            json={"question": "Hello", "code": "x=1"},
        )
        assert resp.status_code == 201
        assert resp.json()["answer"] == "mock:Hello:x=1"


def test_chat_empty_question() -> None:
    app = create_app(lifespan_handlers=[_mock_lifespan])
    with TestClient(app=app) as client:
        resp = client.post("/v1/chat", json={"question": "   "})
        assert resp.status_code == 400


def test_chat_code_too_long(monkeypatch) -> None:
    monkeypatch.setattr("tutor.config.MAX_CODE_CHARS", 10)
    app = create_app(lifespan_handlers=[_mock_lifespan])
    with TestClient(app=app) as client:
        resp = client.post(
            "/v1/chat",
            json={"question": "Hi", "code": "x" * 20},
        )
        assert resp.status_code == 400


def test_chat_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr("tutor.config.API_KEY", "secret")
    app = create_app(lifespan_handlers=[_mock_lifespan])
    with TestClient(app=app) as client:
        resp = client.post("/v1/chat", json={"question": "Hi"})
        assert resp.status_code == 401


def test_chat_with_api_key(monkeypatch) -> None:
    monkeypatch.setattr("tutor.config.API_KEY", "secret")
    app = create_app(lifespan_handlers=[_mock_lifespan])
    with TestClient(app=app) as client:
        resp = client.post(
            "/v1/chat",
            json={"question": "Hi"},
            headers={"X-API-Key": "secret"},
        )
        assert resp.status_code == 201
        assert resp.json()["answer"] == "mock:Hi:"
