"""OpenRouter client (httpx mocked)."""

from __future__ import annotations

import json

import httpx

from tutor.openrouter_client import OpenRouterClient


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json=None, headers=None):
        del url, json, headers
        return self._response


def test_openrouter_generate_ok(monkeypatch) -> None:
    payload = {
        "choices": [{"message": {"content": "ဖြေချက်"}}],
    }
    recorded_payload: dict = {}

    class _CaptureClient(_FakeClient):
        def post(self, url, json=None, headers=None):
            if json:
                recorded_payload.update(json)
            return self._response

    monkeypatch.setattr(httpx, "Client", lambda timeout: _CaptureClient(_FakeResponse(200, payload)))

    client = OpenRouterClient(api_key="sk-test")
    text = client.generate([{"role": "user", "content": "မေး"}])
    assert text == "ဖြေချက်"
    assert recorded_payload.get("max_tokens") == 3072
    assert recorded_payload.get("temperature") == 0.85
    assert recorded_payload.get("top_p") == 0.95


def test_openrouter_missing_key() -> None:
    try:
        OpenRouterClient(api_key="")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "OPENROUTER_API_KEY" in str(exc)
