"""Gemini chat generation (google-genai SDK)."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from typing import TypeVar

import httpx

from tutor.config import (
    CLOUD_MAX_TOKENS,
    GEMINI_API_KEY,
    GEMINI_API_KEY_FALLBACK,
    GEMINI_EMBED_MODEL,
    GEMINI_MODEL,
    generation_config,
)

logger = logging.getLogger(__name__)
CHAT_FALLBACK_WARNING = "using fallback api key for chatting"
_RETRY_SECONDS_RE = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)

T = TypeVar("T")


def warn_chat_fallback() -> None:
    logger.warning(CHAT_FALLBACK_WARNING)
    print(CHAT_FALLBACK_WARNING, flush=True)


def _retry_delay_seconds(exc: Exception) -> float:
    code = getattr(exc, "code", None)
    if code != 429:
        return 0.0
    message = str(exc)
    match = _RETRY_SECONDS_RE.search(message)
    if match:
        return float(match.group(1)) + 1.0
    return 50.0


def is_quota_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    if code == 429:
        return True
    message = str(exc)
    return "429" in message or "RESOURCE_EXHAUSTED" in message


def exception_retry_delay(exc: Exception, attempt: int) -> float | None:
    """Seconds to wait before retry, or None if the error is not retryable."""
    from google.genai.errors import APIError, ClientError

    if isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout)):
        return float(min(2**attempt, 60))

    if isinstance(exc, ClientError) and getattr(exc, "code", None) == 429:
        return _retry_delay_seconds(exc) or 50.0

    if isinstance(exc, APIError):
        code = getattr(exc, "code", None)
        if code is not None and 500 <= int(code) < 600:
            return float(min(5 * (2**attempt), 30))
        return None

    return None


def embedding_vectors_from_response(response: object) -> list[list[float]]:
    """Extract embedding vectors from an EmbedContentResponse."""
    embeddings = getattr(response, "embeddings", None)
    if not embeddings:
        raise RuntimeError("Gemini embed_content returned no embeddings")
    vectors: list[list[float]] = []
    for item in embeddings:
        values = getattr(item, "values", None)
        if values is None and isinstance(item, dict):
            values = item.get("values")
        if not values:
            raise RuntimeError("Gemini embedding entry missing values")
        vectors.append([float(v) for v in values])
    return vectors


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        fallback_api_key: str | None = None,
        generate_model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        key = (api_key if api_key is not None else GEMINI_API_KEY).strip()
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Set it for Gemini chat or MIIT embeddings."
            )
        from google import genai

        self._client = genai.Client(api_key=key)
        raw_fallback = (
            fallback_api_key
            if fallback_api_key is not None
            else GEMINI_API_KEY_FALLBACK
        ).strip()
        self._fallback_client = (
            genai.Client(api_key=raw_fallback)
            if raw_fallback and raw_fallback != key
            else None
        )
        self._chat_use_fallback = False
        self.generate_model = generate_model or GEMINI_MODEL
        self.embed_model = embed_model or GEMINI_EMBED_MODEL

    @property
    def using_chat_fallback(self) -> bool:
        return self._chat_use_fallback

    def _call_with_retries(
        self,
        fn: Callable[[], T],
        *,
        max_attempts: int = 12,
        label: str = "request",
        skip_quota_retry: bool = False,
    ) -> T:
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                return fn()
            except Exception as exc:
                if skip_quota_retry and is_quota_error(exc):
                    raise
                delay = exception_retry_delay(exc, attempt)
                if delay is None:
                    raise
                last_error = exc
                print(
                    f"{label}: transient error ({type(exc).__name__}), "
                    f"retry in {delay:.0f}s (attempt {attempt + 1}/{max_attempts})",
                    flush=True,
                )
                time.sleep(delay)
        if last_error:
            raise last_error
        raise RuntimeError(f"{label} failed without error")

    def generate(
        self,
        messages: list[dict],
        *,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        parts = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            parts.append(f"{role}:\n{content}")
        prompt = "\n\n".join(parts)
        sampling = generation_config("gemini")
        config: dict = {
            "temperature": temperature if temperature is not None else sampling["temperature"],
            "top_p": top_p if top_p is not None else sampling["top_p"],
        }
        limit = max_new_tokens if max_new_tokens is not None else CLOUD_MAX_TOKENS
        if limit:
            config["max_output_tokens"] = limit
        # Disable thinking budget on 2.5 / thinking models so thinking tokens don't eat into output budget
        if "2.5" in self.generate_model or "flash-thinking" in self.generate_model:
            config["thinking_config"] = {"thinking_budget": 0}
        kwargs: dict = {"model": self.generate_model, "contents": prompt}
        if config:
            kwargs["config"] = config

        def _call(sdk_client):
            response = sdk_client.models.generate_content(**kwargs)
            text = getattr(response, "text", None)
            if text:
                return text.strip()
            raise RuntimeError("Gemini generate_content returned empty text")

        if self._fallback_client is not None and not self._chat_use_fallback:
            try:
                return self._call_with_retries(
                    lambda: _call(self._client),
                    label="generate",
                    skip_quota_retry=True,
                )
            except Exception as exc:
                if not is_quota_error(exc):
                    raise
                print(
                    "generate: primary quota exhausted; using GEMINI_API_KEY_FALLBACK",
                    flush=True,
                )
                self._chat_use_fallback = True
                result = self._call_with_retries(
                    lambda: _call(self._fallback_client),
                    label="generate",
                )
                warn_chat_fallback()
                return result
        active = self._fallback_client if self._chat_use_fallback else self._client
        result = self._call_with_retries(lambda: _call(active), label="generate")
        if self._chat_use_fallback:
            warn_chat_fallback()
        return result

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _call():
            response = self._client.models.embed_content(
                model=self.embed_model,
                contents=texts,
            )
            return embedding_vectors_from_response(response)

        return self._call_with_retries(_call, label="embed")
