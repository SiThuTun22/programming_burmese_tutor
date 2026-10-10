#!/usr/bin/env python3
"""Gradio web UI for the Myanmar programming tutor."""

from __future__ import annotations

import html
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

import gradio as gr

from tutor.chats import (
    active_conversation,
    delete_chat,
    load_store,
    radio_choices,
    save_store,
    select_chat,
    start_new_chat,
    upsert_turns,
)
from tutor.config import GRADIO_HOST, GRADIO_PORT, TTS_CACHE_DIR, TTS_ENABLED
from tutor.demo_log import format_answer_metrics, log_human_score, log_session
from tutor.gemini_client import CHAT_FALLBACK_WARNING
from tutor.hybrid import TutorLike, create_engine
from tutor.tts import cached_audio_path, synthesize_sync

ENGINE: TutorLike | None = None

SCORE_CHOICES = ["1", "2", "3", "4", "5"]
TTS_TICK_SECONDS = 0.35
STATIC_DIR = ROOT / "static"
APP_TITLE = "MIIT Programming Tutor"
LOGO_PATH = STATIC_DIR / "miit-logo.png"
BUILDING_PATH = STATIC_DIR / "miit-building.jpg"
LOGO_URL = "/gradio_api/file=" + str(LOGO_PATH.resolve())
BUILDING_URL = "/gradio_api/file=" + str(BUILDING_PATH.resolve())
DELETE_CONFIRM_JS = (
    "(target, conv, hist) => confirm('Delete this chat?') "
    "? [target, conv, hist] : [null, conv, hist]"
)
def _stroke_icon(stroke: str, paths: str) -> str:
    return (
        "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
        f"viewBox='0 0 24 24' fill='none' stroke='{stroke}' stroke-width='2' "
        "stroke-linecap='round' stroke-linejoin='round'%3E"
        f"{paths}%3C/svg%3E\")"
    )


