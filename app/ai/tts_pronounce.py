from __future__ import annotations

import enum
import json
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.ai.errors import LlmUnavailableError
from app.ai.llm import invoke_llm
from app.lib.config import get_knowledge_dir

logger = logging.getLogger(__name__)

_HONORIFICS = {
    'Dr',
    'Dr.',
    'Prof',
    'Prof.',
    'Mr',
    'Mr.',
    'Mrs',
    'Mrs.',
    'Ms',
    'Ms.',
}
_TITLE_WORDS = {
    'Dr',
    'Prof',
    'Mr',
    'Mrs',
    'Ms',
}


class PronunciationKind(enum.StrEnum):
    HONORIFIC = 'honorific'
    PERSON_NAME = 'person_name'


PRONOUNCE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            'system',
            'Build a pronunciation map for Myanmar TTS. '
            'Each entry must have kind honorific or person_name. '
            'honorific: only Dr, Dr., Prof, Prof., Mr, Mr., Mrs, Mrs., Ms, Ms. '
            '(example: Dr -> ဒေါက်တာ). '
            'person_name: only people names from the known faculty name list '
            '(example: Aye Aye Thant -> အေးအေးသန့်). '
            'Do not map research titles, course names, paper titles, systems, orgs, or other English. '
            'Do not repeat keys already listed. '
            'Do not map pure Myanmar text. '
            'If nothing new is needed, return an empty entries list.',
        ),
        (
            'human',
            'Known faculty names (JSON array):\n{known_names}\n\n'
            'Existing keys (JSON array):\n{existing_keys}\n\n'
            'Text to speak:\n{spoken_text}',
        ),
    ]
)


class PronunciationEntry(BaseModel):
    source: str = Field(description='Person name or short honorific as it appears in the text')
    spoken: str = Field(description='Myanmar-script pronunciation for TTS')
    kind: PronunciationKind = Field(description='honorific or person_name')


class PronunciationMap(BaseModel):
    entries: list[PronunciationEntry] = Field(description='New pronunciation mappings only')


def _name_from_stem(stem: str) -> str:
    parts = stem.split('_')
    words: list[str] = []
    for part in parts:
        if len(part) == 0:
            continue
        titled = part.capitalize()
        words.append(titled)
    joined = ' '.join(words)
    return joined


def _bare_person_name(source: str) -> str:
    trimmed = source.strip()
    words = trimmed.split()
    if len(words) == 0:
        return ''
    first = words[0]
    first_bare = first.rstrip('.')
    if first_bare in _TITLE_WORDS:
        rest = words[1:]
        joined = ' '.join(rest)
        return joined
    return trimmed


def list_known_faculty_names() -> list[str]:
    knowledge_dir = get_knowledge_dir()
    faculty_dir = knowledge_dir / 'faculty'
    names: list[str] = []
    seen: set[str] = set()
    if not faculty_dir.is_dir():
        return names
    for path in faculty_dir.iterdir():
        if path.suffix != '.jsonl':
            continue
        if path.name.startswith('_'):
            continue
        from_stem = _name_from_stem(path.stem)
        from_stem_key = from_stem.casefold()
        if from_stem_key not in seen and len(from_stem) > 0:
            names.append(from_stem)
            seen.add(from_stem_key)
        try:
            raw = path.read_text(encoding='utf-8')
        except OSError:
            continue
        lines = raw.splitlines()
        for line in lines:
            stripped = line.strip()
            if len(stripped) == 0:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            name_value = payload.get('name')
            if not isinstance(name_value, str):
                continue
            name_stripped = name_value.strip()
            name_key = name_stripped.casefold()
            if len(name_stripped) == 0 or name_key in seen:
                continue
            names.append(name_stripped)
            seen.add(name_key)
    return names


def is_known_person_name(source: str) -> bool:
    stripped = source.strip()
    if '@' in stripped:
        return False
    compact = stripped.replace('.', '')
    compact = compact.replace(' ', '')
    compact = compact.replace('-', '')
    if compact.isupper() and compact.isalpha() and 2 <= len(compact) <= 8:
        return False
    bare = _bare_person_name(stripped)
    if len(bare) == 0:
        return False
    known = list_known_faculty_names()
    bare_key = bare.casefold()
    source_key = stripped.casefold()
    for name in known:
        name_key = name.casefold()
        if source_key == name_key:
            return True
        if bare_key == name_key:
            return True
    return False


def is_keepable_lexicon_key(source: str) -> bool:
    stripped = source.strip()
    if stripped in _HONORIFICS:
        return True
    return is_known_person_name(stripped)


def is_accepted_entry(kind: PronunciationKind | str, source: str) -> bool:
    kind_value = str(kind)
    stripped = source.strip()
    if kind_value == PronunciationKind.HONORIFIC.value:
        return stripped in _HONORIFICS
    if kind_value == PronunciationKind.PERSON_NAME.value:
        return is_known_person_name(stripped)
    return False


def text_has_latin(text: str) -> bool:
    for character in text:
        code = ord(character)
        if 65 <= code <= 90:
            return True
        if 97 <= code <= 122:
            return True
    return False


async def fetch_new_pronunciations(spoken_text: str, existing_keys: list[str]) -> dict[str, str]:
    if not text_has_latin(spoken_text):
        empty: dict[str, str] = {}
        return empty
    known_names = list_known_faculty_names()
    existing_json = json.dumps(existing_keys, ensure_ascii=False)
    known_json = json.dumps(known_names, ensure_ascii=False)

    def make_runnable(chat_model: ChatGoogleGenerativeAI):
        structured_model = chat_model.with_structured_output(PronunciationMap)
        pronounce_chain = PRONOUNCE_PROMPT | structured_model
        return pronounce_chain

    payload: dict[str, str] = {}
    payload['spoken_text'] = spoken_text
    payload['existing_keys'] = existing_json
    payload['known_names'] = known_json
    try:
        result = await invoke_llm(make_runnable, payload, 0.0)
    except LlmUnavailableError as error:
        logger.warning('TTS pronunciation map skipped: %s', error)
        failed: dict[str, str] = {}
        return failed
    if isinstance(result, PronunciationMap):
        parsed = result
    elif isinstance(result, dict):
        parsed = PronunciationMap.model_validate(result)
    else:
        empty_result: dict[str, str] = {}
        return empty_result
    existing_set = set(existing_keys)
    entries: dict[str, str] = {}
    for item in parsed.entries:
        source = item.source.strip()
        spoken = item.spoken.strip()
        if len(source) == 0 or len(spoken) == 0:
            continue
        if source in existing_set:
            continue
        if not is_accepted_entry(item.kind, source):
            continue
        entries[source] = spoken
    return entries
