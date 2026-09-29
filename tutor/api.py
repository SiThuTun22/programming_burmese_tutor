"""Litestar HTTP API for the Myanmar programming tutor."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from tutor.env_bootstrap import load_project_env

load_project_env()

import torch
from litestar import Litestar, Request, get, post
from litestar.config.cors import CORSConfig
from litestar.exceptions import HTTPException
from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from tutor import config
from tutor.config import ADAPTER_PATH, CORS_ORIGINS
from tutor.engine import TutorEngine

logger = logging.getLogger(__name__)


@dataclass
class ChatRequest:
    question: str
    code: str | None = None
    use_adapter: bool = True


@dataclass
class ChatResponse:
    answer: str


@dataclass
class HealthResponse:
    status: str
    cuda: bool
    adapter: bool


@asynccontextmanager
async def tutor_lifespan(app: Litestar) -> AsyncIterator[None]:
    app.state.engine = TutorEngine(use_adapter=True)
    try:
        yield
    finally:
        app.state.engine.unload()
        app.state.engine = None


def _engine(request: Request) -> TutorEngine:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tutor model is not loaded",
        )
    return engine


def _verify_api_key(request: Request) -> None:
    if not config.API_KEY:
        return
    provided = request.headers.get("x-api-key", "").strip()
    auth = request.headers.get("authorization", "").strip()
    if auth.lower().startswith("bearer "):
        provided = auth[7:].strip()
    if provided != config.API_KEY:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


@get("/health")
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        cuda=torch.cuda.is_available(),
        adapter=ADAPTER_PATH.exists(),
    )


@post("/v1/chat")
async def chat(data: ChatRequest, request: Request) -> ChatResponse:
    _verify_api_key(request)
    if not data.question.strip():
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="question is required",
        )
    code = data.code or ""
    if len(code) > config.MAX_CODE_CHARS:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"code exceeds maximum length ({config.MAX_CODE_CHARS} characters)",
        )
    if not data.use_adapter:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="use_adapter=false is not supported on this server (would load a second model). Use CLI with --base instead.",
        )
    logger.info(
        "chat request question_len=%s code_len=%s",
        len(data.question.strip()),
        len(code.strip()),
    )
    engine = _engine(request)
    answer = engine.answer(data.question, code)
    return ChatResponse(answer=answer)


def create_app(
    *,
    lifespan_handlers: Sequence[Callable[..., Any]] | None = None,
) -> Litestar:
    if lifespan_handlers is None:
        lifespan_handlers = [tutor_lifespan]
    cors = CORSConfig(allow_origins=CORS_ORIGINS)
    return Litestar(
        route_handlers=[health, chat],
        lifespan=list(lifespan_handlers),
        cors_config=cors,
    )


app = create_app()
