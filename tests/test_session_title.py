"""Session sidebar titles preserve faculty names."""

from app.ai.session_title import (
    correct_title_with_faculty,
    resolve_rule_based_title,
)


def test_burmese_cynthia_who_title() -> None:
    q = "ဒေါက်တာစင်သီယာမြင့်က ဘယ်သူလဲ"
    title = resolve_rule_based_title(q)
    assert title is not None
    assert "Myint" in title
    assert "Maung" not in title
    assert title == "Who is Dr Cynthia Myint"


def test_english_cynthia_who_title() -> None:
    q = "Who is Dr Cynthia Myint?"
    title = resolve_rule_based_title(q)
    assert title is not None
    assert "Myint" in title


def test_unrelated_programming_no_rule_title() -> None:
    q = "Python for loop ရှင်းပြပါ"
    assert resolve_rule_based_title(q) is None


def test_correct_title_fixes_maung_hallucination() -> None:
    source = "Who is Dr Cynthia Myint?"
    bad = "Who Is Dr Cynthia Maung"
    fixed = correct_title_with_faculty(bad, source)
    assert "Myint" in fixed
    assert "Maung" not in fixed