EAR_PATHS = (
    "%3Cpath d='M6 10a7 7 0 1 1 13 3.6 10 10 0 0 1-2 2 8 8 0 0 0-2 3 "
    "4.5 4.5 0 0 1-6.8 1.4'/%3E%3Cpath d='M10 10a3 3 0 1 1 5 2.2'/%3E"
)
TRASH_PATHS = (
    "%3Cpolyline points='3 6 5 6 21 6'/%3E%3Cpath d='M19 6l-1 14a2 2 0 0 1-2 "
    "2H8a2 2 0 0 1-2-2L5 6'/%3E%3Cpath d='M10 11v6M14 11v6'/%3E%3Cpath "
    "d='M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2'/%3E"
)
EAR_ICON = _stroke_icon("%231e3a8a", EAR_PATHS)
EAR_ICON_DARK = _stroke_icon("%2393c5fd", EAR_PATHS)
TRASH_ICON = _stroke_icon("%231e3a8a", TRASH_PATHS)
TRASH_ICON_DARK = _stroke_icon("%2393c5fd", TRASH_PATHS)
LISTEN_RELABEL_JS = """
() => {
  const applyTheme = (mode) => {
    const dark = mode === "Dark";
    document.documentElement.classList.toggle("dark", dark);
    document.body.classList.toggle("dark", dark);
    try { localStorage.setItem("miitTheme", dark ? "Dark" : "Light"); } catch (e) {}
    document.querySelectorAll(".miit-theme [data-theme]").forEach((el) => {
      const on = el.getAttribute("data-theme") === (dark ? "Dark" : "Light");
      el.setAttribute("aria-pressed", on ? "true" : "false");
    });
  };
  let saved = "Light";
  try { saved = localStorage.getItem("miitTheme") || "Light"; } catch (e) {}
  applyTheme(saved);
  document.querySelectorAll(".miit-theme [data-theme]").forEach((el) => {
    el.addEventListener("click", () => applyTheme(el.getAttribute("data-theme")));
  });
  const applyListen = () => {
    document.querySelectorAll(
      'button[aria-label="Like"], button[aria-label="like"], button[aria-label="Liked"]'
    ).forEach((btn) => {
      btn.setAttribute("aria-label", "Listen");
      btn.setAttribute("title", "Listen");
    });
  };
  applyListen();
  new MutationObserver(applyListen).observe(document.body, { childList: true, subtree: true });
}
"""
PROGRESS_CSS = """
@font-face {
  font-family: "TutorUI";
  src: local("Times New Roman"), local("Times");
  unicode-range: U+0000-00FF, U+0100-024F, U+1E00-1EFF, U+2000-206F, U+2070-209F;
}
@font-face {
  font-family: "TutorUI";
  src: local("Myanmar Text"), local("Pyidaungsu"), local("Padauk");
  unicode-range: U+1000-109F, U+AA60-AA7F, U+A9E0-A9FF;
}
.gradio-container,
.gradio-container textarea,
.gradio-container input:not([type="radio"]):not([type="checkbox"]),
.gradio-container .markdown,
.gradio-container .prose,
.gradio-container .miit-header,
.tutor-status-label {
  font-family: "TutorUI", "Times New Roman", Times, "Myanmar Text", serif !important;
}
.gradio-container button.primary,
.gradio-container button.secondary,
.gradio-container button[variant],
.gradio-container .lg.primary,
.gradio-container .lg.secondary {
  font-family: "TutorUI", "Times New Roman", Times, "Myanmar Text", serif !important;
}
.gradio-container svg,
.gradio-container .icon-wrap,
.gradio-container [class*="icon"] {
  color: var(--miit-icon) !important;
  fill: var(--miit-icon) !important;
}
.gradio-container {
  color-scheme: light;
  --miit-accent: #1e3a8a;
  --miit-accent-soft: #eff6ff;
  --miit-text: #0f172a;
  --miit-muted: #334155;
  --miit-placeholder: #64748b;
  --miit-card: rgba(255, 255, 255, 0.96);
  --miit-card-solid: #ffffff;
  --miit-border: #c7d2fe;
  --miit-chat-bg: #f8fafc;
  --miit-bot-bg: #ffffff;
  --miit-bot-text: #0f172a;
  --miit-bot-border: #e2e8f0;
  --miit-user-bg: #1e3a8a;
  --miit-overlay: rgba(241, 247, 255, 0.82);
  --miit-track: #e2e8f0;
  --miit-icon: #1e3a8a;
  --ear-icon: {EAR_ICON};
  --trash-icon: {TRASH_ICON};
  --body-background-fill: var(--miit-chat-bg);
  --background-fill-primary: var(--miit-card-solid);
  --background-fill-secondary: var(--miit-chat-bg);
  --body-text-color: var(--miit-text);
  --block-background-fill: var(--miit-card);
  --input-background-fill: var(--miit-card-solid);
  --input-placeholder-color: var(--miit-placeholder);
  --neutral-800: var(--miit-accent);
  --neutral-950: var(--miit-text);
  color: var(--miit-text);
  width: 100% !important;
  max-width: none !important;
  padding: 16px 24px 32px !important;
  background-image: linear-gradient(var(--miit-overlay), var(--miit-overlay)),
    url("{BUILDING_URL}");
  background-size: cover;
  background-position: center;
}
html.dark,
html.dark body {
  color-scheme: dark;
  background: #0b1220;
}
html.dark .gradio-container,
.dark .gradio-container {
  color-scheme: dark;
  --miit-accent: #93c5fd;
  --miit-accent-soft: #1e3a5f;
  --miit-text: #e2e8f0;
  --miit-muted: #94a3b8;
  --miit-placeholder: #94a3b8;
  --miit-card: #1e293b;
  --miit-card-solid: #1e293b;
  --miit-border: #334155;
  --miit-chat-bg: #0f172a;
  --miit-bot-bg: #1e293b;
  --miit-bot-text: #e2e8f0;
  --miit-bot-border: #334155;
  --miit-user-bg: #1e3a8a;
  --miit-overlay: rgba(8, 12, 24, 0.88);
  --miit-track: #334155;
  --miit-icon: #93c5fd;
  --ear-icon: {EAR_ICON_DARK};
  --trash-icon: {TRASH_ICON_DARK};
}
.gradio-container .block {
  background: var(--miit-card) !important;
  border: 1px solid var(--miit-border) !important;
  border-radius: 12px !important;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18) !important;
  color: var(--miit-text) !important;
}
.gradio-container .block.miit-note {
  margin: 10px 0 !important;
  padding: 10px 14px !important;
  border-radius: 12px !important;
}
.gradio-container .prose.miit-note {
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
.gradio-container .block.miit-note:has(.md:empty) {
  display: none !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  min-height: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
}
.gradio-container .miit-note .md,
.gradio-container .miit-note p {
  margin: 0 !important;
}
.gradio-container button.primary,
.gradio-container button.secondary,
.gradio-container .lg.primary,
.gradio-container .lg.secondary,
.gradio-container .sm.primary,
.gradio-container .sm.secondary {
  border-radius: 12px !important;
}
.gradio-container fieldset,
.gradio-container .radio-container,
.gradio-container .form,
.gradio-container ul.options,
.gradio-container .miit-listen,
.gradio-container audio {
  border-radius: 12px !important;
}
.gradio-container .miit-thread .label-wrap,
.gradio-container .miit-composer .label-wrap,
.gradio-container .block:has(.miit-thread) .label-wrap,
.gradio-container .block:has(.miit-composer) .label-wrap {
  display: none !important;
}
.miit-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 4px 0 16px;
  padding: 8px 4px 4px;
}
.miit-logo {
  height: 56px;
  width: auto;
  max-width: 220px;
  object-fit: contain;
  flex-shrink: 0;
}
.miit-header-copy {
  flex: 1 1 auto;
  min-width: 0;
}
.miit-header h1 {
  margin: 0;
  font-size: 1.45rem;
  line-height: 1.25;
  color: var(--miit-accent);
}
.miit-sub {
  margin: 4px 0 0;
  color: var(--miit-muted);
  font-size: 0.95rem;
}
.gradio-container .block:has(.miit-header) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
.miit-theme {
  display: inline-flex;
  flex-shrink: 0;
  align-items: stretch;
  margin-left: auto;
  height: 36px;
  padding: 3px;
  gap: 2px;
  border: 1px solid var(--miit-border);
  border-radius: 999px;
  overflow: hidden;
  background: var(--miit-accent-soft);
}
.gradio-container .miit-theme button,
.gradio-container .miit-theme button.primary,
.gradio-container .miit-theme button.secondary {
  flex: 1 1 auto;
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  color: var(--miit-muted) !important;
  padding: 0 16px !important;
  font-size: 0.85rem !important;
  line-height: 1 !important;
  min-height: 0 !important;
  height: auto !important;
  border-radius: 999px !important;
  cursor: pointer;
}
.gradio-container .miit-theme button[aria-pressed="true"] {
  background: #1e3a8a !important;
  color: #ffffff !important;
}
.miit-sidebar {
  min-width: 220px;
  max-width: 240px;
}
.miit-sidebar .block {
  box-shadow: none !important;
  background: var(--miit-card) !important;
}
.gradio-container .miit-chats {
  font-size: 0.9rem;
}
.miit-chat-row {
  display: flex !important;
  align-items: center;
  gap: 4px;
  margin: 0 0 4px !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
.miit-chat-row .block {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
.miit-sidebar .miit-chat-open {
  flex: 1 1 auto;
  min-width: 0 !important;
  justify-content: flex-start !important;
  text-align: left !important;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.85rem !important;
  padding: 6px 8px !important;
}
.miit-sidebar .miit-chat-del {
  width: 32px !important;
  min-width: 32px !important;
  max-width: 32px !important;
  height: 32px !important;
  padding: 4px !important;
  flex: 0 0 32px !important;
  font-size: 0 !important;
  line-height: 0 !important;
  background-color: var(--miit-accent-soft) !important;
  background-image: var(--trash-icon) !important;
  background-repeat: no-repeat !important;
  background-position: center !important;
  background-size: 16px 16px !important;
}
.miit-sidebar .miit-chat-del img {
  display: none !important;
}
.miit-sidebar .miit-chat-del .button-text,
.miit-sidebar .miit-chat-del span:not(.button-icon) {
  display: none !important;
}
.miit-chat-row textarea {
  display: none !important;
}
@media (max-width: 640px) {
  .miit-header { flex-wrap: wrap; }
  .miit-logo { height: 40px; }
  .miit-header h1 { font-size: 1.15rem; }
  .miit-theme { margin-left: 0; }
  .miit-sidebar {
    min-width: 100%;
    max-width: none;
  }
}
.tutor-status { margin: 4px 0 10px; }
.tutor-status-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--miit-muted);
  margin-bottom: 6px;
}
.tutor-status-track {
  height: 10px;
  background: var(--miit-track);
  border-radius: 999px;
  overflow: hidden;
}
.tutor-status-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--miit-accent), #2563eb);
  transition: width 0.35s ease;
}
.tutor-status-fill.indeterminate {
  width: 38% !important;
  animation: tutor-indeterminate 1.2s ease-in-out infinite;
}
@keyframes tutor-indeterminate {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(280%); }
}
.gradio-container .block:has(.miit-thread),
.gradio-container .miit-thread,
.gradio-container .block:has(.chatbot),
.gradio-container span.chatbot,
.gradio-container .chatbot,
.gradio-container [data-testid="chatbot"] {
  height: 72vh !important;
  min-height: 72vh !important;
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
}
.gradio-container .chatbot,
.gradio-container [data-testid="chatbot"],
.gradio-container .chatbot > .wrapper,
.gradio-container .chatbot .bubble-wrap,
.gradio-container .chatbot .message-wrap,
.gradio-container .chatbot .placeholder-content {
  background: var(--miit-chat-bg) !important;
  color: var(--miit-text) !important;
  max-width: 100%;
}
.gradio-container .miit-thread [aria-label="Copy"],
.gradio-container .miit-thread [aria-label="Copy message"],
.gradio-container .miit-thread [aria-label="Copy conversation"],
.gradio-container .miit-thread [aria-label="Share"],
.gradio-container .miit-thread [aria-label="Clear"],
.gradio-container .miit-thread .resize-handle,
.gradio-container .miit-thread .top-panel {
  display: none !important;
}
.gradio-container .miit-thread .message-buttons {
  position: static !important;
  justify-content: flex-start !important;
  margin-top: 2px !important;
}
.gradio-container .miit-thread button[aria-label="Like"],
.gradio-container .miit-thread button[aria-label="like"],
.gradio-container .miit-thread button[aria-label="Liked"],
.gradio-container .miit-thread button[aria-label="Listen"] {
  width: 32px !important;
  min-width: 32px !important;
  max-width: 32px !important;
  height: 32px !important;
  padding: 4px !important;
  margin: 2px 0 8px !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  background-color: transparent !important;
  background-image: var(--ear-icon) !important;
  background-repeat: no-repeat !important;
  background-position: center !important;
  background-size: 20px 20px !important;
  font-size: 0 !important;
  line-height: 0 !important;
  --border-color: transparent !important;
}
.gradio-container .miit-thread button[aria-label="Like"] svg,
.gradio-container .miit-thread button[aria-label="like"] svg,
.gradio-container .miit-thread button[aria-label="Liked"] svg,
.gradio-container .miit-thread button[aria-label="Listen"] svg,
.gradio-container .miit-thread button[aria-label="Like"] img,
.gradio-container .miit-thread button[aria-label="like"] img,
.gradio-container .miit-thread button[aria-label="Liked"] img,
.gradio-container .miit-thread button[aria-label="Listen"] img {
  opacity: 0 !important;
  width: 0 !important;
  height: 0 !important;
}
.gradio-container .miit-listen {
  margin: 8px 0 4px !important;
}
.gradio-container .chatbot .placeholder,
.gradio-container .chatbot .placeholder-content,
.gradio-container .chatbot .placeholder p {
  color: var(--miit-placeholder) !important;
  background: transparent !important;
}
.gradio-container .message,
.gradio-container .bubble-wrap {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.gradio-container .user,
.gradio-container .message.user,
.gradio-container [data-testid="user"] .bubble-content,
.gradio-container .user .message,
.gradio-container .user .bubble {
  background: var(--miit-user-bg) !important;
  color: #ffffff !important;
  border-color: var(--miit-user-bg) !important;
  border-radius: 16px !important;
}
.gradio-container .bot,
.gradio-container .message.bot,
.gradio-container [data-testid="bot"] .bubble-content,
.gradio-container .bot .message,
.gradio-container .bot .bubble {
  background: var(--miit-bot-bg) !important;
  color: var(--miit-bot-text) !important;
  border: 1px solid var(--miit-bot-border) !important;
  border-radius: 16px !important;
}
.gradio-container .block:has(.miit-composer) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
.gradio-container .miit-composer textarea,
.gradio-container textarea,
.gradio-container input[type="text"] {
  background: var(--miit-card-solid) !important;
  color: var(--miit-text) !important;
  border: 1px solid var(--miit-border) !important;
  border-radius: 20px !important;
  padding: 12px 16px !important;
}
.gradio-container textarea::placeholder,
.gradio-container input::placeholder {
  color: var(--miit-placeholder) !important;
  opacity: 1 !important;
}
.gradio-container .markdown,
.gradio-container .prose,
.gradio-container label,
.gradio-container .label-wrap span {
  color: var(--miit-text) !important;
}
@media (max-width: 640px) {
  .gradio-container { padding: 12px 12px 24px !important; }
  .gradio-container .block:has(.chatbot),
  .gradio-container span.chatbot,
  .gradio-container .chatbot {
    height: 55vh !important;
    min-height: 55vh !important;
  }
}
""".replace("{BUILDING_URL}", BUILDING_URL).replace("{EAR_ICON}", EAR_ICON).replace(
    "{EAR_ICON_DARK}", EAR_ICON_DARK
).replace("{TRASH_ICON}", TRASH_ICON).replace("{TRASH_ICON_DARK}", TRASH_ICON_DARK)


