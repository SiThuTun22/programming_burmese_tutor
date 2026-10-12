from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from langchain_google_genai import ChatGoogleGenerativeAI

from app.ai.errors import LlmUnavailableError
from app.ai.llm import invoke_llm
from tutor.faculty_query import (
    looks_like_research_question,
    matched_faculty_profile,
)

DEFAULT_SESSION_TITLE = 'New chat'
_TITLE_SOURCE_MAX_CHARS = 800
_TITLE_MAX_CHARS = 80

_WHO_PROFILE_HINTS: tuple[str, ...] = (
    'who is',
    "who's",
    'who are',
    'tell me about',
    'about dr',
    'about prof',
    'profile',
    'ဘယ်သူ',
    'ဘယ်လို',
    'ပါမောက္ခ',
    'ဒေါက်တာ',
    'ဒေါ်',
    'ဆရာ',
    'ဆရာမ',
)

_TITLE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            'system',
            'You invent short study-session titles. '
            'Reply with a title of 3 to 6 English words only. '
            'Copy exact person names from the student message; do not change surnames or invent names. '
            'If unsure of a name, use the student wording. '
            'No quotes, no trailing punctuation, no explanation.',
        ),
        (
            'human',
            'Student content:\n{source_text}\n\nTitle:',
        ),
    ]
)


def _truncate_source(source_text: str) -> str:
    trimmed = source_text.strip()
    if len(trimmed) <= _TITLE_SOURCE_MAX_CHARS:
        return trimmed
    truncated = trimmed[:_TITLE_SOURCE_MAX_CHARS]
    return truncated


def _clamp_title(title: str) -> str:
    if len(title) <= _TITLE_MAX_CHARS:
        return title
    return title[:_TITLE_MAX_CHARS].rstrip()


def _canonical_surname(canonical_title: str) -> str:
    parts = canonical_title.split()
    if len(parts) == 0:
        return ''
    return parts[-1].lower()


def looks_like_who_or_profile_question(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    for hint in _WHO_PROFILE_HINTS:
        if hint in lowered or hint in stripped:
            return True
    if looks_like_research_question(stripped):
        return True
    return False


def _first_line_contains_canonical_surname(source_text: str, canonical_title: str) -> bool:
    surname = _canonical_surname(canonical_title)
    if len(surname) == 0:
        return False
    first_line = source_text.strip().splitlines()[0].lower()
    return surname in first_line


def resolve_rule_based_title(source_text: str) -> str | None:
    """Deterministic sidebar title for faculty who/profile asks."""
    stripped = source_text.strip()
    if len(stripped) == 0:
        return None
    profile = matched_faculty_profile(stripped)
    if profile is None:
        return None
    canonical = profile.canonical_title
    if looks_like_who_or_profile_question(stripped):
        return _clamp_title(f'Who is {canonical}')
    if _first_line_contains_canonical_surname(stripped, canonical):
        fallback = fallback_session_title(stripped)
        if fallback != DEFAULT_SESSION_TITLE and _canonical_surname(canonical) in fallback.lower():
            return _clamp_title(fallback)
    return None


def correct_title_with_faculty(title: str, source_text: str) -> str:
    """Fix LLM titles that swap faculty surnames."""
    profile = matched_faculty_profile(source_text)
    if profile is None:
        return title
    canonical = profile.canonical_title
    surname = _canonical_surname(canonical)
    if len(surname) > 0 and surname in title.lower():
        return title
    rule_title = resolve_rule_based_title(source_text)
    if rule_title is not None:
        return rule_title
    return _clamp_title(f'Who is {canonical}')


def fallback_session_title(source_text: str) -> str:
    trimmed = source_text.strip()
    if len(trimmed) == 0:
        return DEFAULT_SESSION_TITLE

    first_line = trimmed.splitlines()[0]
    first_line = first_line.strip()
    if first_line.lower().startswith('uploaded "'):
        without_prefix = first_line[len('uploaded "') :]
        if without_prefix.endswith('"'):
            without_prefix = without_prefix[:-1]
        first_line = without_prefix.strip()

    if len(first_line) == 0:
        return DEFAULT_SESSION_TITLE

    if len(first_line) <= _TITLE_MAX_CHARS:
        return first_line

    shortened = first_line[:_TITLE_MAX_CHARS].rstrip()
    return shortened


def _clean_generated_title(raw_title: str) -> str:
    cleaned = raw_title.strip()
    cleaned = cleaned.strip('"\'')
    cleaned = cleaned.strip()
    if cleaned.endswith('.'):
        cleaned = cleaned[:-1]
        cleaned = cleaned.strip()
    if len(cleaned) == 0:
        return DEFAULT_SESSION_TITLE
    if len(cleaned) > _TITLE_MAX_CHARS:
        cleaned = cleaned[:_TITLE_MAX_CHARS].rstrip()
    return cleaned


async def generate_session_title(source_text: str) -> str:
    truncated_source = _truncate_source(source_text)
    if len(truncated_source) == 0:
        return DEFAULT_SESSION_TITLE

    rule_title = resolve_rule_based_title(truncated_source)
    if rule_title is not None:
        return rule_title

    def make_title_runnable(chat_model: ChatGoogleGenerativeAI):
        output_parser = StrOutputParser()
        title_chain = _TITLE_PROMPT | chat_model | output_parser
        return title_chain

    payload = {
        'source_text': truncated_source,
    }

    try:
        reply = await invoke_llm(make_title_runnable, payload)
    except LlmUnavailableError:
        fallback = fallback_session_title(truncated_source)
        return correct_title_with_faculty(fallback, truncated_source)

    if not isinstance(reply, str):
        fallback = fallback_session_title(truncated_source)
        return correct_title_with_faculty(fallback, truncated_source)

    cleaned = _clean_generated_title(reply)
    if cleaned == DEFAULT_SESSION_TITLE:
        fallback = fallback_session_title(truncated_source)
        return correct_title_with_faculty(fallback, truncated_source)
    return correct_title_with_faculty(cleaned, truncated_source)
