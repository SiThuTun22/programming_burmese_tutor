"""OpenRouter chat completions (OpenAI-compatible HTTP API)."""

from __future__ import annotations

import time

import httpx

from tutor.config import (
    CLOUD_MAX_TOKENS,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    generation_config,
)
from tutor.gemini_client import exception_retry_delay


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        key = (api_key if api_key is not None else OPENROUTER_API_KEY).strip()
        if not key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is missing. Set it in .env for HYBRID_CHAT_PROVIDER=openrouter."
            )
        self.api_key = key
        self.model = model or OPENROUTER_MODEL
        self.base_url = (base_url or OPENROUTER_BASE_URL).rstrip("/")

    def _messages_to_openai(self, messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for message in messages:
            role = message.get("role", "user")
            if role not in ("user", "assistant", "system"):
                role = "user"
            out.append({"role": role, "content": message.get("content", "")})
        return out

    def generate(
        self,
        messages: list[dict],
        *,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        sampling = generation_config("gemini")
        payload = {
            "model": self.model,
            "messages": self._messages_to_openai(messages),
            "max_tokens": max_new_tokens if max_new_tokens is not None else CLOUD_MAX_TOKENS,
            "temperature": temperature if temperature is not None else sampling["temperature"],
            "top_p": top_p if top_p is not None else sampling["top_p"],
        }
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(12):
            try:
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(url, json=payload, headers=headers)
                if response.status_code == 429 or response.status_code >= 500:
                    exc = httpx.HTTPStatusError(
                        "openrouter error",
                        request=response.request,
                        response=response,
                    )
                    delay = exception_retry_delay(exc, attempt)
                    if delay is None and response.status_code == 429:
                        delay = 50.0
                    if delay is None and response.status_code >= 500:
                        delay = 5.0
                    if delay is None:
                        response.raise_for_status()
                    last_error = exc
                    print(
                        f"openrouter: HTTP {response.status_code}, "
                        f"retry in {delay:.0f}s (attempt {attempt + 1}/12)",
                        flush=True,
                    )
                    time.sleep(delay)
                    continue
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices") or []
                if not choices:
                    raise RuntimeError("OpenRouter returned no choices")
                content = choices[0].get("message", {}).get("content", "")
                if not str(content).strip():
                    raise RuntimeError("OpenRouter returned empty content")
                return str(content).strip()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in (429,) and exc.response.status_code < 500:
                    raise
                delay = exception_retry_delay(exc, attempt) or 5.0
                last_error = exc
                print(
                    f"openrouter: transient error, retry in {delay:.0f}s "
                    f"(attempt {attempt + 1}/12)",
                    flush=True,
                )
                time.sleep(delay)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                delay = exception_retry_delay(exc, attempt)
                if delay is None:
                    raise
                last_error = exc
                print(
                    f"openrouter: network error, retry in {delay:.0f}s "
                    f"(attempt {attempt + 1}/12)",
                    flush=True,
                )
                time.sleep(delay)
        if last_error:
            raise last_error
        raise RuntimeError("OpenRouter request failed without error")
