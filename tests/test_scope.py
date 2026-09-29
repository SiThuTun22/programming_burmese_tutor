from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_engine_answer_is_not_gated() -> None:
    src = (ROOT / "tutor" / "engine.py").read_text(encoding="utf-8")
    assert "is_out_of_scope" not in src
    assert "out_of_scope_message" not in src
    assert "is_uncovered_algorithm" not in src
    assert "retrieve_book_quotes" in src
    assert "generate_text" in src


def test_gradio_does_not_refuse_or_banner() -> None:
    text = (ROOT / "scripts" / "serve_gradio.py").read_text(encoding="utf-8")
    assert "SCOPE_BANNER" not in text
    assert "is_out_of_scope" not in text
    assert "out_of_scope_message" not in text
    assert "is_uncovered_algorithm" not in text
