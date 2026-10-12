"""MIIT grounding checks for AAA backend (in-scope only)."""

from __future__ import annotations

from app.agents.router import (
    ROUTE_CAMPUS,
    ROUTE_COURSES,
    ROUTE_FACULTY,
    classify_routes,
)
from app.knowledge.store import (
    CATEGORY_CAMPUS,
    CATEGORY_COURSES,
    CATEGORY_FACULTY,
    embed_query,
    retrieve,
)
from tutor.faculty_query import (
    expand_faculty_retrieval_query_with_history,
    faculty_routes_for_question,
    faculty_routes_for_thread,
)
from tutor.knowledge import looks_like_miit

_ROUTE_TO_CATEGORY = {
    ROUTE_FACULTY: CATEGORY_FACULTY,
    ROUTE_CAMPUS: CATEGORY_CAMPUS,
    ROUTE_COURSES: CATEGORY_COURSES,
}
_ALL_CATEGORIES = (CATEGORY_FACULTY, CATEGORY_CAMPUS, CATEGORY_COURSES)


async def miit_question_has_grounding(user_content: str) -> bool:
    """True when AAA retrieval can return at least one chunk for this MIIT ask."""
    text = (user_content or "").strip()
    if not text:
        return False
    routes = classify_routes(text, "(none)")
    if (
        not routes
        and not looks_like_miit(text)
        and not faculty_routes_for_question(text)
        and not faculty_routes_for_thread(text, "")
    ):
        return False
    retrieval_query = expand_faculty_retrieval_query_with_history(text, "")
    embedding = await embed_query(retrieval_query)
    categories: list[str] = []
    if routes:
        for route in routes:
            category = _ROUTE_TO_CATEGORY.get(route)
            if category and category not in categories:
                categories.append(category)
    else:
        categories = list(_ALL_CATEGORIES)
    if faculty_routes_for_question(text) and CATEGORY_FACULTY not in categories:
        categories.insert(0, CATEGORY_FACULTY)
    for category in categories:
        chunks = await retrieve(category, retrieval_query, embedding)
        if chunks:
            return True
    return False
