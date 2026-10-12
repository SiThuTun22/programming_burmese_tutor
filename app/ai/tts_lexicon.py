from __future__ import annotations

import json
import threading
from pathlib import Path

from app.ai.tts_pronounce import is_keepable_lexicon_key
from app.lib.config import get_tts_lexicon_path

_lock = threading.Lock()


def _ensure_parent(path: Path) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)


def _read_raw_lexicon(path: Path) -> dict[str, str]:
    lexicon: dict[str, str] = {}
    if not path.is_file():
        return lexicon
    raw = path.read_text(encoding='utf-8')
    if len(raw.strip()) == 0:
        return lexicon
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        return lexicon
    for key, value in loaded.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if len(key.strip()) == 0 or len(value.strip()) == 0:
            continue
        lexicon[key] = value
    return lexicon


def _prune_lexicon(lexicon: dict[str, str]) -> dict[str, str]:
    kept: dict[str, str] = {}
    for key, value in lexicon.items():
        if not is_keepable_lexicon_key(key):
            continue
        kept[key] = value
    return kept


def _write_lexicon(path: Path, lexicon: dict[str, str]) -> None:
    _ensure_parent(path)
    encoded = json.dumps(lexicon, ensure_ascii=False, indent=2)
    path.write_text(encoded, encoding='utf-8')


def load_lexicon() -> dict[str, str]:
    path = get_tts_lexicon_path()
    with _lock:
        lexicon = _read_raw_lexicon(path)
        pruned = _prune_lexicon(lexicon)
        if pruned != lexicon:
            _write_lexicon(path, pruned)
        return pruned


def merge_lexicon(entries: dict[str, str]) -> dict[str, str]:
    path = get_tts_lexicon_path()
    with _lock:
        lexicon = _read_raw_lexicon(path)
        for key, value in entries.items():
            if len(key.strip()) == 0 or len(value.strip()) == 0:
                continue
            if not is_keepable_lexicon_key(key):
                continue
            lexicon[key] = value
        pruned = _prune_lexicon(lexicon)
        _write_lexicon(path, pruned)
        return pruned


def apply_lexicon(text: str, lexicon: dict[str, str]) -> str:
    keys: list[str] = []
    for key in lexicon:
        keys.append(key)
    keys.sort(key=len, reverse=True)
    spoken = text
    for key in keys:
        if len(key) == 0:
            continue
        if not is_keepable_lexicon_key(key):
            continue
        replacement = lexicon[key]
        spoken = spoken.replace(key, replacement)
    return spoken
