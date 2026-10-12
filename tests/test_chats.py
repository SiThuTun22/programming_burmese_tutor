"""On-disk chat store (no Gradio)."""

import json
from pathlib import Path

from tutor.chats import (
    active_conversation,
    conversation_title,
    delete_chat,
    load_store,
    radio_choices,
    save_store,
    select_chat,
    start_new_chat,
    upsert_turns,
)


def _store(path: Path) -> dict:
    return load_store(path)


def test_new_save_switch_delete(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    first = active_conversation(store)
    store = upsert_turns(
        store,
        first["id"],
        [{"question": "A question", "answer": "A answer"}],
    )
    save_store(store, path)

    store = start_new_chat(store)
    second = active_conversation(store)
    assert second["id"] != first["id"]
    store = upsert_turns(
        store,
        second["id"],
        [{"question": "B question", "answer": "B answer"}],
    )
    save_store(store, path)

    store = select_chat(store, first["id"])
    opened = active_conversation(store)
    assert opened["id"] == first["id"]
    assert opened["turns"][0]["question"] == "A question"

    store = delete_chat(store, second["id"])
    ids = {conv["id"] for conv in store["conversations"]}
    assert first["id"] in ids
    assert second["id"] not in ids
    assert active_conversation(store)["id"] == first["id"]
    save_store(store, path)
    reloaded = load_store(path)
    reloaded_ids = {conv["id"] for conv in reloaded["conversations"]}
    assert first["id"] in reloaded_ids
    assert second["id"] not in reloaded_ids


def test_delete_active_chat_opens_blank_like_new(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    first = active_conversation(store)
    store = upsert_turns(
        store,
        first["id"],
        [{"question": "Keep other", "answer": "ok"}],
    )
    store = start_new_chat(store)
    extra = active_conversation(store)
    store = upsert_turns(
        store,
        extra["id"],
        [{"question": "Delete me", "answer": "bye"}],
    )
    store = delete_chat(store, extra["id"])
    assert extra["id"] not in {conv["id"] for conv in store["conversations"]}
    assert first["id"] in {conv["id"] for conv in store["conversations"]}
    opened = active_conversation(store)
    assert opened["id"] != extra["id"]
    assert opened["id"] != first["id"]
    assert opened["turns"] == []
    save_store(store, path)
    reloaded = load_store(path)
    assert extra["id"] not in {conv["id"] for conv in reloaded["conversations"]}
    assert active_conversation(reloaded)["turns"] == []


def test_delete_non_active_keeps_open_chat(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    first = active_conversation(store)
    store = upsert_turns(
        store,
        first["id"],
        [{"question": "Keep me", "answer": "ok"}],
    )
    store = start_new_chat(store)
    extra = active_conversation(store)
    store = upsert_turns(
        store,
        extra["id"],
        [{"question": "Remove me", "answer": "bye"}],
    )
    store = select_chat(store, first["id"])
    store = delete_chat(store, extra["id"])
    assert active_conversation(store)["id"] == first["id"]
    assert extra["id"] not in {conv["id"] for conv in store["conversations"]}
    assert first["id"] in {conv["id"] for conv in store["conversations"]}


def test_two_new_chats_without_messages_stay_one(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    first = active_conversation(store)["id"]
    store = start_new_chat(store)
    store = start_new_chat(store)
    assert len(store["conversations"]) == 1
    assert active_conversation(store)["id"] == first
    assert active_conversation(store)["turns"] == []


def test_title_from_first_question() -> None:
    assert conversation_title([]) == "New chat"
    assert conversation_title([{"question": "MIIT ဆိုတာ ဘာလဲ။"}]) == "MIIT ဆိုတာ ဘာလဲ"
    long_q = "x" * 50
    title = conversation_title([{"question": long_q}])
    assert title.endswith("…")
    assert len(title) == 33


def test_turns_persist_audio_ids(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    first = active_conversation(store)
    store = upsert_turns(
        store,
        first["id"],
        [
            {
                "question": "q",
                "answer": "hello",
                "conversation_id": first["id"],
                "turn_id": "tid-1",
                "tts_id": "tid-1",
                "tts_voice": "Male",
                "audio_message_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            }
        ],
    )
    save_store(store, path)
    reloaded = load_store(path)
    turn = active_conversation(reloaded)["turns"][0]
    assert turn["conversation_id"] == first["id"]
    assert turn["turn_id"] == "tid-1"
    assert turn["tts_id"] == "tid-1"
    assert turn["tts_voice"] == "Male"
    assert turn["audio_message_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_delete_only_chat_survives_reload(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    only = active_conversation(store)
    store = upsert_turns(
        store,
        only["id"],
        [{"question": "Gone after delete", "answer": "bye"}],
    )
    save_store(store, path)
    deleted_id = only["id"]
    store = delete_chat(store, deleted_id)
    save_store(store, path)
    reloaded = load_store(path)
    assert deleted_id not in {conv["id"] for conv in reloaded["conversations"]}
    assert radio_choices(reloaded) == []
    assert active_conversation(reloaded)["turns"] == []


def test_upsert_stale_id_after_delete_does_not_resurrect(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    only = active_conversation(store)
    store = upsert_turns(
        store,
        only["id"],
        [{"question": "Q", "answer": "A"}],
    )
    stale_id = only["id"]
    store = delete_chat(store, stale_id)
    save_store(store, path)
    store = load_store(path)
    store = upsert_turns(
        store,
        stale_id,
        [{"question": "Q", "answer": "A"}],
    )
    save_store(store, path)
    reloaded = load_store(path)
    assert stale_id not in {conv["id"] for conv in reloaded["conversations"]}
    assert radio_choices(reloaded) == []
    assert active_conversation(reloaded)["turns"] == []


def test_load_store_orphan_active_id_prefers_empty(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    first = active_conversation(store)
    store = upsert_turns(
        store,
        first["id"],
        [{"question": "Keep in file", "answer": "ok"}],
    )
    store = start_new_chat(store)
    blank = active_conversation(store)
    assert blank["id"] != first["id"]
    assert blank["turns"] == []
    save_store(store, path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["active_id"] = "missing-active-id"
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reloaded = load_store(path)
    opened = active_conversation(reloaded)
    assert opened["turns"] == []
    assert opened["id"] != first["id"]


def test_delete_chat_records_tombstone(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    only = active_conversation(store)
    store = upsert_turns(
        store,
        only["id"],
        [{"question": "Q", "answer": "A"}],
    )
    deleted_id = only["id"]
    store = delete_chat(store, deleted_id)
    assert deleted_id in store.get("deleted_ids", [])
    save_store(store, path)
    reloaded = load_store(path)
    assert deleted_id in reloaded.get("deleted_ids", [])


def test_upsert_empty_id_with_questions_uses_active(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    active = active_conversation(store)
    active_id = active["id"]
    before = len(store["conversations"])
    store = upsert_turns(
        store,
        "",
        [{"question": "Hello", "answer": "Hi"}],
    )
    assert len(store["conversations"]) == before
    assert active_conversation(store)["id"] == active_id
    assert active_conversation(store)["turns"][0]["question"] == "Hello"


def test_radio_choices_skips_empty(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = _store(path)
    assert radio_choices(store) == []
    first = active_conversation(store)
    store = upsert_turns(
        store,
        first["id"],
        [{"question": "MIIT ဆိုတာ ဘာလဲ။", "answer": "တက္ကသိုလ်။"}],
    )
    choices = radio_choices(store)
    assert choices == [("MIIT ဆိုတာ ဘာလဲ", first["id"])]
    store = start_new_chat(store)
    assert radio_choices(store) == [("MIIT ဆိုတာ ဘာလဲ", first["id"])]
