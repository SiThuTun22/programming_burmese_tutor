"""Faculty alias expansion for AAA retrieval."""

from __future__ import annotations

from app.agents.router import ROUTE_FACULTY, classify_routes
from tutor.faculty_query import (
    expand_faculty_retrieval_query,
    expand_faculty_retrieval_query_with_history,
    faculty_profile_matched,
    faculty_routes_for_question,
    faculty_routes_for_thread,
)


def test_burmese_cynthia_profile_matched() -> None:
    q = "ဒေါက်တာစင်သီယာမြင့်က ဘယ်သူလဲ"
    assert faculty_profile_matched(q)
    assert faculty_routes_for_question(q)


def test_expand_cynthia_burmese() -> None:
    expanded = expand_faculty_retrieval_query("ဒေါက်တာစင်သီယာမြင့်က ဘယ်သူလဲ")
    assert "Cynthia Myint" in expanded
    assert "Sin Thi Yar" in expanded


def test_expand_english_cynthia() -> None:
    expanded = expand_faculty_retrieval_query("Who is Dr. Cynthia Myint?")
    assert "Cynthia Myint" in expanded


def test_classify_routes_burmese_faculty() -> None:
    routes = classify_routes("ဒေါက်တာစင်သီယာမြင့်က ဘယ်သူလဲ", "(none)")
    assert ROUTE_FACULTY in routes


def test_paper_followup_routes_faculty_with_history() -> None:
    history = (
        "Student: ဒေါက်တာစင်သီယာမြင့်က ဘယ်သူလဲ\n"
        "Tutor: ပါမောက္ခ Dr. Cynthia Myint သည် MIIT တွင် ..."
    )
    q = "သူမရဲ့ သုတေသနစာတမ်းတွေက ဘာတွေလဲ။"
    assert faculty_routes_for_thread(q, history)
    routes = classify_routes(q, "(none)", history)
    assert ROUTE_FACULTY in routes
    expanded = expand_faculty_retrieval_query_with_history(q, history)
    assert "Cynthia Myint" in expanded
    assert "research" in expanded.lower() or "paper" in expanded.lower()