def status_bar(label: str, percent: int | None = None) -> str:
    if not label:
        return ""
    safe = html.escape(label)
    if percent is None:
        fill = '<div class="tutor-status-fill indeterminate"></div>'
        pct = ""
    else:
        width = max(0, min(100, int(percent)))
        fill = f'<div class="tutor-status-fill" style="width:{width}%"></div>'
        pct = f"<span>{width}%</span>"
    return (
        '<div class="tutor-status">'
        f'<div class="tutor-status-label"><span>{safe}</span>{pct}</div>'
        f'<div class="tutor-status-track">{fill}</div>'
        "</div>"
    )


def _using_chat_fallback() -> bool:
    fn = getattr(ENGINE, "_generate_fn", None)
    client = getattr(fn, "__self__", None)
    return bool(getattr(client, "using_chat_fallback", False))


def _finish_status() -> str:
    if _using_chat_fallback():
        return status_bar(CHAT_FALLBACK_WARNING, 100)
    return ""


def _error_answer(err_msg: str) -> str:
    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
        return (
            "⚠️ API Rate limit သို့မဟုတ် Quota ပြည့်သွားပါသည်။ "
            "ခေတ္တ စက္ကန့်အနည်းငယ် စောင့်ဆိုင်းပြီးမှ ပြန်လည် မေးမြန်းပေးပါ။"
        )
    if "503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg:
        return (
            "⚠️ Model အခု အလုပ်များနေပါသည်။ "
            "ခဏနေပြီး ပြန်လည် မေးမြန်းပေးပါ။"
        )
    if "404" in err_msg:
        return (
            "⚠️ သတ်မှတ်ထားသော Model ကို ရှာမတွေ့ပါ။ "
            ".env ထဲရှိ GEMINI_MODEL ကို ပြန်လည် စစ်ဆေးပေးပါ။"
        )
    return (
        "⚠️ အဖြေ ထုတ်ယူရာတွင် အမှားတစ်ခု ဖြစ်ပေါ်ခဲ့ပါသည်။ "
        "VPN သို့မဟုတ် အင်တာနက် လိုင်းကို စစ်ဆေးပြီး ထပ်မံ ကြိုးစားကြည့်ပါ။"
    )


