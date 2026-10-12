"""Faculty and honorific pronunciation maps for Myanmar TTS."""

from __future__ import annotations

import json
import logging
import re
from tutor.config import MIIT_DIR

logger = logging.getLogger(__name__)

_HONORIFICS = {
    "Dr",
    "Dr.",
    "Prof",
    "Prof.",
    "Mr",
    "Mr.",
    "Mrs",
    "Mrs.",
    "Ms",
    "Ms.",
}
_TITLE_WORDS = {"Dr", "Prof", "Mr", "Mrs", "Ms"}
_CAMPUS_STEMS = {
    "institute",
    "bachelor_admission",
    "cse_be_hons",
    "ece_be_hons",
}
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
PRONOUNCE_PROMPT = (
    "Build a pronunciation map for Myanmar TTS. Return JSON only with an entries array. "
    "Each entry must have source, spoken, and kind (honorific or person_name). "
    "honorific: only Dr, Dr., Prof, Prof., Mr, Mr., Mrs, Mrs., Ms, Ms. "
    "(example: Dr -> ဒေါက်တာ). "
    "person_name: only people names from the known faculty name list. "
    "Do not map research titles, course names, orgs, or other English. "
    "Do not repeat keys already listed. Do not map pure Myanmar text. "
    "If nothing new is needed, return an empty entries list.\n\n"
    "Known faculty names (JSON array):\n{known_names}\n\n"
    "Existing keys (JSON array):\n{existing_keys}\n\n"
    "Text to speak:\n{spoken_text}"
)


def _name_from_stem(stem: str) -> str:
    return " ".join(part.capitalize() for part in stem.split("_") if part)


def _bare_person_name(source: str) -> str:
    words = source.strip().split()
    if not words:
        return ""
    first_bare = words[0].rstrip(".")
    if first_bare in _TITLE_WORDS:
        return " ".join(words[1:])
    return source.strip()


def list_known_faculty_names() -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    if not MIIT_DIR.is_dir():
        return names
    for path in sorted(MIIT_DIR.glob("*.jsonl")):
        if path.stem in _CAMPUS_STEMS or path.name.startswith("_"):
            continue
        from_stem = _name_from_stem(path.stem)
        key = from_stem.casefold()
        if from_stem and key not in seen:
            names.append(from_stem)
            seen.add(key)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            name_value = payload.get("name")
            if not isinstance(name_value, str):
                continue
            name_stripped = name_value.strip()
            name_key = name_stripped.casefold()
            if not name_stripped or name_key in seen:
                continue
            names.append(name_stripped)
            seen.add(name_key)
    return names


def is_known_person_name(source: str) -> bool:
    stripped = source.strip()
    if "@" in stripped:
        return False
    compact = stripped.replace(".", "").replace(" ", "").replace("-", "")
    if compact.isupper() and compact.isalpha() and 2 <= len(compact) <= 8:
        return False
    bare = _bare_person_name(stripped)
    if not bare:
        return False
    known = list_known_faculty_names()
    bare_key = bare.casefold()
    source_key = stripped.casefold()
    for name in known:
        name_key = name.casefold()
        if source_key == name_key or bare_key == name_key:
            return True
    return False


def is_keepable_lexicon_key(source: str) -> bool:
    stripped = source.strip()
    if stripped in _HONORIFICS:
        return True
    return is_known_person_name(stripped)


def text_has_latin(text: str) -> bool:
    return any("A" <= character <= "Z" or "a" <= character <= "z" for character in text)


def _parse_entries(raw: str) -> list[dict]:
    payload = _FENCE_RE.sub("", (raw or "").strip()).strip()
    if not payload:
        return []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    rows = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def fetch_new_pronunciations(spoken_text: str, existing_keys: list[str]) -> dict[str, str]:
    from tutor.config import TTS_SKIP_GEMINI_HELPERS

    if TTS_SKIP_GEMINI_HELPERS or not text_has_latin(spoken_text):
        return {}
    known_names = list_known_faculty_names()
    prompt = PRONOUNCE_PROMPT.format(
        known_names=json.dumps(known_names, ensure_ascii=False),
        existing_keys=json.dumps(existing_keys, ensure_ascii=False),
        spoken_text=spoken_text,
    )
    try:
        from tutor.gemini_client import get_tts_helper_gemini_client

        messages = [{"role": "user", "content": prompt}]
        kwargs = {"temperature": 0.0, "top_p": 1.0, "max_new_tokens": 256}
        raw = get_tts_helper_gemini_client().generate(messages, **kwargs)
    except Exception as exc:
        logger.warning("TTS pronunciation map skipped: %s", exc)
        return {}
    existing_set = set(existing_keys)
    entries: dict[str, str] = {}
    for item in _parse_entries(raw):
        source = str(item.get("source") or "").strip()
        spoken = str(item.get("spoken") or "").strip()
        kind = str(item.get("kind") or "").strip()
        if not source or not spoken or source in existing_set:
            continue
        if kind == "honorific" and source not in _HONORIFICS:
            continue
        if kind == "person_name" and not is_known_person_name(source):
            continue
        if kind not in {"honorific", "person_name"}:
            continue
        entries[source] = spoken
    return entries
