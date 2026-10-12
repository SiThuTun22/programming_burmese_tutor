"""AAA agent router fork (programming hints)."""

from __future__ import annotations

from app.agents.router import ROUTE_PDF, ROUTE_PROGRAMMING, classify_routes


def test_programming_route_without_document() -> None:
    routes = classify_routes("How does a Python for loop work?", "(none)")
    assert ROUTE_PROGRAMMING in routes
    assert ROUTE_PDF not in routes


def test_no_pdf_route_without_session_document() -> None:
    routes = classify_routes("What is MIIT?", "(none)")
    assert ROUTE_PDF not in routes