CODE_SNIPPET_HINTS = ("def ", "function ", "```", "{")


def code_from_ask(text: str) -> str:
    stripped = text.strip()
    lowered = stripped.lower()
    if any(hint in lowered or hint in stripped for hint in CODE_SNIPPET_HINTS):
        return stripped
    return ""


def history_to_messages(history: list[dict] | None) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for turn in history or []:
        question = str(turn.get("question", "")).strip()
        answer = str(turn.get("answer", "")).strip()
        if question:
            messages.append({"role": "user", "content": question})
        if answer:
            messages.append({"role": "assistant", "content": answer})
    return messages


def message_text_from_like(like_data: object) -> str:
    value = getattr(like_data, "value", like_data)
    if isinstance(value, dict):
        for key in ("text", "content"):
            raw = value.get(key)
            if raw:
                return str(raw).strip()
        return ""
    return str(value or "").strip()


def _chat_rows(store: dict) -> list[tuple[str, str]]:
    return radio_choices(store)


def _persist(conv_id: str | None, history: list[dict] | None) -> dict:
    store = load_store()
    store = upsert_turns(store, conv_id, history)
    save_store(store)
    return store


def _audio_update(path: str | None) -> object:
    if path:
        return gr.update(value=path, visible=True)
    return gr.update(value=None, visible=False)


