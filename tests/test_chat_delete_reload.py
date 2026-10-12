"""Delete chat and reload from disk (Gradio hydrate path)."""

from pathlib import Path

from tutor.chats import (
    active_conversation,
    delete_chat,
    load_store,
    mutate_store,
    radio_choices,
    save_store,
    upsert_turns,
)


def test_mutate_store_serializes_delete(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "chats.json"
    monkeypatch.setattr("tutor.chats.CHATS_PATH", path)
    store = load_store(path)
    only = active_conversation(store)
    mutate_store(
        lambda s: upsert_turns(
            s,
            only["id"],
            [{"question": "Q", "answer": "A"}],
        ),
        path,
    )
    deleted_id = only["id"]
    mutate_store(lambda s: delete_chat(s, deleted_id), path)
    reloaded = load_store(path)
    assert deleted_id not in {c["id"] for c in reloaded["conversations"]}
    assert deleted_id in reloaded.get("deleted_ids", [])
    assert radio_choices(reloaded) == []


def test_save_store_persists_deleted_ids(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    store = load_store(path)
    only = active_conversation(store)
    store = delete_chat(
        upsert_turns(
            store,
            only["id"],
            [{"question": "x", "answer": "y"}],
        ),
        only["id"],
    )
    save_store(store, path)
    raw = path.read_text(encoding="utf-8")
    assert "deleted_ids" in raw
    reloaded = load_store(path)
    assert only["id"] in reloaded.get("deleted_ids", [])
