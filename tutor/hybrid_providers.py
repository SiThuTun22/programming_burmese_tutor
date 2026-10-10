"""Resolve the hybrid chat provider from env."""

from __future__ import annotations

from collections.abc import Callable

from tutor.config import HYBRID_CHAT_PROVIDER

GenerateFn = Callable[..., str]


def resolve_generate_fn() -> GenerateFn:
    if HYBRID_CHAT_PROVIDER == "gemini":
        from tutor.gemini_client import GeminiClient

        return GeminiClient().generate
    if HYBRID_CHAT_PROVIDER == "openrouter":
        from tutor.openrouter_client import OpenRouterClient

        return OpenRouterClient().generate
    raise ValueError(
        f"Unknown HYBRID_CHAT_PROVIDER={HYBRID_CHAT_PROVIDER!r} "
        "(use openrouter or gemini)"
    )
