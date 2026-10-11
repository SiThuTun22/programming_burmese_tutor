"""Ask-time route classifier (GEMINI_TTS_NAMES_API_KEY only)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path

from tutor.config import GEMINI_TTS_NAMES_API_KEY, ROOT
from tutor.knowledge import looks_like_miit

logger = logging.getLogger(__name__)

RouteGenerateFn = Callable[..., str]

ROUTES = frozenset({"miit", "programming", "other"})
OUT_OF_SCOPE_ANSWER = (
    "ဒီမေးခွန်းက MIIT / တက္ကသိုလ်အချက်အလက်၊ "
    "သို့မဟုတ် ကွန်ပျူတာအင်ဂျင်နီယာ (CSE/ECE) ဘာသာရပ် အပြင်ဘက် ဖြစ်ပါတယ်။ "
    "အဲဒီအထဲက တစ်ခုကိုပဲ မေးပေးပါ။"
)
FOLLOW_HINTS = (
    "သူမ",
    "သူ",
    "အဲဒါ",
    "ဒီ",
    "more",
    "also",
    "ဘာတွေ",
    "ဘယ်လို",
    "အပို",
    "ရှိသေး",
    "နောက်",
    "else",
    "အသေးစိတ်",
)
SHORT_FOLLOWUP_CHARS = 48


def looks_like_followup(question: str) -> bool:
    lowered = question.lower()
    if any(hint in lowered for hint in FOLLOW_HINTS):
        return True
    stripped = question.strip()
    return bool(stripped) and len(stripped) <= SHORT_FOLLOWUP_CHARS


def last_user_question(history: list[dict] | None) -> str:
    for turn in reversed(list(history or [])):
        asked = str(turn.get("question") or "").strip()
        if asked:
            return asked
        if turn.get("role") == "user":
            text = str(turn.get("content") or "").strip()
            if text:
                return text
    return ""


def _turn_text(turn: dict) -> str:
    return " ".join(
        part
        for part in (
            str(turn.get("question") or "").strip(),
            str(turn.get("answer") or "").strip(),
            str(turn.get("content") or "").strip(),
        )
        if part
    )


def last_thread_route(history: list[dict] | None) -> str | None:
    """Most recent MIIT or programming topic in this chat."""
    for turn in reversed(list(history or [])):
        blob = _turn_text(turn)
        if not blob:
            continue
        if looks_like_miit(blob):
            return "miit"
        if looks_like_programming(blob):
            return "programming"
    return None


def inherit_thread_route(
    question: str,
    history: list[dict] | None = None,
) -> str | None:
    """Keep MIIT/programming when the new ask is a follow-up or short."""
    if not looks_like_followup(question):
        return None
    return last_thread_route(history)


PROGRAMMING_HINTS = (
    "binary search",
    "algorithm",
    "algo",
    "data structure",
    "python",
    "def ",
    "class ",
    "html",
    "css",
    "javascript",
    "react",
    "php",
    "sql",
    "hook",
    "loop",
    "code",
    "ohm",
    "kirchhoff",
    "voltage",
    "current",
    "resistor",
    "capacitor",
    "transistor",
    "diode",
    "circuit",
    "fourier",
    "laplace",
    "boolean",
    "logic gate",
    "semiconductor",
    "microprocessor",
    "embedded",
    "operating system",
    "computer network",
    "binary",
    "v = ir",
    "v=ir",
)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_ROUTER_PROMPT = (
    "Classify the student question. Return JSON only: "
    '{"route":"miit"} or {"route":"programming"} or {"route":"other"}. '
    "miit = Myanmar Institute of Information Technology, faculty, campus, "
    "curriculum, university people or MIIT research. "
    "programming = computer-engineering / CSE / ECE subjects and coding: "
    "algorithms, data structures, Python, web, HTML, CSS, JavaScript, React, "
    "PHP, SQL, pasted code, circuits, Ohm's law, signals, digital electronics, "
    "OS, networks, microprocessors, embedded systems. "
    "other = weather, news, sports, cooking, greetings, chit-chat, biology, "
    "general physics (e.g. Newton), high-school geometry, or other non-CE "
    "topics; not MIIT and not computer engineering. "
    "If Prior question is set and this is a follow-up, keep that same route; "
    "do not use other.\n"
)


def _router_prompt(question: str, code: str, prior: str = "") -> str:
    parts = [_ROUTER_PROMPT]
    if prior:
        parts.append(f"Prior question:\n{prior}\n\n")
    parts.append(f"Question:\n{question}")
    if code.strip():
        parts.append(f"\n\n{code.strip()}")
    return "".join(parts)

_memory: dict[str, str] = {}
_generate_fn: RouteGenerateFn | None = None
ROUTER_CACHE_DIR = ROOT / ".cache" / "router"


def set_route_generate_fn(fn: RouteGenerateFn | None) -> None:
    global _generate_fn
    _generate_fn = fn


def clear_route_cache() -> None:
    _memory.clear()


def looks_like_programming(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in PROGRAMMING_HINTS)


def rule_route(question: str, code: str = "") -> str | None:
    if looks_like_miit(question) or looks_like_miit(code):
        return "miit"
    if code.strip() or looks_like_programming(f"{question}\n{code}"):
        return "programming"
    return None


def _parse_route(raw: str) -> str | None:
    payload = _FENCE_RE.sub("", (raw or "").strip()).strip()
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        token = payload.split()[0].strip().lower().strip('"{}:,')
        return token if token in ROUTES else None
    if not isinstance(data, dict):
        return None
    route = str(data.get("route") or "").strip().lower()
    return route if route in ROUTES else None


def _cache_path(cache_key: str) -> Path:
    ROUTER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return ROUTER_CACHE_DIR / f"{cache_key}.json"


def _call_router(prompt: str) -> str:
    kwargs = {"temperature": 0.0, "top_p": 1.0, "max_new_tokens": 32}
    messages = [{"role": "user", "content": prompt}]
    if _generate_fn is not None:
        return str(_generate_fn(messages, **kwargs) or "")
    if not GEMINI_TTS_NAMES_API_KEY.strip():
        return ""
    from tutor.gemini_client import GeminiClient

    return GeminiClient(api_key=GEMINI_TTS_NAMES_API_KEY).generate(messages, **kwargs)


def classify_route(
    question: str,
    code: str = "",
    history: list[dict] | None = None,
) -> str | None:
    """Return miit|programming|other, or None to keep retrieve_miit fallback."""
    stripped = question.strip()
    code_text = (code or "").strip()
    if not stripped and not code_text:
        return None
    ruled = rule_route(stripped, code_text)
    if ruled:
        return ruled
    inherited = inherit_thread_route(stripped, history)
    if inherited:
        return inherited
    if _generate_fn is None and not GEMINI_TTS_NAMES_API_KEY.strip():
        return None
    cache_payload = f"{stripped}\n\n{code_text}"
    cache_key = hashlib.sha256(cache_payload.encode("utf-8")).hexdigest()[:32]
    prior = last_user_question(history)

    def _resolve(route: str | None) -> str | None:
        if route == "other" and looks_like_programming(cache_payload):
            route = "programming"
        if route == "other":
            kept = inherit_thread_route(stripped, history)
            if kept:
                return kept
        return route

    if cache_key in _memory:
        return _resolve(_memory[cache_key])
    path = _cache_path(cache_key)
    if path.is_file():
        try:
            cached = _parse_route(path.read_text(encoding="utf-8"))
        except OSError:
            cached = None
        if cached:
            resolved = _resolve(cached)
            if resolved and resolved != "other":
                _memory[cache_key] = resolved
            return resolved
    try:
        raw = _call_router(_router_prompt(stripped, code_text, prior))
        route = _parse_route(raw)
    except Exception as exc:
        logger.warning("Ask router failed: %s", exc)
        return inherit_thread_route(stripped, history)
    if not route:
        return inherit_thread_route(stripped, history)
    route = _resolve(route)
    if not route:
        return None
    if route != "other" or not history:
        _memory[cache_key] = route
        path.write_text(json.dumps({"route": route}), encoding="utf-8")
    return route
