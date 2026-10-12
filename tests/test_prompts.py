"""Tutor prompt delivery lines (no live API)."""

from tutor.knowledge import KnowledgeChunk
from tutor.prompts import (
    ANTI_COPY_LINE,
    CONTINUE_STYLE,
    ENGLISH_NAMES_LINE,
    FOLLOW_THREAD_LINE,
    MIIT_FOCUS_LINE,
    MIIT_OVERVIEW_LINE,
    MIIT_PAPERS_LINE,
    MIIT_PROGRAM_LINE,
    MIIT_WORDING_STYLES,
    PERSON_PRONOUN_LINE,
    PROGRAMMING_STYLES,
    TUTOR_VOICE_FEMALE,
    TUTOR_VOICE_MALE,
    build_general_tutor_messages,
    build_miit_messages,
)


def test_general_prompt_includes_anti_copy_and_style(monkeypatch) -> None:
    monkeypatch.setattr("tutor.prompts.secrets.choice", lambda seq: seq[1])
    content = build_general_tutor_messages("Fragment ဆိုတာ ဘာလဲ?")[0]["content"]
    assert ANTI_COPY_LINE in content
    assert PERSON_PRONOUN_LINE in content
    assert "Dr. Cynthia Myint" in PERSON_PRONOUN_LINE
    assert "ဒေါ်စင်သီယာမြင့်" not in PERSON_PRONOUN_LINE
    assert ENGLISH_NAMES_LINE in content
    assert PROGRAMMING_STYLES[1][1] in content
    assert PROGRAMMING_STYLES[0][1] not in content
    assert TUTOR_VOICE_FEMALE in content
    male = build_general_tutor_messages("Fragment ဆိုတာ ဘာလဲ?", voice="male")[0]["content"]
    assert TUTOR_VOICE_MALE in male
    assert TUTOR_VOICE_FEMALE not in male


def test_miit_prompt_anti_copy_without_programming_styles(monkeypatch) -> None:
    monkeypatch.setattr("tutor.prompts.secrets.choice", lambda seq: seq[1])
    chunk = KnowledgeChunk(
        id="role",
        text="Cynthia Myint teaches at MIIT.",
        sources=("https://example.com/cynthia",),
        tokens=frozenset(),
    )
    content = build_miit_messages("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?", [chunk])[0]["content"]
    assert ANTI_COPY_LINE in content
    assert PERSON_PRONOUN_LINE in content
    assert ENGLISH_NAMES_LINE in content
    assert MIIT_FOCUS_LINE in content
    assert "ပါမောက္ခ ကို ပထမဝါကျမှာ တစ်ကြိမ်သာ သုံးပါ" in MIIT_FOCUS_LINE
    assert "Dr. Cynthia Myint နှင့် Dr. Sin Thi Yar Myint ကို တစ်ဝါကျတည်း မထပ်ရေးပါနှင့်" in MIIT_FOCUS_LINE
    assert MIIT_PAPERS_LINE not in content
    assert MIIT_PROGRAM_LINE in content
    assert "နှစ်ကျော်မသွားပါနှင့်" in MIIT_PROGRAM_LINE
    assert "အပြည့်အစုံ မေးမှသာ" not in MIIT_PROGRAM_LINE
    assert "ကြော်ငြာပုံ မရေးပါနှင့်" in content
    for _name, line in PROGRAMMING_STYLES:
        assert line not in content
    assert MIIT_WORDING_STYLES[1][1] in content
    teaching = dict(MIIT_WORDING_STYLES)["teaching"]
    assert "သင်ကြားရေးအကြောင်းကို အရင် ပြောပါ" not in teaching
    assert "အရင် ပြောပါ" not in teaching
    assert "ခန့်မှန်းမရေးပါနှင့်" in content
    assert "Cynthia Myint teaches at MIIT." in content
    assert "https://example.com/cynthia" in content


def test_miit_overview_prompt_prefers_identity_line(monkeypatch) -> None:
    monkeypatch.setattr("tutor.prompts.secrets.choice", lambda seq: seq[0])
    chunk = KnowledgeChunk(
        id="institute-overview",
        text="MIIT Mandalay 2015",
        sources=("https://example.com/miit",),
        tokens=frozenset(),
    )
    content = build_miit_messages("MIIT ဆိုတာ ဘာလဲ?", [chunk])[0]["content"]
    assert MIIT_OVERVIEW_LINE in content
    assert MIIT_PROGRAM_LINE not in content


def test_miit_followup_uses_continue_style(monkeypatch) -> None:
    monkeypatch.setattr(
        "tutor.prompts.secrets.choice",
        lambda seq: seq[0],
    )
    chunk = KnowledgeChunk(
        id="role",
        text="Cynthia Myint teaches at MIIT.",
        sources=("https://example.com/cynthia",),
        tokens=frozenset(),
    )
    history = [{"question": "Cynthia Myint ဆိုတာ ဘယ်သူလဲ?", "answer": "MIIT professor"}]
    content = build_miit_messages(
        "သူမ ဘာတွေ သုတေသနလုပ်လဲ?",
        [chunk],
        history=history,
    )[0]["content"]
    assert FOLLOW_THREAD_LINE in content
    assert CONTINUE_STYLE[1] in content
    assert "ရာထူးနှင့် လုပ်ရာနေရာ" not in content
