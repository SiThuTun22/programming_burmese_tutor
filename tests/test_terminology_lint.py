"""Terminology lint unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from terminology_lint import allows_taing_context, lint_record


def test_taing_misuse_on_math_context() -> None:
    row = {
        "instruction": "odd numbers",
        "domain": "python",
        "output": "တစ်တန်းပဲ သိမ်းပါတယ်။",
        "input": "def f(): pass",
    }
    assert "term_taing_misuse" in lint_record(row)


def test_taing_ok_on_bootstrap() -> None:
    row = {
        "instruction": "Responsive design",
        "domain": "bootstrap",
        "output": "ဖုန်းမှာ တစ်တန်း ဖြစ်နိုင်ပါတယ်။",
        "input": "",
    }
    assert lint_record(row) == []
