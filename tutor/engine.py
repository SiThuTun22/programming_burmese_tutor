"""High-level tutor: load model once, answer questions."""

from __future__ import annotations

from pathlib import Path

from tutor.env_bootstrap import load_project_env

load_project_env()

import torch
from peft import PeftModel

from tutor.config import ADAPTER_PATH, BASE_MODEL, MAX_NEW_TOKENS
from tutor.model import (
    generate_text,
    load_base_model,
    load_tokenizer,
    ready_for_generate,
    require_cuda,
    resolve_model_id,
    setup_inference_env,
)
from tutor.prompts import build_messages
from tutor.retrieve import retrieve_book_quotes


class TutorEngine:
    def __init__(
        self,
        *,
        base_model: str | None = None,
        adapter_path: Path | None = None,
        max_new_tokens: int | None = None,
        use_adapter: bool = True,
    ) -> None:
        require_cuda()
        setup_inference_env()

        self.max_new_tokens = max_new_tokens or MAX_NEW_TOKENS
        self.adapter_path = adapter_path or ADAPTER_PATH
        self.use_adapter = use_adapter
        requested = base_model or BASE_MODEL
        self.model_id = resolve_model_id(requested)

        if use_adapter and not self.adapter_path.exists():
            raise FileNotFoundError(f"LoRA adapter not found: {self.adapter_path}")

        self.tokenizer = load_tokenizer(self.model_id)
        base = ready_for_generate(load_base_model(self.model_id, "4bit"))
        if use_adapter:
            self.model = PeftModel.from_pretrained(base, str(self.adapter_path))
            self.model.eval()
        else:
            self.model = base

    def answer(self, question: str, code: str = "") -> str:
        quotes = retrieve_book_quotes(question, code)
        messages = build_messages(question, code, quotes)
        return generate_text(
            self.model,
            self.tokenizer,
            messages,
            self.max_new_tokens,
        )

    def answer_messages(self, messages: list[dict]) -> str:
        return generate_text(
            self.model,
            self.tokenizer,
            messages,
            self.max_new_tokens,
        )

    def unload(self) -> None:
        del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
