from __future__ import annotations

import base64
import logging

import httpx

from app.ai.errors import LlmUnavailableError
from app.ai.gemini_pool import (
    get_gemini_key_pool,
    is_quota_error,
    should_rotate_pool_key,
)
from app.lib.config import (
    get_gemini_vision_max_tokens,
    get_gemini_vision_model,
    get_gemini_vision_timeout_seconds,
)
from app.services.documents.image_prepare import (
    prepare_image_bytes_for_vision,
    prepare_image_bytes_for_vision_small,
)

_VISION_EXTRACT_PROMPT = (
    'You are a careful academic document and image analyst. '
    'Extract ALL useful information from the provided image(s) in detail. '
    'If this is a graph, chart, diagram, or plot, describe: chart type; axes and units; '
    'important points, curves, or bars; whether curves open upward or downward; '
    'trends, intercepts, peaks, and relationships; and any labels, legends, or titles. '
    'If this is text or mixed content, transcribe important text and explain figures. '
    'If something is unclear or unreadable, say so explicitly. '
    'Write a detailed plain-text description only. Do not tutor the student.'
)

_VISION_DOWN = 'Gemini vision request failed. Check GEMINI_API_KEYS and GEMINI_VISION_MODEL.'
_GENERATE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

logger = logging.getLogger(__name__)


def _encode_image(image_bytes: bytes) -> str:
    encoded = base64.b64encode(image_bytes)
    encoded_text = encoded.decode('ascii')
    return encoded_text


def _text_from_gemini_body(body: object) -> str:
    if not isinstance(body, dict):
        raise LlmUnavailableError('Gemini returned an invalid vision response.')

    candidates = body.get('candidates')
    if not isinstance(candidates, list) or len(candidates) == 0:
        raise LlmUnavailableError('Gemini returned an invalid vision response.')

    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        raise LlmUnavailableError('Gemini returned an invalid vision response.')

    content = first_candidate.get('content')
    if not isinstance(content, dict):
        raise LlmUnavailableError('Gemini returned an invalid vision message.')

    parts = content.get('parts')
    if not isinstance(parts, list) or len(parts) == 0:
        raise LlmUnavailableError('Gemini returned an invalid vision description.')

    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get('text')
        if isinstance(text, str) and len(text.strip()) > 0:
            texts.append(text)

    if len(texts) == 0:
        raise LlmUnavailableError('Gemini returned an empty vision description.')

    joined = '\n'.join(texts)
    trimmed = joined.strip()
    return trimmed


async def _post_vision_request(
    client: httpx.AsyncClient,
    model: str,
    api_key: str,
    image_bytes: bytes,
    max_tokens: int,
) -> str:
    encoded_text = _encode_image(image_bytes)

    prompt_part: dict[str, str] = {}
    prompt_part['text'] = _VISION_EXTRACT_PROMPT

    inline_data: dict[str, str] = {}
    inline_data['mime_type'] = 'image/jpeg'
    inline_data['data'] = encoded_text

    image_part: dict[str, object] = {}
    image_part['inline_data'] = inline_data

    parts: list[object] = []
    parts.append(prompt_part)
    parts.append(image_part)

    content: dict[str, object] = {}
    content['parts'] = parts

    generation_config: dict[str, object] = {}
    generation_config['temperature'] = 0
    generation_config['maxOutputTokens'] = max_tokens

    payload: dict[str, object] = {}
    payload['contents'] = [content]
    payload['generationConfig'] = generation_config

    url_template = _GENERATE_URL
    url = url_template.format(model=model)
    params: dict[str, str] = {}
    params['key'] = api_key

    response = await client.post(url, params=params, json=payload)

    if response.status_code == 429:
        raise LlmUnavailableError(f'{_VISION_DOWN} (429): {response.text}')
    if response.status_code >= 400:
        detail = response.text
        raise LlmUnavailableError(f'{_VISION_DOWN} ({response.status_code}): {detail}')

    try:
        body = response.json()
    except ValueError as error:
        raise LlmUnavailableError('Gemini returned an invalid vision response.') from error

    description = _text_from_gemini_body(body)
    return description


