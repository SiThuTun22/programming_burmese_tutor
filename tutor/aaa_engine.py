"""Gradio tutor engine backed by AAA LangGraph + pgvector (no session PDF)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from tutor.aaa_bootstrap import ensure_aaa_ready
from tutor.aaa_llm import generate_from_tutor_messages
from tutor.aaa_scope import miit_question_has_grounding
from tutor.config import HYBRID_DEBUG, generation_config
from tutor.prompts import (
    CONTINUE_STYLE,
    build_general_tutor_messages,
    pick_programming_style,
    strip_answer_cue,
)
from tutor.hybrid import ROUTE_BADGES
from tutor.router import (
    OUT_OF_SCOPE_ANSWER,
    classify_route,
    inherit_thread_route,
)


class AAAEngine:
    def __init__(self) -> None:
        self.last_route: str | None = None
        self.last_score: float | None = None
        self.last_badge: str | None = None

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
                return OUT_OF_SCOPE_ANSWER

        if classified == "programming":
            return self._answer_programming(question, code, history, voice)

        return self._answer_miit_aaa(question, code, history, voice)

    def _answer_programming(
        self,
        question: str,
        code: str,
        history: list[dict] | None,
        voice: str | None,
    ) -> str:
        self.last_route = "gemini"
        self.last_score = None
        self.last_badge = ROUTE_BADGES["gemini"]
        sampling = generation_config("gemini")
        style_name, style_line = (
            CONTINUE_STYLE if history else pick_programming_style()
        )
        if HYBRID_DEBUG:
            print(
                f"aaa: route=programming temperature={sampling['temperature']} "
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
        raw = asyncio.run(
            generate_from_tutor_messages(
                messages,
                temperature=sampling["temperature"],
                top_p=sampling["top_p"],
            )
        )
        return strip_answer_cue(raw)

    def _answer_miit_aaa(
        self,
        question: str,
        code: str,
        history: list[dict] | None,
        voice: str | None,
    ) -> str:
        self.last_route = "miit"
        self.last_score = None
        self.last_badge = ROUTE_BADGES["miit"]
        if HYBRID_DEBUG:
            print("aaa: route=miit (LangGraph)", flush=True)
        ensure_aaa_ready()
        user_content = question.strip()
        if code.strip():
            user_content = f"{user_content}\n\n```\n{code.strip()}\n```"
        if not asyncio.run(miit_question_has_grounding(user_content)):
            self.last_route = "other"
            self.last_badge = ROUTE_BADGES["other"]
            return OUT_OF_SCOPE_ANSWER
        reply = asyncio.run(
            _generate_tutor_reply_async(user_content, history, voice),
        )
        return reply

    def unload(self) -> None:
        return None


async def _generate_tutor_reply_async(
    user_content: str,
    history: list[dict] | None,
    voice: str | None,
) -> str:
    from app.ai.tutor import generate_tutor_reply
    from app.db.enums import MessageRole, TutorAvatar, TutorTone
    from app.db.models import ChatMessage, ChatSession

    avatar = TutorAvatar.MALE if (voice or "").strip().lower() == "male" else TutorAvatar.FEMALE
    session = ChatSession(
        id=uuid.uuid4(),
        title="Gradio",
        tutor_tone=TutorTone.SOCRATIC,
        tutor_avatar=avatar,
        owner_id=uuid.uuid4(),
    )
    messages: list[ChatMessage] = []
    for turn in list(history or []):
        asked = str(turn.get("question") or "").strip()
        answered = str(turn.get("answer") or "").strip()
        if asked:
            messages.append(
                ChatMessage(
                    id=uuid.uuid4(),
                    chat_session_id=session.id,
                    role=MessageRole.USER,
                    content=asked,
                )
            )
        if answered:
            messages.append(
                ChatMessage(
                    id=uuid.uuid4(),
                    chat_session_id=session.id,
                    role=MessageRole.ASSISTANT,
                    content=answered,
                    tutor_avatar=avatar,
                )
            )
    return await generate_tutor_reply(
        session,
        messages,
        user_content,
        document_context=None,
    )


def create_aaa_engine(**kwargs: Any) -> AAAEngine:
    del kwargs
    return AAAEngine()
