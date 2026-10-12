from __future__ import annotations

import logging

import httpx

from app.ai.errors import LlmUnavailableError
from app.ai.gemini_pool import (
    get_gemini_key_pool,
    is_quota_error,
    should_rotate_pool_key,
)
from app.lib.config import (
    get_gemini_embedding_dims,
    get_gemini_embedding_model,
    get_gemini_timeout_seconds,
)

TASK_DOCUMENT = 'RETRIEVAL_DOCUMENT'
TASK_QUERY = 'RETRIEVAL_QUERY'

_EMBED_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent'
_EMBED_DOWN = 'Gemini embedding request failed. Check GEMINI_API_KEYS and GEMINI_EMBEDDING_MODEL.'

logger = logging.getLogger(__name__)


def _values_from_body(body: object) -> list[float]:
    if not isinstance(body, dict):
        raise LlmUnavailableError('Gemini returned an invalid embedding response.')
    embedding = body.get('embedding')
    if not isinstance(embedding, dict):
        raise LlmUnavailableError('Gemini returned an invalid embedding response.')
    values = embedding.get('values')
    if not isinstance(values, list) or len(values) == 0:
        raise LlmUnavailableError('Gemini returned an empty embedding.')
    floats: list[float] = []
    for value in values:
        number = float(value)
        floats.append(number)
    return floats


async def _post_embed(
    client: httpx.AsyncClient,
    api_key: str,
    text: str,
    task_type: str,
) -> list[float]:
    model = get_gemini_embedding_model()
    url_template = _EMBED_URL
    url = url_template.format(model=model)
    headers: dict[str, str] = {}
    headers['x-goog-api-key'] = api_key
    headers['Content-Type'] = 'application/json'

    part: dict[str, str] = {}
    part['text'] = text
    parts: list[dict[str, str]] = []
    parts.append(part)
    content: dict[str, object] = {}
    content['parts'] = parts

    dims = get_gemini_embedding_dims()
    payload: dict[str, object] = {}
    payload['model'] = f'models/{model}'
    payload['content'] = content
    payload['taskType'] = task_type
    payload['output_dimensionality'] = dims

    response = await client.post(url, headers=headers, json=payload)
    if response.status_code == 429:
        raise LlmUnavailableError(f'{_EMBED_DOWN} (429): {response.text}')
    if response.status_code >= 400:
        detail = response.text
        raise LlmUnavailableError(f'{_EMBED_DOWN} ({response.status_code}): {detail}')
    try:
        body = response.json()
    except ValueError as error:
        raise LlmUnavailableError('Gemini returned an invalid embedding response.') from error
    values = _values_from_body(body)
    return values


async def embed_text(text: str, task_type: str) -> list[float]:
    trimmed = text.strip()
    if len(trimmed) == 0:
        raise LlmUnavailableError('Cannot embed empty text.')
    pool = get_gemini_key_pool()
    timeout_seconds = get_gemini_timeout_seconds()
    timeout_value = httpx.Timeout(float(timeout_seconds), connect=10.0)
    worker_count = pool.worker_count()
    last_error: LlmUnavailableError | None = None
    attempt = 0
    async with httpx.AsyncClient(timeout=timeout_value) as client:
        while attempt < worker_count:
            api_key = pool.acquire()
            try:
                values = await _post_embed(client, api_key, trimmed, task_type)
                return values
            except LlmUnavailableError as error:
                if should_rotate_pool_key(error):
                    if is_quota_error(error):
                        pool.mark_cooling(api_key)
                    last_error = error
                    attempt = attempt + 1
                    continue
                raise
    if last_error is not None:
        raise last_error
    raise LlmUnavailableError(_EMBED_DOWN)


def embedding_to_literal(values: list[float]) -> str:
    parts: list[str] = []
    for value in values:
        text = str(value)
        parts.append(text)
    joined = ','.join(parts)
    literal = f'[{joined}]'
    return literal
