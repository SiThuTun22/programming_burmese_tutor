"""Preflight hybrid path (no GPU)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_preflight():
    path = ROOT / "scripts" / "preflight_tutor.py"
    spec = importlib.util.spec_from_file_location("preflight_tutor", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_hybrid_missing_gemini_key(monkeypatch) -> None:
    pf = _load_preflight()
    monkeypatch.setattr(pf, "TUTOR_BACKEND", "hybrid")
    monkeypatch.setattr(pf, "HYBRID_CHAT_PROVIDER", "gemini")
    monkeypatch.setattr(pf, "GEMINI_API_KEY", "")
    assert pf.main() == 1


def test_preflight_hybrid_ok_gemini(monkeypatch, tmp_path) -> None:
    pf = _load_preflight()
    index = tmp_path / "index.json"
    index.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pf, "TUTOR_BACKEND", "hybrid")
    monkeypatch.setattr(pf, "HYBRID_CHAT_PROVIDER", "gemini")
    monkeypatch.setattr(pf, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(pf, "MIIT_RETRIEVAL", "embed")
    monkeypatch.setattr(pf, "MIIT_INDEX_PATH", index)
    assert pf.main() == 0


def test_preflight_missing_index_fails(monkeypatch, tmp_path) -> None:
    pf = _load_preflight()
    monkeypatch.setattr(pf, "TUTOR_BACKEND", "hybrid")
    monkeypatch.setattr(pf, "HYBRID_CHAT_PROVIDER", "gemini")
    monkeypatch.setattr(pf, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(pf, "MIIT_RETRIEVAL", "embed")
    monkeypatch.setattr(pf, "MIIT_INDEX_PATH", tmp_path / "missing.json")
    assert pf.main() == 1
