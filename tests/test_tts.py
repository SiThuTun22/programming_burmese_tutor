"""TTS helpers (no network in most tests)."""

from __future__ import annotations

from pathlib import Path

from tutor.tts import (
    cache_path_for,
    cached_audio_path,
    prepare_for_speech,
    synthesize_both_sync,
    synthesize_sync,
)


def test_default_tts_gender_is_female(monkeypatch) -> None:
    monkeypatch.setattr("tutor.tts.TTS_VOICE", "my-MM-NilarNeural")
    from tutor.tts import default_tts_gender

    assert default_tts_gender() == "female"


def test_prepare_for_speech_collapses_whitespace() -> None:
    raw = "Hello   world\n\n\n\nMyanmar"
    assert prepare_for_speech(raw) == "Hello world\n\nMyanmar"


def test_prepare_for_speech_maps_english_person_names() -> None:
    out = prepare_for_speech("Dr. Cynthia Myint teaches at MIIT.")
    assert "စင်သီယာမြင့်" in out
    assert "ဒေါက်တာ" in out
    assert "Cynthia Myint" not in out
    assert "MIIT" in out
    rector = prepare_for_speech("Dr. Win Aye is rector.")
    assert "ဝင်းအေး" in rector
    assert "Win Aye" not in rector


def test_prepare_for_speech_skips_latin_parentheses() -> None:
    out = prepare_for_speech("Natural Language Processing (NLP) ကို သုတေသနလုပ်သည်။")
    assert "NLP" not in out
    assert "Natural Language Processing" in out
    assert "သုတေသန" in out


def test_prepare_for_speech_keeps_myanmar_parentheses() -> None:
    out = prepare_for_speech("ရှင်းပြချက် (မှတ်ချက်) ပါသည်။")
    assert "(မှတ်ချက်)" in out


def test_prepare_for_speech_leaves_code_terms() -> None:
    assert "useState" in prepare_for_speech("useState hook ကို သုံးပါ။")
    assert "React" in prepare_for_speech("React ဆိုတာ ဘာလဲ?")
    assert "NLP" in prepare_for_speech("NLP ကို သုတေသနလုပ်သည်။")


def test_prepare_for_speech_strips_http_urls() -> None:
    wiki = "https://en.wikipedia.org/wiki/Myanmar_Institute_of_Information_Technology"
    out = prepare_for_speech(f"See {wiki} for papers.")
    assert "https://" not in out
    assert "wikipedia" not in out.lower()
    assert "See" in out
    assert "for papers." in out

    linkedin = "https://www.linkedin.com/school/myanmar-institute-of-information-technology-miit-/"
    site = "https://www.miit.edu.mm/"
    both = prepare_for_speech(f"Sources\n{linkedin}\n{site}")
    assert "https://" not in both
    assert "linkedin" not in both.lower()
    assert "miit.edu" not in both.lower()
    assert "Sources" in both


def test_prepare_for_speech_cynthia_skips_gemini(monkeypatch) -> None:
    from tutor.speech_names import clear_speech_name_cache, set_speech_name_generate_fn

    clear_speech_name_cache()

    def boom(*args, **kwargs):
        raise AssertionError("Gemini should not run for mapped Cynthia names")

    set_speech_name_generate_fn(boom)
    try:
        out = prepare_for_speech("Dr. Cynthia Myint teaches at MIIT.")
        assert "စင်သီယာမြင့်" in out
        assert "Cynthia Myint" not in out
    finally:
        set_speech_name_generate_fn(None)
        clear_speech_name_cache()


def test_prepare_for_speech_dynamic_unknown_name(monkeypatch, tmp_path: Path) -> None:
    from tutor import speech_names as sn

    sn.clear_speech_name_cache()
    monkeypatch.setattr(sn, "TTS_CACHE_DIR", tmp_path)
    calls = {"n": 0}

    def fake(messages, **kwargs):
        calls["n"] += 1
        assert kwargs.get("temperature") == 0.0
        assert kwargs.get("max_new_tokens") == 256
        assert "Jane Doe" in messages[0]["content"]
        return '{"replacements":[{"en":"Jane Doe","my":"ဂျိန်းဒိုး"}]}'

    sn.set_speech_name_generate_fn(fake)
    try:
        first = prepare_for_speech("Jane Doe wrote the paper.")
        second = prepare_for_speech("Jane Doe wrote the paper.")
        assert "ဂျိန်းဒိုး" in first
        assert "Jane Doe" not in first
        assert first == second
        assert calls["n"] == 1
        assert "useState" in prepare_for_speech("useState hook ကို သုံးပါ။")
    finally:
        sn.set_speech_name_generate_fn(None)
        sn.clear_speech_name_cache()


