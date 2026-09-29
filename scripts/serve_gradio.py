#!/usr/bin/env python3
"""Gradio web UI for the Myanmar programming tutor."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

import gradio as gr

from tutor.config import GRADIO_HOST, GRADIO_PORT, TTS_AUTOPLAY, TTS_ENABLED
from tutor.engine import TutorEngine
from tutor.tts import synthesize_sync

ENGINE: TutorEngine | None = None

EXAMPLE_QUESTIONS = [
    "React ဆိုတာ ဘာလဲ?",
    "Fragment ဆိုတာ ဘာလဲ?",
    "useState hook ကို ဘယ်လို သုံးမလဲ?",
    "HTML နဲ့ CSS ကွာခြားချက် ရှင်းပြပါ",
]


def respond(
    question: str,
    code: str,
    read_aloud: bool,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, str | None]:
    if not question.strip():
        return "မေးခွန်း ထည့်ပါ။", None
    assert ENGINE is not None
    progress(0, desc="Generating answer…")
    answer = ENGINE.answer(question, code or "")
    progress(0.7, desc="Answer ready")
    audio_path: str | None = None
    if read_aloud and TTS_ENABLED:
        progress(0.85, desc="Generating speech…")
        audio_path = synthesize_sync(answer)
    progress(1, desc="Done")
    return answer, audio_path


def main() -> None:
    global ENGINE
    print("Loading tutor model (fine-tuned adapter)...", flush=True)
    ENGINE = TutorEngine(use_adapter=True)
    print("Model ready.", flush=True)

    with gr.Blocks(title="Myanmar Web Programming Tutor") as demo:
        gr.Markdown(
            "# Myanmar Web Programming Tutor\n"
            "မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ — v0.3 book-voice LoRA on Gemma-3-4B-IT"
        )
        gr.Markdown("**Status:** Model loaded. Ask a question below.")
        question = gr.Textbox(
            label="Question",
            lines=2,
            placeholder="React ဆိုတာ ဘာလဲ?",
        )
        code = gr.Textbox(
            label="Code (optional)",
            lines=8,
            placeholder="Paste your code here if the question is about it",
        )
        read_aloud = gr.Checkbox(
            label="Read answer aloud",
            value=TTS_ENABLED,
            interactive=TTS_ENABLED,
        )
        answer = gr.Textbox(label="Answer", lines=14)
        audio = gr.Audio(
            label="Listen",
            type="filepath",
            autoplay=TTS_AUTOPLAY,
        )
        ask_btn = gr.Button("Ask", variant="primary")
        gr.Examples(
            examples=[[q, "", TTS_ENABLED] for q in EXAMPLE_QUESTIONS],
            inputs=[question, code, read_aloud],
            label="Example questions",
        )
        ask_btn.click(
            fn=respond,
            inputs=[question, code, read_aloud],
            outputs=[answer, audio],
            show_progress="full",
        )
        gr.Markdown(
            "*Academic use only. Books © Ei Maung and Saturngod.*"
            + (
                " Read-aloud uses edge-tts (internet required)."
                if TTS_ENABLED
                else ""
            )
        )

    demo.queue(default_concurrency_limit=1)
    demo.launch(
        server_name=GRADIO_HOST,
        server_port=GRADIO_PORT,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
