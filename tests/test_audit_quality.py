"""Audit leftover gates."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_quality import audit_record


def test_explain_rejects_debug_leftover() -> None:
    row = {
        "instruction": "ဒီ Python code က ဘာလုပ်သလဲ? မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ",
        "task_type": "explain_code",
        "input": "username = input(\"What is your name ? : \")\nprint(\"Your name is \", username)",
        "output": "မှန်ကန်သော code: username = input()\n\nဒီ code မှာ ဘာမှားနေလဲ။",
        "domain": "programming_basic",
    }
    fails = audit_record(row)
    assert "debug_leftover_in_explain" in fails


def test_concept_rejects_debug_leftover() -> None:
    row = {
        "instruction": "Python ဆိုတာ ဘာလဲ? မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ",
        "task_type": "concept_qa",
        "input": "",
        "output": "မှန်ကန်သော code: print(1)\n\nPython က language ဖြစ်ပါတယ်။",
        "domain": "programming_basic",
    }
    fails = audit_record(row)
    assert "debug_leftover_in_concept" in fails


def test_explain_requires_identifier_overlap() -> None:
    row = {
        "instruction": "ဒီ code ကို ရှင်းပြပါ။ မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ",
        "task_type": "explain_code",
        "input": "username = input()\nprint(username)",
        "output": "ဒီက ပရိုဂရမ် တစ်ခု ဖြစ်ပါတယ်။\n\nဘာမှ မရှင်းပါ။",
        "domain": "programming_basic",
    }
    fails = audit_record(row)
    assert "code_explanation_mismatch" in fails


def test_rejects_path_calque_off_routing() -> None:
    row = {
        "instruction": "Python ဆိုတာ ဘာလဲ? မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ",
        "task_type": "concept_qa",
        "input": "",
        "output": "Python က code လမ်းကြောင်း နဲ့ ရေးပါတယ်။ Interpreter က run ပါတယ်။",
        "domain": "programming_basic",
    }
    fails = audit_record(row)
    assert "invented_calque_path" in fails


def test_allows_path_on_route_question() -> None:
    row = {
        "instruction": "Route ဆိုတာ ဘာလဲ? မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ",
        "task_type": "concept_qa",
        "input": "",
        "output": "Route က URL လမ်းကြောင်း ကို function နဲ့ ချိတ်ပါတယ်။ web.php မှာ ရေးပါတယ်။",
        "domain": "laravel",
    }
    fails = audit_record(row)
    assert "invented_calque_path" not in fails


def test_rejects_svelte_ui_calque() -> None:
    row = {
        "instruction": "Svelte ဆိုတာ ဘာလဲ? မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ",
        "task_type": "concept_qa",
        "input": "",
        "output": "Svelte က UI ကို လျော့ချပါတယ်။ compile လုပ်ပါတယ်။",
        "domain": "javascript",
    }
    fails = audit_record(row)
    assert "invented_calque_ui" in fails