def respond(
    question: str,
    history: list[dict] | None,
    conversation_id: str | None,
) -> Iterator[
    tuple[
        list[dict[str, str]],
        str,
        str,
        object,
        str | object,
        list[dict],
        str | object,
        str,
        str,
        object,
    ]
]:
    history = list(history or [])
    conv_id = (conversation_id or "").strip()
    asked = (question or "").strip()
    thread = history_to_messages(history)
    hidden = _audio_update(None)
    if not asked:
        yield (
            thread,
            question,
            "",
            hidden,
            "",
            history,
            "",
            status_bar("မေးခွန်း ထည့်ပါ။"),
            conv_id,
            gr.skip(),
        )
        return
    code = code_from_ask(asked)
    assert ENGINE is not None
    yield (
        thread,
        asked,
        gr.skip(),
        hidden,
        gr.skip(),
        history,
        gr.skip(),
        status_bar("Generating answer…"),
        conv_id,
        gr.skip(),
    )
    prior_turns = len(history)
    try:
        answer = ENGINE.answer(asked, code, history=history)
    except Exception as exc:
        err_msg = str(exc)
        print(f"serve_gradio error: {err_msg}", file=sys.stderr)
        answer = _error_answer(err_msg)
        history.append({"question": asked, "answer": answer})
        store = _persist(conv_id, history)
        conv_id = store["active_id"]
        yield (
            history_to_messages(history),
            "",
            answer,
            hidden,
            "",
            history,
            "",
            "",
            conv_id,
            _chat_rows(store),
        )
        return

    turn_id = uuid.uuid4().hex
    log_session(
        turn_id=turn_id,
        question=asked,
        code=code,
        answer=answer,
        prior_turns=prior_turns,
    )
    history.append({"question": asked, "answer": answer})
    store = _persist(conv_id, history)
    conv_id = store["active_id"]
    thread = history_to_messages(history)
    metrics = format_answer_metrics(answer)
    yield (
        thread,
        "",
        answer,
        hidden,
        metrics,
        history,
        turn_id,
        status_bar("Done", 100),
        conv_id,
        _chat_rows(store),
    )
    yield (
        thread,
        "",
        answer,
        hidden,
        metrics,
        history,
        turn_id,
        _finish_status(),
        conv_id,
        gr.skip(),
    )


