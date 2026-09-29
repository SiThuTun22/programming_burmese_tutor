"""Book-voice compose keeps catalog gold."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_book_voice_dataset import compose_output


def test_compose_keeps_gold_when_two_book_sents() -> None:
    row = {
        "task_type": "explain_code",
        "input": "username = input()\nprint(username)",
        "output": "ဒီ code က နာမည် လက်ခံပါတယ်။\n\ninput() က စာယူပါတယ်။\n\nprint က ပြပါတယ်။",
    }
    book = [
        "နောက်လာမယ့် အခန်းမှာ OOP ကို သင်မှာ ဖြစ်ပါတယ်။",
        "Class ဆိုတာကတော့ object တစ်ခု ဖန်တီးဖို့ ပါ။",
    ]
    text, mode = compose_output(row, book)
    assert "input()" in text
    assert "နာမည် လက်ခံ" in text
    assert "နောက်လာမယ့် အခန်း" not in text
    assert "book_only" != mode


def test_compose_skips_unusable_garnish() -> None:
    row = {
        "task_type": "concept_qa",
        "instruction": "Python ဆိုတာ ဘာလဲ?",
        "input": "",
        "output": "Programmer တွေဟာ programming language တစ်ခုခု ကို အသုံးပြုပြီး app တွေကို ဖန်တီးကြပါတယ်။\n\nPython ဟာ Object Oriented Programming Language တစ်ခုပါ။",
    }
    text, mode = compose_output(row, ["HELLO Python ကို ရိုက်ပါ။ ဒီစာအုပ်မှာ ကြည့်ပါ။"])
    assert "HELLO Python" not in text
    assert mode == "gold_only"
