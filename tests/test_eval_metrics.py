"""Unit tests for published eval metrics (no live API)."""

from __future__ import annotations

from tutor.eval_metrics import (
    accuracy,
    exact_match,
    macro_f1,
    mrr,
    recall_at_k,
    token_f1,
)


def test_accuracy_and_macro_f1() -> None:
    gold = ["miit", "programming", "other", "miit"]
    pred = ["miit", "programming", "miit", "miit"]
    assert accuracy(gold, pred) == 0.75
    score = macro_f1(gold, pred)
    assert 0.5 < score < 1.0


def test_recall_at_k_and_mrr() -> None:
    gold = ["institute-overview"]
    ranked = ["cse-overview", "institute-overview", "institute-campus"]
    assert recall_at_k(gold, ranked, k=3) == 1.0
    assert recall_at_k(gold, ranked, k=1) == 0.0
    assert mrr(gold, ranked) == 0.5


def test_em_and_token_f1() -> None:
    answer = "ပါမောက္ခချုပ်မှာ Dr. Win Aye ဖြစ်ပါသည်။ MIIT သည် Mandalay တွင် ရှိသည်။"
    assert exact_match(answer, ["Win Aye", "Mandalay"]) == 1.0
    assert exact_match(answer, ["Win Aye", "Yangon"]) == 0.0
    assert token_f1(answer, ["Win Aye"]) > 0.0