def play_history_turn(
    like_data: gr.LikeData,
    voice: str | None = None,
) -> Iterator[tuple[object, str, str]]:
    text = message_text_from_like(like_data)
    hidden = _audio_update(None)
    if not TTS_ENABLED or not text or text.startswith("⚠️") or text == "မေးခွန်း ထည့်ပါ။":
        yield hidden, text, ""
        return
    gender = voice or "female"
    hit = cached_audio_path(text, gender)
    if hit:
        yield _audio_update(hit), text, ""
        return
    yield gr.skip(), text, status_bar("Generating speech…", 40)
    time.sleep(TTS_TICK_SECONDS)
    yield gr.skip(), text, status_bar("Generating speech…", 70)
    try:
        path = synthesize_sync(text, voice=gender)
    except Exception as tts_err:
        print(f"TTS error: {tts_err}", file=sys.stderr)
        yield hidden, text, ""
        return
    if path:
        yield _audio_update(path), text, ""
        return
    yield hidden, text, ""


def respeak(
    answer: str, voice: str | None
) -> Iterator[tuple[object, str]]:
    text = (answer or "").strip()
    hidden = _audio_update(None)
    if not TTS_ENABLED:
        yield hidden, ""
        return
    if not text or text.startswith("⚠️") or text == "မေးခွန်း ထည့်ပါ။":
        yield hidden, ""
        return
    gender = voice or "female"
    hit = cached_audio_path(text, gender)
    if hit:
        yield _audio_update(hit), ""
        return
    yield gr.skip(), status_bar("Generating speech…", 40)
    time.sleep(TTS_TICK_SECONDS)
    yield gr.skip(), status_bar("Generating speech…", 70)
    try:
        path = synthesize_sync(text, voice=gender)
    except Exception as tts_err:
        print(f"TTS error: {tts_err}", file=sys.stderr)
        yield hidden, ""
        return
    if path:
        yield _audio_update(path), ""
        return
    yield hidden, ""


