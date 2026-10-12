"""Local conversation list for the Gradio sidebar (one file on this machine)."""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.config import ROOT

CHATS_PATH = ROOT / "results" / "chats.json"
NEW_TITLE = "New chat"
TITLE_MAX = 32
_TITLE_TRAILING = "။?!.,;:…"
_DELETED_IDS_MAX = 200

Store = dict[str, Any]
Conversation = dict[str, Any]

_store_lock = threading.Lock()


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
    return {"active_id": conv["id"], "conversations": [conv], "deleted_ids": []}


_TURN_META_KEYS = (
    "conversation_id",
    "turn_id",
    "tts_id",
    "tts_voice",
    "audio_message_id",
)


def _has_questions(turns: list[dict] | None) -> bool:
    return any(str(turn.get("question") or "").strip() for turn in turns or [])


def _normalize_turn(turn: dict) -> dict[str, str]:
    out: dict[str, str] = {
        "question": str(turn.get("question") or "").strip(),
        "answer": str(turn.get("answer") or "").strip(),
    }
    for key in _TURN_META_KEYS:
        raw = str(turn.get(key) or "").strip()
        if raw:
            out[key] = raw
    return out


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


def _normalize_deleted_ids(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        cid = str(item or "").strip()
        if not cid or cid in seen:
            continue
        out.append(cid)
        seen.add(cid)
    return out[-_DELETED_IDS_MAX:]


def _tombstone(store: Store, conv_id: str) -> None:
    cid = str(conv_id or "").strip()
    if not cid:
        return
    deleted = _normalize_deleted_ids(store.get("deleted_ids"))
    if cid not in deleted:
        deleted.append(cid)
    store["deleted_ids"] = deleted[-_DELETED_IDS_MAX:]


def _is_tombstoned(store: Store, conv_id: str) -> bool:
    cid = str(conv_id or "").strip()
    if not cid:
        return False
    return cid in set(_normalize_deleted_ids(store.get("deleted_ids")))


def _ensure_deleted_ids(store: Store) -> None:
    store["deleted_ids"] = _normalize_deleted_ids(store.get("deleted_ids"))


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
        empty_ids = [
            conv["id"]
            for conv in conversations
            if not _has_questions(conv.get("turns"))
        ]
        if empty_ids:
            active = empty_ids[-1]
        else:
            blank = empty_conversation()
            conversations.append(blank)
            active = blank["id"]
    deleted_ids = _normalize_deleted_ids(data.get("deleted_ids"))
    return {
        "active_id": active,
        "conversations": conversations,
        "deleted_ids": deleted_ids,
    }


def save_store(store: Store, path: Path | None = None) -> None:
    target = path or CHATS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    _ensure_deleted_ids(store)
    payload = {
        "active_id": store["active_id"],
        "conversations": store["conversations"],
        "deleted_ids": store.get("deleted_ids") or [],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(target)


def mutate_store(
    fn: Callable[[Store], Store],
    path: Path | None = None,
) -> Store:
    """Load, mutate, and save under a process-wide lock."""
    with _store_lock:
        store = load_store(path)
        store = fn(store)
        save_store(store, path)
        return store


def get_conversation(store: Store, conv_id: str | None) -> Conversation | None:
    if not conv_id:
        return None
    for conv in store["conversations"]:
        if conv["id"] == conv_id:
            return conv
    return None


def active_conversation(store: Store) -> Conversation:
    active_id = str(store.get("active_id") or "").strip()
    conv = get_conversation(store, active_id)
    if conv is not None:
        return conv
    for item in store.get("conversations") or []:
        turns = item.get("turns") or []
        if not _has_questions(turns):
            store["active_id"] = item["id"]
            return item
    blank = empty_conversation()
    store.setdefault("conversations", []).append(blank)
    store["active_id"] = blank["id"]
    return blank


def radio_choices(store: Store) -> list[tuple[str, str]]:
    ordered = sorted(
        store["conversations"],
        key=lambda conv: str(conv.get("updated") or ""),
        reverse=True,
    )
    choices: list[tuple[str, str]] = []
    for conv in ordered:
        turns = conv.get("turns") or []
        if not _has_questions(turns):
            continue
        choices.append((str(conv["title"]), str(conv["id"])))
    return choices


def upsert_turns(
    store: Store,
    conv_id: str | None,
    turns: list[dict] | None,
) -> Store:
    normalized = [_normalize_turn(turn) for turn in turns or []]
    cid = str(conv_id or "").strip()
    if cid and _is_tombstoned(store, cid):
        return store
    conv = get_conversation(store, cid) if cid else None
    if conv is None:
        if cid:
            return store
        if normalized and _has_questions(normalized):
            conv = active_conversation(store)
        else:
            conv = empty_conversation()
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


def finalize_after_delete(store: Store) -> Store:
    """One empty active shell; keep conversations that still have messages."""
    active = active_conversation(store)
    active_id = str(active["id"])
    if not _has_questions(active.get("turns")):
        shell = active
    else:
        shell = empty_conversation()
        store["conversations"].append(shell)
        active_id = str(shell["id"])
    kept: list[Conversation] = []
    for conv in store.get("conversations") or []:
        if _has_questions(conv.get("turns")):
            kept.append(conv)
    kept.append(shell)
    store["conversations"] = kept
    store["active_id"] = active_id
    return store


def delete_chat(store: Store, conv_id: str | None) -> Store:
    if not conv_id:
        return store
    _tombstone(store, conv_id)
    was_active = store.get("active_id") == conv_id
    remaining = [conv for conv in store["conversations"] if conv["id"] != conv_id]
    if not remaining:
        empty = empty_conversation()
        store["conversations"] = [empty]
        store["active_id"] = empty["id"]
        return finalize_after_delete(store)
    store["conversations"] = remaining
    if was_active:
        empty = empty_conversation()
        store["conversations"].append(empty)
        store["active_id"] = empty["id"]
        return finalize_after_delete(store)
    if get_conversation(store, str(store.get("active_id") or "")) is None:
        newest = max(remaining, key=lambda conv: str(conv.get("updated") or ""))
        store["active_id"] = newest["id"]
    return store

