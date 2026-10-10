"""Local conversation list for the Gradio sidebar (one file on this machine)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.config import ROOT

CHATS_PATH = ROOT / "results" / "chats.json"
NEW_TITLE = "New chat"
TITLE_MAX = 32
_TITLE_TRAILING = "။?!.,;:…"

Store = dict[str, Any]
Conversation = dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex


def conversation_title(turns: list[dict] | None) -> str:
    for turn in turns or []:
        asked = str(turn.get("question") or "").strip().rstrip(_TITLE_TRAILING).strip()
        if asked:
            if len(asked) > TITLE_MAX:
                return asked[:TITLE_MAX].rstrip() + "…"
            return asked
    return NEW_TITLE


def empty_conversation() -> Conversation:
    return {
        "id": new_id(),
        "title": NEW_TITLE,
        "updated": utc_now(),
        "turns": [],
    }


def empty_store() -> Store:
    conv = empty_conversation()
    return {"active_id": conv["id"], "conversations": [conv]}


def _normalize_turn(turn: dict) -> dict[str, str]:
    return {
        "question": str(turn.get("question") or "").strip(),
        "answer": str(turn.get("answer") or "").strip(),
    }


def _normalize_conversation(raw: dict) -> Conversation:
    turns = [
        _normalize_turn(item)
        for item in raw.get("turns") or []
        if isinstance(item, dict)
    ]
    return {
        "id": str(raw.get("id") or "").strip() or new_id(),
        "title": conversation_title(turns),
        "updated": str(raw.get("updated") or "").strip() or utc_now(),
        "turns": turns,
    }


def load_store(path: Path | None = None) -> Store:
    target = path or CHATS_PATH
    if not target.is_file():
        store = empty_store()
        save_store(store, target)
        return store
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        store = empty_store()
        save_store(store, target)
        return store
    if not isinstance(data, dict):
        store = empty_store()
        save_store(store, target)
        return store
    conversations: list[Conversation] = []
    for item in data.get("conversations") or []:
        if isinstance(item, dict):
            conversations.append(_normalize_conversation(item))
    if not conversations:
        store = empty_store()
        save_store(store, target)
        return store
    active = str(data.get("active_id") or "").strip()
    ids = {conv["id"] for conv in conversations}
    if active not in ids:
        active = conversations[0]["id"]
    return {"active_id": active, "conversations": conversations}


def save_store(store: Store, path: Path | None = None) -> None:
    target = path or CHATS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "active_id": store["active_id"],
        "conversations": store["conversations"],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(target)


def get_conversation(store: Store, conv_id: str | None) -> Conversation | None:
    if not conv_id:
        return None
    for conv in store["conversations"]:
        if conv["id"] == conv_id:
            return conv
    return None


def active_conversation(store: Store) -> Conversation:
    conv = get_conversation(store, str(store.get("active_id") or ""))
    if conv is not None:
        return conv
    store["active_id"] = store["conversations"][0]["id"]
    return store["conversations"][0]


def radio_choices(store: Store) -> list[tuple[str, str]]:
    ordered = sorted(
        store["conversations"],
        key=lambda conv: str(conv.get("updated") or ""),
        reverse=True,
    )
    choices: list[tuple[str, str]] = []
    for conv in ordered:
        turns = conv.get("turns") or []
        if not any(str(turn.get("question") or "").strip() for turn in turns):
            continue
        choices.append((str(conv["title"]), str(conv["id"])))
    return choices


def upsert_turns(
    store: Store,
    conv_id: str | None,
    turns: list[dict] | None,
) -> Store:
    normalized = [_normalize_turn(turn) for turn in turns or []]
    conv = get_conversation(store, conv_id)
    if conv is None:
        conv = empty_conversation()
        if conv_id:
            conv["id"] = conv_id
        store["conversations"].append(conv)
    conv["turns"] = normalized
    conv["title"] = conversation_title(normalized)
    conv["updated"] = utc_now()
    store["active_id"] = conv["id"]
    return store


def start_new_chat(store: Store) -> Store:
    active = active_conversation(store)
    if not active["turns"]:
        store["active_id"] = active["id"]
        return store
    conv = empty_conversation()
    store["conversations"].append(conv)
    store["active_id"] = conv["id"]
    return store


def select_chat(store: Store, conv_id: str | None) -> Store:
    conv = get_conversation(store, conv_id)
    if conv is not None:
        store["active_id"] = conv["id"]
    return store


def delete_chat(store: Store, conv_id: str | None) -> Store:
    if not conv_id:
        return store
    was_active = store.get("active_id") == conv_id
    remaining = [conv for conv in store["conversations"] if conv["id"] != conv_id]
    if not remaining:
        empty = empty_conversation()
        store["conversations"] = [empty]
        store["active_id"] = empty["id"]
        return store
    store["conversations"] = remaining
    if was_active or get_conversation(store, str(store.get("active_id") or "")) is None:
        newest = max(remaining, key=lambda conv: str(conv.get("updated") or ""))
        store["active_id"] = newest["id"]
    return store