def _open_session(store: dict) -> tuple[list, str, str, object, str, list, str, str, str, object]:
    active = active_conversation(store)
    history = list(active["turns"])
    return (
        history_to_messages(history),
        "",
        "",
        _audio_update(None),
        "",
        history,
        "",
        "",
        active["id"],
        _chat_rows(store),
    )


def on_new_chat(
    conversation_id: str | None,
    history: list[dict] | None,
) -> tuple[list, str, str, None, str, list, str, str, str, object]:
    store = _persist(conversation_id, history)
    store = start_new_chat(store)
    save_store(store)
    return _open_session(store)


def on_select_chat(
    selected: str | None,
    conversation_id: str | None,
    history: list[dict] | None,
) -> tuple[list, str, str, None, str, list, str, str, str, object] | object:
    chosen = (selected or "").strip()
    current = (conversation_id or "").strip()
    if not chosen or chosen == current:
        return (
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
        )
    store = _persist(current, history)
    store = select_chat(store, chosen)
    save_store(store)
    return _open_session(store)


def on_delete_chat(
    target: str | None,
    conversation_id: str | None,
    history: list[dict] | None,
) -> tuple[list, str, str, None, str, list, str, str, str, object]:
    chosen = (target or "").strip()
    if not chosen:
        return (
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            gr.skip(),
        )
    store = load_store()
    if chosen != (conversation_id or "").strip():
        store = upsert_turns(store, conversation_id, history)
    store = delete_chat(store, chosen)
    save_store(store)
    return _open_session(store)


def save_score(turn_id: str, fluency: str, correctness: str, beginner: str) -> str:
    if not (turn_id or "").strip():
        return "Ask a question before saving a score."
    log_human_score(
        turn_id=turn_id.strip(),
        fluency=int(fluency),
        correctness=int(correctness),
        beginner=int(beginner),
    )
    return "Score saved."


