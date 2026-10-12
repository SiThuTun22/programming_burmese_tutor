"""Hybrid tutor: every question is answered by the cloud chat model."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, Protocol

from tutor.config import HYBRID_DEBUG, generation_config
from tutor.prompts import (
    CONTINUE_STYLE,
    build_general_tutor_messages,
    build_miit_messages,
    pick_miit_wording_style,
    pick_programming_style,
    strip_answer_cue,
)
from tutor.router import (
    OUT_OF_SCOPE_ANSWER,
    classify_route,
    inherit_thread_route,
    set_route_generate_fn,
)
from tutor.specialists import retrieve_specialists

GenerateFn = Callable[..., str]

ROUTE_BADGES = {
    "gemini": "Gemini",
    "miit": "MIIT",
    "other": "Out of scope",
}


class TutorLike(Protocol):
    def answer(self, question: str, code: str = "") -> str: ...

    def unload(self) -> None: ...


class HybridEngine:
    def __init__(self, *, generate_fn: GenerateFn | None = None) -> None:
        from tutor.hybrid_providers import resolve_generate_fn

        self.last_route: str | None = None
        self.last_score: float | None = None
        self.last_badge: str | None = None
        if generate_fn is None:
            self._generate_fn = resolve_generate_fn()
        else:
            self._generate_fn = generate_fn
        _wire_router_generate(self._generate_fn)

    def answer(
        self,
        question: str,
        code: str = "",
        history: list[dict] | None = None,
        voice: str | None = None,
    ) -> str:
        classified = classify_route(question, code, history)
        if classified == "other":
            classified = inherit_thread_route(question, history)
            if classified is None:
                self.last_route = "other"
                self.last_score = None
                self.last_badge = ROUTE_BADGES["other"]
                if HYBRID_DEBUG:
                    print("hybrid: route=other", flush=True)
                return OUT_OF_SCOPE_ANSWER

        if classified == "programming":
            passages = []
            result_score = None
        elif classified == "miit":
            result = retrieve_specialists(question, history=history)
            passages = result.chunks
            result_score = result.best_score
        else:
            result = retrieve_specialists(question, history=history)
            passages = result.chunks
            result_score = result.best_score

        if classified == "miit" or passages:
            self.last_route = "miit"
            self.last_score = result_score
            self.last_badge = ROUTE_BADGES["miit"]
            sampling = generation_config("miit")
            style_name, style_line = (
                CONTINUE_STYLE if history else pick_miit_wording_style()
            )
            if HYBRID_DEBUG:
                print(
                    f"hybrid: route=miit temperature={sampling['temperature']} "
                    f"style={style_name}",
                    flush=True,
                )
            messages = build_miit_messages(
                question,
                passages or [],
                code,
                history,
                delivery_style=(style_name, style_line),
                voice=voice,
            )
        else:
            self.last_route = "gemini"
            self.last_score = None
            self.last_badge = ROUTE_BADGES["gemini"]
            sampling = generation_config("gemini")
            style_name, style_line = (
                CONTINUE_STYLE if history else pick_programming_style()
            )
            if HYBRID_DEBUG:
                print(
                    f"hybrid: route=gemini temperature={sampling['temperature']} "
                    f"style={style_name}",
                    flush=True,
                )
            messages = build_general_tutor_messages(
                question,
                code,
                history,
                delivery_style=(style_name, style_line),
                voice=voice,
            )
        return strip_answer_cue(self._call_generate(messages, sampling))

    def _call_generate(self, messages: list[dict], sampling: dict[str, float]) -> str:
        if _supports_sampling(self._generate_fn):
            return self._generate_fn(messages, **sampling)
        return self._generate_fn(messages)

    def answer_messages(self, messages: list[dict]) -> str:
        return self._call_generate(messages, generation_config(self.last_route))

    def unload(self) -> None:
        return None


def _supports_sampling(fn: Callable[..., str]) -> bool:
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return True
    return "temperature" in params or "top_p" in params


def _wire_router_generate(generate_fn: GenerateFn) -> None:
    set_route_generate_fn(generate_fn)


def create_engine(**kwargs: Any) -> HybridEngine:
    from tutor.config import TUTOR_BACKEND

    del kwargs
    if TUTOR_BACKEND == "aaa":
        from tutor.aaa_engine import AAAEngine

        return AAAEngine()
    return HybridEngine()
