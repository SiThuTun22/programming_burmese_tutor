"""AAA TTS id resolution and pronunciation maps for Gradio Listen."""

from __future__ import annotations

import uuid

from tutor.aaa_tts import (
    aaa_audio_not_ready,
    aaa_primary_pending,
    kickoff_aaa_tts,
    message_id_for_text,
    message_id_for_turn,
    restore_turn_audio_ids,
)


def test_message_id_for_text_from_persisted_turn() -> None:
    mid = uuid.uuid4()
    history = [
        {
            "question": "q",
            "answer": "hello",
            "turn_id": "tid",
            "audio_message_id": str(mid),
        },
    ]
    assert message_id_for_text("hello", history) == mid


def test_restore_turn_audio_ids_from_persisted_history() -> None:
    mid = uuid.uuid4()
    history = [
        {
            "question": "q",
            "answer": "hello",
            "turn_id": "tid-restore",
            "audio_message_id": str(mid),
        },
    ]
    restore_turn_audio_ids(history)
    assert message_id_for_turn("tid-restore") == mid
    assert message_id_for_text("hello", [{"answer": "hello", "turn_id": "tid-restore"}]) == mid


def test_kickoff_reuses_persisted_message_id(monkeypatch) -> None:
    mid = uuid.uuid4()
    monkeypatch.setattr("tutor.aaa_tts.TTS_ENABLED", False)
    got = kickoff_aaa_tts("hello", "Female", "tid-reuse", message_id=mid)
    assert got == mid
    assert message_id_for_turn("tid-reuse") == mid


def test_aaa_primary_pending_without_file(monkeypatch) -> None:
    mid = uuid.uuid4()
    monkeypatch.setattr(
        "tutor.aaa_tts.aaa_audio_file_ready",
        lambda _mid: False,
    )
    monkeypatch.setattr(
        "tutor.aaa_tts.aaa_prepare_in_flight",
        lambda _mid: True,
    )
    turn = {"answer": "hello", "audio_message_id": str(mid), "tts_voice": "Male"}
    assert aaa_primary_pending(turn) is True


def test_aaa_primary_not_pending_without_message_id() -> None:
    turn = {"answer": "hello", "tts_voice": "Male"}
    assert aaa_primary_pending(turn) is False


def test_aaa_primary_not_pending_when_file_ready(monkeypatch) -> None:
    mid = uuid.uuid4()
    monkeypatch.setattr(
        "tutor.aaa_tts.aaa_audio_file_ready",
        lambda _mid: True,
    )
    turn = {"answer": "hello", "audio_message_id": str(mid), "tts_voice": "Male"}
    assert aaa_primary_pending(turn) is False


def test_aaa_secondary_not_ready_uses_hybrid_pending(monkeypatch) -> None:
    mid = uuid.uuid4()
    monkeypatch.setattr(
        "tutor.aaa_tts.aaa_audio_file_ready",
        lambda _mid: True,
    )
    monkeypatch.setattr(
        "tutor.aaa_tts.cached_audio_path",
        lambda _a, _g: None,
    )
    monkeypatch.setattr(
        "tutor.aaa_tts.prefetch_pending",
        lambda _a, _g: True,
    )
    turn = {"answer": "hello", "audio_message_id": str(mid), "tts_voice": "Male"}
    assert aaa_audio_not_ready(turn, "Female") is True


def test_aaa_audio_not_ready_until_file_exists(monkeypatch) -> None:
    mid = uuid.uuid4()
    monkeypatch.setattr(
        "tutor.aaa_tts.aaa_audio_file_ready",
        lambda _mid: False,
    )
    monkeypatch.setattr(
        "tutor.aaa_tts.cached_audio_path",
        lambda *_a, **_k: None,
    )
    turn = {"answer": "hello", "audio_message_id": str(mid), "tts_voice": "Male"}
    assert aaa_audio_not_ready(turn, "Male") is True


def test_miit_spells_letter_by_letter() -> None:
    from app.ai.tts_spell import KIND_SPELL, apply_spell_cache, letters_for_speech

    spoken = letters_for_speech("MIIT")
    assert "အမ်" in spoken
    assert "အိုင်" in spoken
    assert "တီ" in spoken
    mapped = apply_spell_cache("MIIT မှာ သင်သည်။", {"MIIT": KIND_SPELL})
    assert "MIIT" not in mapped
    assert "အမ်" in mapped


def test_roman_i_vs_letter_i() -> None:
    from app.ai.tts_roman import KIND_ROMAN, apply_roman_cache
    from app.ai.tts_spell import KIND_SPELL, apply_spell_cache

    roman = apply_roman_cache("Semester I", {"I": KIND_ROMAN})
    assert "Semester I" != roman
    assert "I" not in roman.split()
    letter = apply_spell_cache("use ID", {"ID": KIND_SPELL})
    assert "ID" not in letter
    assert "အိုင်" in letter
