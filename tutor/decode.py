"""Deterministic cleanup after generation (no GPU)."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _is_near_duplicate(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return True
    if na == nb:
        return True
    prefix = 40
    if na[:prefix] == nb[:prefix] and len(na) >= 20 and len(nb) >= 20:
        return True
    if na in nb or nb in na:
        shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
        if len(shorter) >= 24 and len(shorter) / len(longer) >= 0.55:
            return True
    return SequenceMatcher(None, na, nb).ratio() >= 0.72


def _split_units(text: str) -> list[str]:
    chunks = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if len(chunks) == 1 and chunks[0].count("။") >= 2:
        parts = re.split(r"(?<=။)", chunks[0])
        chunks = [p.strip() for p in parts if p.strip()]
    return chunks


def collapse_repeated_paragraphs(text: str, *, max_paragraphs: int = 4) -> str:
    """Drop near-duplicate paragraphs and a truncated trailing fragment."""
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    units = _split_units(cleaned)
    kept: list[str] = []
    for unit in units:
        if any(_is_near_duplicate(unit, prev) for prev in kept):
            continue
        kept.append(unit)
        if len(kept) >= max_paragraphs:
            break
    if kept:
        last = kept[-1]
        if (
            not last.endswith(("။", ".", "```", "`"))
            and "```" not in last
            and len(last) < 80
        ):
            kept.pop()
    return "\n\n".join(kept).strip()