async def _describe_single_image(
    client: httpx.AsyncClient,
    model: str,
    image_bytes: bytes,
    max_tokens: int,
) -> str:
    prepared_bytes = prepare_image_bytes_for_vision(image_bytes)
    pool = get_gemini_key_pool()
    worker_count = pool.worker_count()
    last_error: LlmUnavailableError | None = None
    attempt = 0
    while attempt < worker_count:
        api_key = pool.acquire()
        try:
            description = await _post_vision_request(
                client,
                model,
                api_key,
                prepared_bytes,
                max_tokens,
            )
            return description
        except LlmUnavailableError as error:
            if should_rotate_pool_key(error):
                if is_quota_error(error):
                    pool.mark_cooling(api_key)
                last_error = error
                attempt = attempt + 1
                continue
            error_text = str(error)
            context_too_large = 'exceed_context_size' in error_text or 'context size' in error_text
            context_too_large = context_too_large or 'context_length' in error_text
            if not context_too_large:
                raise
            logger.warning('Vision image exceeded context size; retrying with smaller image.')
            smaller_bytes = prepare_image_bytes_for_vision_small(image_bytes)
            description = await _post_vision_request(
                client,
                model,
                api_key,
                smaller_bytes,
                max_tokens,
            )
            return description
    if last_error is not None:
        raise last_error
    raise LlmUnavailableError(_VISION_DOWN)


async def _describe_image_with_retry(
    client: httpx.AsyncClient,
    model: str,
    image_bytes: bytes,
    max_tokens: int,
) -> str:
    try:
        description = await _describe_single_image(
            client,
            model,
            image_bytes,
            max_tokens,
        )
        return description
    except (httpx.ConnectError, OSError) as error:
        logger.warning('Vision connection failed; retrying once: %s', error)

    try:
        description = await _describe_single_image(
            client,
            model,
            image_bytes,
            max_tokens,
        )
        return description
    except (httpx.ConnectError, OSError) as error:
        cause = str(error)
        message = f'{_VISION_DOWN} {cause}'
        raise LlmUnavailableError(message) from error


async def extract_vision_description(image_bytes_list: list[bytes]) -> str:
    if len(image_bytes_list) == 0:
        return ''

    model = get_gemini_vision_model()
    timeout_seconds = get_gemini_vision_timeout_seconds()
    timeout_value = httpx.Timeout(float(timeout_seconds), connect=10.0)
    max_tokens = get_gemini_vision_max_tokens()

    descriptions: list[str] = []
    last_error: LlmUnavailableError | None = None

    try:
        async with httpx.AsyncClient(timeout=timeout_value) as client:
            image_index = 0
            while image_index < len(image_bytes_list):
                image_bytes = image_bytes_list[image_index]
                if len(image_bytes) > 0:
                    try:
                        description = await _describe_image_with_retry(
                            client,
                            model,
                            image_bytes,
                            max_tokens,
                        )
                        descriptions.append(description)
                    except LlmUnavailableError as error:
                        last_error = error
                        page_number = image_index + 1
                        logger.warning(
                            'Vision skipped for image %s of %s: %s',
                            page_number,
                            len(image_bytes_list),
                            error,
                        )
                image_index = image_index + 1
    except httpx.TimeoutException as error:
        if len(descriptions) > 0:
            logger.warning(
                'Vision timed out after %ss; using %s partial description(s).',
                timeout_seconds,
                len(descriptions),
            )
        else:
            timeout_message = (
                f'Gemini vision timed out after {timeout_seconds}s. '
                'Increase GEMINI_VISION_TIMEOUT_SECONDS.'
            )
            raise LlmUnavailableError(timeout_message) from error
    except (httpx.ConnectError, OSError) as error:
        if len(descriptions) > 0:
            logger.warning(
                'Vision connection failed; using %s partial description(s).',
                len(descriptions),
            )
        else:
            cause = str(error)
            message = f'{_VISION_DOWN} {cause}'
            raise LlmUnavailableError(message) from error

    if len(descriptions) == 0:
        if last_error is not None:
            raise last_error
        return ''

    joined = '\n\n'.join(descriptions)
    return joined
