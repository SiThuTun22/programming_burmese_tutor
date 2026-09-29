#!/usr/bin/env python3
"""Fixed 15-question quality smoke (needs GPU + adapter)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

import torch

from tutor.config import ADAPTER_PATH
from tutor.engine import TutorEngine

SMOKE = [
    {"question": "Python ဆိုတာ ဘာလဲ?", "code": ""},
    {"question": "list နဲ့ dict ဘာကွာလဲ?", "code": ""},
    {"question": "Fragment ဆိုတာ ဘာလဲ?", "code": ""},
    {"question": "Variable ဆိုတာ ဘာလဲ?", "code": ""},
    {"question": "for loop နဲ့ while loop ဘာကွာလဲ?", "code": ""},
    {"question": "def က ဘာအတွက်လဲ?", "code": ""},
    {"question": "try except က ဘာကြောင့် လိုသလဲ?", "code": ""},
    {"question": "SQL ဆိုတာ ဘာလဲ?", "code": ""},
    {"question": "useState hook ကို ဘယ်လို သုံးမလဲ?", "code": ""},
    {"question": "HTML နဲ့ CSS ကွာခြားချက် ရှင်းပြပါ", "code": ""},
    {
        "question": "ဒီ Python code က ဘာလုပ်သလဲ?",
        "code": "username = input(\"What is your name ? : \")\nprint(\"Your name is \", username)",
    },
    {"question": "None ဆိုတာ ဘာလဲ?", "code": ""},
    {"question": "class နဲ့ instance ဘာကွာလဲ?", "code": ""},
    {"question": "Compiler နဲ့ interpreter ဘာကွာလဲ?", "code": ""},
    {"question": "Indentation က ဘာကြောင့် အရေးကြီးလဲ?", "code": ""},
]


def main() -> int:
    if not torch.cuda.is_available():
        print("SKIP: no CUDA")
        return 0
    if not ADAPTER_PATH.exists():
        print(f"SKIP: adapter missing at {ADAPTER_PATH}")
        return 0
    engine = TutorEngine(use_adapter=True)
    rows = []
    try:
        for item in SMOKE:
            answer = engine.answer(item["question"], item["code"])
            rows.append({**item, "answer": answer})
            preview = answer.replace("\n", " ")[:160]
            print(f"Q: {item['question']}\nA: {preview}\n")
    finally:
        engine.unload()
    out = ROOT / "results" / "smoke_quality.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    empty = [r["question"] for r in rows if not r["answer"].strip()]
    if empty:
        print("FAIL: empty answers", empty, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
