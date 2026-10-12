"""Gemini chat generation (google-genai SDK) with a round-robin key pool."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from typing import TypeVar

import httpx

from tutor.config import (
    CLOUD_MAX_TOKENS,
    GEMINI_EMBED_MODEL,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
    generation_config,
)
from tutor.gemini_pool import GeminiKeyPool, get_gemini_key_pool

logger = logging.getLogger(__name__)
CHAT_FALLBACK_WARNING = "using fallback api key for chatting"
_RETRY_SECONDS_RE = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)
_ALL_KEYS_RATE_LIMITED = "All Gemini API keys are rate-limited."

T = TypeVar("T")

_HTTPX_BY_KEY: dict[str, httpx.Client] = {}


def is_transient_network_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    message = str(exc).lower()
    return (
        "handshake" in message
        or "connecttimeout" in message
        or ("timed out" in message and "ssl" in message)
    )


def network_error_in_chain(exc: BaseException) -> bool:
    if is_transient_network_error(exc):
        return True
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if is_transient_network_error(current):
            return True
        current = current.__cause__ or current.__context__
    return False


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
    message = str(exc).lower()
    return (
        "429" in message
        or "resource_exhausted" in message
        or "resource exhausted" in message
        or "quota" in message
        or "rate limit" in message
        or "too many requests" in message
    )


def is_overloaded_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    if code is not None:
        try:
            status = int(code)
        except (TypeError, ValueError):
            status = None
        if status == 503:
            return True
        if status is not None and 500 <= status < 600 and status != 501:
            return True
    message = str(exc).lower()
    return (
        "503" in message
        or "unavailable" in message
        or "high demand" in message
        or "overloaded" in message
    )


def should_rotate_pool_key(exc: Exception) -> bool:
    return is_quota_error(exc) or is_overloaded_error(exc)


def exception_retry_delay(exc: Exception, attempt: int) -> float | None:
    """Seconds to wait before retry, or None if the error is not retryable."""
    from google.genai.errors import APIError, ClientError

    if network_error_in_chain(exc):
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


def _httpx_client_for_key(api_key: str) -> httpx.Client:
    cached = _HTTPX_BY_KEY.get(api_key)
    if cached is not None:
        return cached
    timeout = float(GEMINI_TIMEOUT_SECONDS)
    created = httpx.Client(timeout=httpx.Timeout(timeout, connect=timeout))
    _HTTPX_BY_KEY[api_key] = created
    return created


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        fallback_api_key: str | None = None,
        generate_model: str | None = None,
        embed_model: str | None = None,
        pool: GeminiKeyPool | None = None,
    ) -> None:
        from google import genai

        if pool is not None:
            self._pool = pool
        elif api_key is not None:
            keys = [api_key.strip()]
            extra = (fallback_api_key or "").strip()
            if extra and extra not in keys:
                keys.append(extra)
            self._pool = GeminiKeyPool(keys)
        else:
            self._pool = get_gemini_key_pool()
        self._genai = genai
        self._clients: dict[str, object] = {}
        self._last_key = self._pool.primary_key
        self.generate_model = generate_model or GEMINI_MODEL
        self.embed_model = embed_model or GEMINI_EMBED_MODEL

    @property
    def using_chat_fallback(self) -> bool:
        return self._last_key != self._pool.primary_key

    def _client_for(self, api_key: str):
        cached = self._clients.get(api_key)
        if cached is not None:
            return cached
        # google-genai HttpOptions.timeout is milliseconds, not seconds.
        timeout_ms = int(GEMINI_TIMEOUT_SECONDS * 1000)
        created = self._genai.Client(
            api_key=api_key,
            http_options={
                "timeout": timeout_ms,
                "httpx_client": _httpx_client_for_key(api_key),
            },
        )
        self._clients[api_key] = created
        return created

    def _call_with_retries(
        self,
        fn: Callable[[], T],
        *,
        max_attempts: int = 12,
        label: str = "request",
        skip_quota_retry: bool = False,
        pool_rotate: bool = False,
    ) -> T:
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                return fn()
            except Exception as exc:
                if skip_quota_retry and is_quota_error(exc):
                    raise
                if pool_rotate and should_rotate_pool_key(exc):
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

    def _call_pooled(self, fn: Callable, *, label: str):
        last_rotate: Exception | None = None
        workers = max(self._pool.worker_count(), 1)
        for _ in range(workers):
            key = self._pool.acquire()
            self._last_key = key
            sdk = self._client_for(key)
            try:
                return self._call_with_retries(
                    lambda client=sdk: fn(client),
                    label=label,
                    skip_quota_retry=True,
                    pool_rotate=True,
                )
            except Exception as exc:
                if should_rotate_pool_key(exc):
                    if is_quota_error(exc):
                        self._pool.mark_cooling(key)
                    last_rotate = exc
                    continue
                raise
        if last_rotate is not None:
            raise RuntimeError(f"{_ALL_KEYS_RATE_LIMITED} ({label})") from last_rotate
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

        return self._call_pooled(_call, label="generate")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _call(sdk_client):
            response = sdk_client.models.embed_content(
                model=self.embed_model,
                contents=texts,
            )
            return embedding_vectors_from_response(response)

        return self._call_pooled(_call, label="embed")


_SHARED_CLIENT: GeminiClient | None = None


def get_shared_gemini_client() -> GeminiClient:
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None:
        _SHARED_CLIENT = GeminiClient()
    return _SHARED_CLIENT


def get_tts_helper_gemini_client() -> GeminiClient:
    """Router / TTS map helpers: optional dedicated key, else shared pool."""
    from tutor.config import GEMINI_TTS_NAMES_API_KEY

    tts_key = GEMINI_TTS_NAMES_API_KEY.strip()
    if tts_key:
        return GeminiClient(api_key=tts_key)
    return get_shared_gemini_client()


def probe_gemini_connectivity() -> None:
    """Raise on unreachable Gemini API (for preflight)."""
    vectors = get_shared_gemini_client().embed(["connectivity probe"])
    if not vectors:
        raise RuntimeError("Gemini embed returned no vectors")
