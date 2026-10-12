"""Polite particle handling for speech."""

from app.ai.tts_phrases import (
    PAUSE_SENTINEL,
    fix_orphan_polite_sentences,
    phrases_from_markdown,
    strip_markdown_for_speech,
)


def test_fix_orphan_polite_sentence() -> None:
    raw = "အသုံးချသုတေသနပြုနေသူ ဖြစ်ပါသည်။ ရှင်။"
    fixed = fix_orphan_polite_sentences(raw)
    assert fixed == "အသုံးချသုတေသနပြုနေသူ ဖြစ်ပါသည် ရှင်။"


def test_speech_single_phrase_after_orphan_fix() -> None:
    raw = "အသုံးချသုတေသနပြုနေသူ ဖြစ်ပါသည်။ ရှင်။"
    spoken = strip_markdown_for_speech(raw)
    assert PAUSE_SENTINEL not in spoken
    assert spoken.endswith("ရှင်။")
    assert "သည်။" not in spoken


def test_merge_orphan_polite_phrase_list() -> None:
    phrases = phrases_from_markdown("ပထမ စာကြောင်း။ ရှင်။")
    assert len(phrases) == 1
    assert phrases[0].endswith("ရှင်။")
