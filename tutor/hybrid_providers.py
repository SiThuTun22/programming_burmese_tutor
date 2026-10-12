"""Resolve the hybrid chat provider from env."""

from __future__ import annotations

from collections.abc import Callable

from tutor.config import HYBRID_CHAT_PROVIDER

GenerateFn = Callable[..., str]


def resolve_generate_fn() -> GenerateFn:
    if HYBRID_CHAT_PROVIDER != "gemini":
        raise ValueError(
            f"Unknown HYBRID_CHAT_PROVIDER={HYBRID_CHAT_PROVIDER!r} (use gemini)"
        )
    from tutor.gemini_client import get_shared_gemini_client

    return get_shared_gemini_client().generate