def test_prepare_for_speech_skips_qa_gemini_key(monkeypatch, tmp_path: Path) -> None:
    from tutor import speech_names as sn

    sn.clear_speech_name_cache()
    monkeypatch.setattr(sn, "TTS_CACHE_DIR", tmp_path)
    monkeypatch.setattr(sn, "GEMINI_TTS_NAMES_API_KEY", "")
    sn.set_speech_name_generate_fn(None)

    def boom(**kwargs):
        raise AssertionError("must not use GEMINI_API_KEY for TTS names")

    monkeypatch.setattr("tutor.gemini_client.GeminiClient", boom)
    out = prepare_for_speech("Jane Doe wrote the paper.")
    assert "Jane Doe" in out
    sn.clear_speech_name_cache()


def test_synthesize_sync_disabled(monkeypatch) -> None:
    monkeypatch.setattr("tutor.tts.TTS_ENABLED", False)
    assert synthesize_sync("text") is None


def test_synthesize_sync_returns_hashed_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("tutor.tts.TTS_ENABLED", True)
    monkeypatch.setattr("tutor.tts.TTS_CACHE_DIR", tmp_path)

    async def ok(text: str, path: Path, *args) -> Path:
        path.write_bytes(b"\x00")
        return path

    monkeypatch.setattr("tutor.tts._synthesize_with_fallback", ok)

    result = synthesize_sync("မြန်မာ", voice="female")
    expected = cache_path_for("မြန်မာ", "female")
    assert result == str(expected)
    assert expected.is_file()


def test_synthesize_sync_cache_hit_skips_network(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("tutor.tts.TTS_ENABLED", True)
    monkeypatch.setattr("tutor.tts.TTS_CACHE_DIR", tmp_path)
    calls = {"n": 0}

    async def ok(text: str, path: Path, *args) -> Path:
        calls["n"] += 1
        path.write_bytes(b"\x00")
        return path

    monkeypatch.setattr("tutor.tts._synthesize_with_fallback", ok)
    first = synthesize_sync("မြန်မာ", voice="Female")
    second = synthesize_sync("မြန်မာ", voice="female")
    assert first == second
    assert calls["n"] == 1
    assert cached_audio_path("မြန်မာ", "female") == first


def test_synthesize_sync_female_uses_nilar(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("tutor.tts.TTS_ENABLED", True)
    monkeypatch.setattr("tutor.tts.TTS_CACHE_DIR", tmp_path)
    voices: list[str] = []

    async def capture(text: str, path: Path, primary: str, fallback: str) -> Path:
        voices.append(primary)
        voices.append(fallback)
        path.write_bytes(b"\x00")
        return path

    monkeypatch.setattr("tutor.tts._synthesize_with_fallback", capture)

    from tutor.tts import VOICE_FEMALE, VOICE_MALE

    result = synthesize_sync("မြန်မာ", voice="female")
    assert result == str(cache_path_for("မြန်မာ", "female"))
    assert voices[0] == VOICE_FEMALE
    assert voices[1] == VOICE_MALE


def test_synthesize_both_writes_two_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("tutor.tts.TTS_ENABLED", True)
    monkeypatch.setattr("tutor.tts.TTS_CACHE_DIR", tmp_path)
    voices: list[str] = []

    async def capture(text: str, path: Path, primary: str, fallback: str) -> Path:
        voices.append(primary)
        path.write_bytes(b"\x00")
        return path

    monkeypatch.setattr("tutor.tts._synthesize_with_fallback", capture)

    from tutor.tts import VOICE_FEMALE, VOICE_MALE

    selected = synthesize_both_sync("မြန်မာ", selected_gender="Male")
    male = cache_path_for("မြန်မာ", "male")
    female = cache_path_for("မြန်မာ", "female")
    assert selected == str(male)
    assert male.is_file()
    assert female.is_file()
    assert VOICE_MALE in voices
    assert VOICE_FEMALE in voices
    assert cached_audio_path("မြန်မာ", "female") == str(female)
