"""Ask-time lexical retrieval from extracted book sentences (CPU)."""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from build_book_voice_dataset import (  # noqa: E402
    CODE_TOKEN_RE,
    STOP_EN,
    load_book_sentences,
    merge_pools,
    pick_book_sentences,
    score_sentence,
    token_in_text,
    topic_keys,
)

from tutor.scope import IN_SCOPE_TOKENS, _STOP

_DEF_NAME = re.compile(
    r"\b(?:def|function)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
_QUOTE_HEADER = "စာအုပ်မှ ကိုးကား:"

# Too common to retrieve on (e.g. low → "Low Level Programming").
_GENERIC_CODE = frozenset(STOP_EN) | {
    "low",
    "high",
    "mid",
    "arr",
    "len",
    "return",
    "while",
    "elif",
    "else",
    "target",
    "result",
    "numbers",
    "element",
    "index",
    "value",
    "left",
    "right",
    "print",
    "input",
    "true",
    "false",
    "none",
    "self",
    "this",
    "let",
    "var",
    "const",
    "function",
    "class",
    "def",
    "int",
    "str",
    "list",
    "dict",
    "range",
    "len",
}


def _distinctive_code_keys(code: str) -> list[str]:
    keys = []
    seen: set[str] = set()
    for token in CODE_TOKEN_RE.findall(code or ""):
        low = token.lower()
        if low in _GENERIC_CODE or low in _STOP:
            continue
        if low in seen:
            continue
        distinctive = ("_" in token) or token[:1].isupper() or len(token) >= 8
        if not distinctive and low in IN_SCOPE_TOKENS:
            continue
        if not distinctive:
            continue
        seen.add(low)
        keys.append(token)
    return keys


@lru_cache(maxsize=1)
def book_sentence_pool() -> list[str]:
    return merge_pools(load_book_sentences())


def retrieve_book_quotes(question: str, code: str = "", *, limit: int = 3) -> list[str]:
    code = (code or "").strip()
    pool = book_sentence_pool()
    if code:
        return _retrieve_for_code(question, code, pool, limit)
    row = {
        "instruction": question or "",
        "input": "",
        "task_type": "concept_qa",
    }
    picked = pick_book_sentences(row, pool, limit=limit)
    return _drop_path_calque(question, picked)


def _drop_path_calque(question: str, picked: list[str]) -> list[str]:
    routing_q = bool(
        re.search(
            r"(route|routing|router|/posts|/hello|web\.php)",
            question or "",
            re.I,
        )
    )
    keep = []
    for sent in picked:
        if "လမ်းကြောင်း" in sent and not routing_q:
            continue
        keep.append(sent)
    return keep


def _retrieve_for_code(question: str, code: str, pool: list[str], limit: int) -> list[str]:
    keys = _distinctive_code_keys(code) + topic_keys(question)
    keys = list(dict.fromkeys(keys))
    if not keys:
        return []
    ranked = []
    for sent in pool:
        hits = [k for k in keys if token_in_text(k, sent)]
        if not hits:
            continue
        points = score_sentence(sent, keys)
        if points < 4:
            continue
        ranked.append((points, len(sent), sent))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    picked = []
    seen: set[str] = set()
    for _, __, sent in ranked:
        key = sent[:48]
        if key in seen:
            continue
        seen.add(key)
        picked.append(sent)
        if len(picked) >= limit:
            break
    return _drop_path_calque(question, picked)


def defined_names(code: str) -> list[str]:
    return [m.group(1) for m in _DEF_NAME.finditer(code or "")]


def is_uncovered_algorithm(question: str, code: str = "", quotes: list[str] | None = None) -> bool:
    """True when code/question names a def that books do not support and retrieval missed."""
    if quotes is None:
        quotes = retrieve_book_quotes(question, code)
    if quotes:
        return False
    names = defined_names(code)
    blob = f"{question}\n{code}"
    for name in names:
        key = name.lower()
        if key in IN_SCOPE_TOKENS or key in _STOP:
            continue
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", blob):
            return True
    return False


def format_quote_block(quotes: list[str]) -> str:
    if not quotes:
        return ""
    lines = [_QUOTE_HEADER]
    lines.extend(quotes)
    return "\n".join(lines)
