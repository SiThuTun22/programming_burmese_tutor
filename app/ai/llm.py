from __future__ import annotations

from collections.abc import Callable

import httpx
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from app.ai.errors import LlmUnavailableError
from app.ai.gemini_pool import (
    get_gemini_key_pool,
    is_quota_error,
    should_rotate_pool_key,
)
from app.lib.config import (
    get_gemini_max_tokens,
    get_gemini_model,
    get_gemini_timeout_seconds,
)

_GEMINI_DOWN = 'Gemini is not reachable. Check GEMINI_API_KEYS.'


def build_chat_model(api_key: str, temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    model = get_gemini_model()
    timeout_seconds = get_gemini_timeout_seconds()
    max_tokens = get_gemini_max_tokens()
    timeout_value = float(timeout_seconds)
    chat_model = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
        max_output_tokens=max_tokens,
        timeout=timeout_value,
        max_retries=0,
    )
    return chat_model


def get_chat_model() -> ChatGoogleGenerativeAI:
    pool = get_gemini_key_pool()
    api_key = pool.acquire()
    chat_model = build_chat_model(api_key)
    return chat_model


async def invoke_llm(
    make_runnable: Callable[[ChatGoogleGenerativeAI], Runnable],
    payload: dict[str, str],
    temperature: float | None = None,
) -> object:
    pool = get_gemini_key_pool()
    timeout_seconds = get_gemini_timeout_seconds()
    worker_count = pool.worker_count()
    last_error: BaseException | None = None
    attempt = 0
    if temperature is None:
        sample_temperature = 0.0
    else:
        sample_temperature = temperature
    while attempt < worker_count:
        api_key = pool.acquire()
        chat_model = build_chat_model(api_key, sample_temperature)
        runnable = make_runnable(chat_model)
        try:
            result = await runnable.ainvoke(payload)
            return result
        except httpx.TimeoutException as error:
            timeout_message = (
                f'Gemini timed out after {timeout_seconds}s. Increase GEMINI_TIMEOUT_SECONDS.'
            )
            raise LlmUnavailableError(timeout_message) from error
        except (httpx.ConnectError, ConnectionError, OSError) as error:
            raise LlmUnavailableError(_GEMINI_DOWN) from error
        except Exception as error:
            if should_rotate_pool_key(error):
                if is_quota_error(error):
                    pool.mark_cooling(api_key)
                last_error = error
                attempt = attempt + 1
                continue
            message = str(error)
            lowered = message.lower()
            if 'connection' in lowered or 'connect' in lowered:
                raise LlmUnavailableError(_GEMINI_DOWN) from error
            raise LlmUnavailableError(f'Gemini request failed: {message}') from error
    if last_error is not None:
        detail = str(last_error)
        raise LlmUnavailableError(
            f'All Gemini API keys failed (quota or overload): {detail}'
        ) from last_error
    raise LlmUnavailableError(_GEMINI_DOWN)


async def invoke_chat(runnable: Runnable, payload: dict[str, str]) -> object:
    result = await invoke_llm(lambda _model: runnable, payload)
    return result
