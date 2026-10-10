"""On-disk chat store (no Gradio)."""

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
