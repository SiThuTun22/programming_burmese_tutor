"""User prompts aligned with SFT chat format."""

from __future__ import annotations

import re
from functools import lru_cache

from tutor.config import (
    INFERENCE_PROMPT_PATH,
    LANG_SUFFIX,
    STYLE_GUIDE_ENABLED,
)

_SECTION_RE = re.compile(r"^##\s+(\S+)\s*$", re.MULTILINE)


def _parse_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in markdown.splitlines():
        match = _SECTION_RE.match(line)
        if match:
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = match.group(1).lower()
            lines = []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections


def _bullets_to_text(section: str) -> str:
    parts: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("- "):
            parts.append(line[2:].strip())
    return " ".join(parts)


@lru_cache(maxsize=1)
def load_inference_guide() -> dict[str, str]:
    raw = INFERENCE_PROMPT_PATH.read_text(encoding="utf-8")
    parsed = _parse_sections(raw)
    return {
        "general": _bullets_to_text(parsed.get("general", "")),
        "with_code": _bullets_to_text(parsed.get("with_code", "")),
    }


def inference_guide_text(has_code: bool) -> str:
    guides = load_inference_guide()
    general = guides.get("general", "").strip()
    if not general:
        return ""
    if has_code:
        extra = guides.get("with_code", "").strip()
        if extra:
            return f"{general} {extra}"
    return general


def guide_marker() -> str:
    """Substring used to detect whether the guide was already appended."""
    guides = load_inference_guide()
    general = guides.get("general", "").strip()
    if len(general) >= 24:
        return general[:24]
    return general


def append_inference_guide(text: str, *, has_code: bool) -> str:
    if not STYLE_GUIDE_ENABLED:
        return text
    guide = inference_guide_text(has_code)
    if not guide:
        return text
    marker = guide_marker()
    if marker and marker in text:
        return text
    return f"{text} {guide}"


def format_sft_user_content(instruction: str, code: str = "") -> str:
    """Build user turn: instruction (+ lang suffix) → guide → optional code fence."""
    text = instruction.strip()
    if LANG_SUFFIX not in text:
        text = f"{text} {LANG_SUFFIX}"
    code = (code or "").strip()
    text = append_inference_guide(text, has_code=bool(code))
    if code:
        text = f"{text}\n\n```\n{code}\n```"
    return text


def inject_book_quotes(user_content: str, quotes: list[str]) -> str:
    if not quotes:
        return user_content
    from tutor.retrieve import format_quote_block

    block = format_quote_block(quotes)
    fence = "\n\n```\n"
    if fence in user_content:
        head, tail = user_content.split(fence, 1)
        return f"{head}\n\n{block}{fence}{tail}"
    return f"{user_content}\n\n{block}"


def build_user_content(question: str, code: str = "", quotes: list[str] | None = None) -> str:
    text = format_sft_user_content(question, code)
    if quotes:
        text = inject_book_quotes(text, quotes)
    return text


def build_messages(
    question: str, code: str = "", quotes: list[str] | None = None
) -> list[dict]:
    return [{"role": "user", "content": build_user_content(question, code, quotes)}]


def build_messages_from_row(row: dict) -> list[dict]:
    return [
        {
            "role": "user",
            "content": format_sft_user_content(
                row["instruction"],
                row.get("input", ""),
            ),
        }
    ]
