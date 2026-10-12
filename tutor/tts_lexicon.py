"""Persist TTS honorific and faculty-name pronunciation maps."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from tutor.config import TTS_LEXICON_PATH
from tutor.tts_pronounce import is_keepable_lexicon_key

_lock = threading.Lock()


def _read_raw_lexicon(path: Path) -> dict[str, str]:
    lexicon: dict[str, str] = {}
    if not path.is_file():
        return lexicon
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return lexicon
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        return lexicon
    for key, value in loaded.items():
        if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
            lexicon[key] = value
    return lexicon


def _prune_lexicon(lexicon: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in lexicon.items() if is_keepable_lexicon_key(key)}


def _write_lexicon(path: Path, lexicon: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lexicon, ensure_ascii=False, indent=2), encoding="utf-8")


def load_lexicon() -> dict[str, str]:
    path = TTS_LEXICON_PATH
    with _lock:
        lexicon = _read_raw_lexicon(path)
        pruned = _prune_lexicon(lexicon)
        if pruned != lexicon:
            _write_lexicon(path, pruned)
        return pruned


def merge_lexicon(entries: dict[str, str]) -> dict[str, str]:
    path = TTS_LEXICON_PATH
    with _lock:
        lexicon = _read_raw_lexicon(path)
        for key, value in entries.items():
            if not key.strip() or not value.strip() or not is_keepable_lexicon_key(key):
                continue
            lexicon[key] = value
        pruned = _prune_lexicon(lexicon)
        _write_lexicon(path, pruned)
        return pruned


def apply_lexicon(text: str, lexicon: dict[str, str]) -> str:
    keys = [key for key in lexicon if is_keepable_lexicon_key(key)]
    keys.sort(key=len, reverse=True)
    spoken = text
    for key in keys:
        spoken = spoken.replace(key, lexicon[key])
    return spoken