def main() -> None:
    global ENGINE
    print("Loading tutor (hybrid)...", flush=True)
    ENGINE = create_engine()
    print("Tutor ready.", flush=True)

    with gr.Blocks(title=APP_TITLE) as demo:
        startup = load_store()
        active = active_conversation(startup)
        gr.HTML(
            f'<div class="miit-header">'
            f'<img class="miit-logo" src="{html.escape(LOGO_URL)}" '
            f'alt="MIIT logo" />'
            f'<div class="miit-header-copy">'
            f"<h1>{html.escape(APP_TITLE)}</h1>"
            f'<p class="miit-sub">Follow-ups stay in this chat. Past chats are in the sidebar.</p>'
            f"</div>"
            f'<div class="miit-theme" role="group" aria-label="Theme">'
            f'<button type="button" data-theme="Light" aria-pressed="true">Light</button>'
            f'<button type="button" data-theme="Dark" aria-pressed="false">Dark</button>'
            f"</div></div>"
        )
        history = gr.State(list(active["turns"]))
        conversation_id = gr.State(active["id"])
        chat_rows = gr.State(_chat_rows(startup))
        turn_id = gr.State("")
        last_answer = gr.State("")
        session_outputs: list = []
        with gr.Row():
            with gr.Column(scale=0, min_width=220, elem_classes=["miit-sidebar"]):
                new_chat_btn = gr.Button("New chat", variant="primary")

                @gr.render(
                    inputs=[chat_rows, conversation_id],
                    show_progress="hidden",
                )
                def render_chat_rows(rows, active_id):
                    for title, cid in rows or []:
                        with gr.Row(elem_classes=["miit-chat-row"]):
                            open_btn = gr.Button(
                                title,
                                variant=(
                                    "primary"
                                    if cid == active_id
                                    else "secondary"
                                ),
                                size="sm",
                                elem_classes=["miit-chat-open"],
                                key=f"open-{cid}",
                                preserved_by_key=[],
                            )
                            open_btn.click(
                                fn=lambda conv_id, hist, _cid=cid: on_select_chat(
                                    _cid, conv_id, hist
                                ),
                                inputs=[conversation_id, history],
                                outputs=session_outputs,
                                show_progress=False,
                            )
                            if cid != active_id:
                                del_btn = gr.Button(
                                    "",
                                    size="sm",
                                    elem_classes=["miit-chat-del"],
                                    key=f"del-{cid}",
                                )
                                del_btn.click(
                                    fn=on_delete_chat,
                                    inputs=[
                                        gr.Textbox(
                                            value=cid,
                                            visible=False,
                                            key=f"del-id-{cid}",
                                        ),
                                        conversation_id,
                                        history,
                                    ],
                                    outputs=session_outputs,
                                    js=DELETE_CONFIRM_JS,
                                    show_progress=False,
                                )

            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                    value=history_to_messages(active["turns"]),
                    show_label=False,
                    container=False,
                    height="72vh",
                    layout="bubble",
                    autoscroll=True,
                    buttons=[],
                    resizable=False,
                    feedback_options=["Like"],
                    like_user_message=False,
                    placeholder="Ask a follow-up anytime. Past chats stay in the sidebar.",
                    elem_classes=["miit-thread"],
                )
                status = gr.HTML()
                question = gr.Textbox(
                    show_label=False,
                    lines=2,
                    placeholder="Message MIIT… MIIT ဆိုတာ ဘာလဲ။ Code ရှိရင် ဒီအကွက်ထဲမှာပဲ ကူးထည့်ပါ။",
                    elem_classes=["miit-composer"],
                )
                ask_btn = gr.Button("Ask", variant="primary")
                tts_gender = gr.Radio(
                    choices=["Male", "Female"],
                    value="Female",
                    label="Voice",
                    interactive=TTS_ENABLED,
                )
                audio = gr.Audio(
                    show_label=False,
                    type="filepath",
                    autoplay=True,
                    visible=False,
                    elem_classes=["miit-listen"],
                )
                metrics = gr.Markdown(elem_classes=["miit-note"])
                gr.Markdown(
                    "Score this answer (1–5) for the report.",
                    elem_classes=["miit-note"],
                )
                with gr.Row():
                    fluency = gr.Dropdown(SCORE_CHOICES, value="3", label="Fluency")
                    correctness = gr.Dropdown(
                        SCORE_CHOICES, value="3", label="Correctness"
                    )
                    beginner = gr.Dropdown(
                        SCORE_CHOICES, value="3", label="Easy for a beginner"
                    )
                save_btn = gr.Button("Save score")
                score_status = gr.Markdown(elem_classes=["miit-note"])
        session_outputs.extend(
            [
                chatbot,
                question,
                last_answer,
                audio,
                metrics,
                history,
                turn_id,
                status,
                conversation_id,
                chat_rows,
            ]
        )
        ask_btn.click(
            fn=respond,
            inputs=[question, history, conversation_id],
            outputs=session_outputs,
            show_progress=False,
        )
        question.submit(
            fn=respond,
            inputs=[question, history, conversation_id],
            outputs=session_outputs,
            show_progress=False,
        )
        chatbot.like(
            fn=play_history_turn,
            inputs=[tts_gender],
            outputs=[audio, last_answer, status],
            show_progress=False,
        )
        tts_gender.change(
            fn=respeak,
            inputs=[last_answer, tts_gender],
            outputs=[audio, status],
            show_progress=False,
        )
        new_chat_btn.click(
            fn=on_new_chat,
            inputs=[conversation_id, history],
            outputs=session_outputs,
            show_progress=False,
        )
        save_btn.click(
            fn=save_score,
            inputs=[turn_id, fluency, correctness, beginner],
            outputs=[score_status],
        )

    demo.queue(default_concurrency_limit=1)
    demo.launch(
        server_name=GRADIO_HOST,
        server_port=GRADIO_PORT,
        favicon_path=str(LOGO_PATH),
        share=False,
        show_error=True,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
        ),
        css=PROGRESS_CSS,
        js=LISTEN_RELABEL_JS,
        allowed_paths=[str(STATIC_DIR), str(TTS_CACHE_DIR)],
    )


if __name__ == "__main__":
    main()
