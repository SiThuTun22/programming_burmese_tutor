"""Prompt formatting tests (no GPU / model load)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.config import LANG_SUFFIX
from tutor.prompts import (
    append_inference_guide,
    build_messages,
    build_messages_from_row,
    build_user_content,
    guide_marker,
    inference_guide_text,
    load_inference_guide,
)
from tutor.prompts import _parse_sections, _bullets_to_text


def test_appends_language_suffix():
    text = build_user_content("React ဆိုတာ ဘာလဲ?")
    assert LANG_SUFFIX in text
    assert guide_marker() in text


def test_does_not_duplicate_suffix():
    q = f"Hello? {LANG_SUFFIX}"
    assert build_user_content(q).count(LANG_SUFFIX) == 1


def test_does_not_duplicate_guide():
    text = build_user_content("React ဆိုတာ ဘာလဲ?")
    again = append_inference_guide(text, has_code=False)
    assert again == text


def test_code_fence_and_with_code_guide():
    text = build_user_content("ရှင်းပြပါ", "print(1)")
    assert "```\nprint(1)\n```" in text
    guides = load_inference_guide()
    assert guides["with_code"] in text


def test_concept_without_code_guide_only_general():
    text = build_user_content("IDE ဆိုတာ ဘာလဲ?")
    guides = load_inference_guide()
    assert guides["general"] in text
    assert guides["with_code"] not in text


def test_build_messages_role():
    msgs = build_messages("Variable ဆိုတာ ဘာလဲ?")
    assert msgs[0]["role"] == "user"
    assert LANG_SUFFIX in msgs[0]["content"]


def test_row_matches_chat_format():
    row = {
        "instruction": f"ဒီ code ကို ရှင်းပြပါ။ {LANG_SUFFIX}",
        "input": "x = 1",
        "output": "dummy",
    }
    msgs = build_messages_from_row(row)
    direct = build_user_content("ဒီ code ကို ရှင်းပြပါ။", "x = 1")
    assert msgs[0]["content"] == direct


def test_parse_inference_sections():
    md = "## general\n\n- Line one.\n\n## with_code\n\n- Line two."
    sections = _parse_sections(md)
    assert _bullets_to_text(sections["general"]) == "Line one."
    assert _bullets_to_text(sections["with_code"]) == "Line two."


def test_inference_guide_text_flag():
    assert inference_guide_text(False)
    with_code = inference_guide_text(True)
    assert len(with_code) > len(inference_guide_text(False))
