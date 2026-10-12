"""MIIT specialist retrieve (faculty / campus / courses). No PDF agent."""

from __future__ import annotations

from tutor.knowledge import (
    INTENT_OVERVIEW,
    KnowledgeChunk,
    RetrieveResult,
    miit_retrieval_intent,
    retrieve_miit,
    retrieve_query,
)

ROUTE_FACULTY = "faculty"
ROUTE_CAMPUS = "campus"
ROUTE_COURSES = "courses"

_FACULTY_HINTS = (
    "teacher",
    "professor",
    "faculty",
    "lecturer",
    "staff",
    "dr.",
    "cynthia",
    "sin thi yar",
    "kyawt",
    "htay",
    "thant",
    "aye aye",
    "phyu thwe",
    "tin moh",
    "zar chi",
    "zarchi",
    "su su hlaing",
    "ပါမောက္ခ",
    "ဆရာမ",
    "ဆရာ့",
    "ဆရာ",
)
_CAMPUS_HINTS = (
    "miit",
    "campus",
    "institute",
    "mandalay",
    "hostel",
    "university",
    "college",
    "admission",
    "rector",
    "iiit",
    "chanmyathazi",
    "မန္တလေး",
    "ဝင်ခွင့်",
)
_COURSE_HINTS = (
    "course",
    "handout",
    "syllabus",
    "lecture",
    "module",
    "subject",
    "assignment",
    "catalog",
    "cse",
    "ece",
    "electronics",
    "communications",
    "b.e.",
    "hons",
    "semester",
    "elective",
    "capstone",
    "ဘာသာရပ်",
    "သင်ခန်းစာ",
    "သင်ရိုး",
)
_FACULTY_ID = ("cynthia", "aye", "kyawt", "phyu", "tin", "zar")
_CAMPUS_ID = ("institute", "admission")
_COURSE_ID = ("cse", "ece")
_TITLES = {
    ROUTE_FACULTY: "Faculty knowledge:",
    ROUTE_CAMPUS: "Campus / MIIT knowledge:",
    ROUTE_COURSES: "Course knowledge:",
}


def classify_specialists(question: str) -> list[str]:
    lowered = question.lower()
    routes: list[str] = []
    if any(hint in lowered for hint in _FACULTY_HINTS):
        routes.append(ROUTE_FACULTY)
    if any(hint in lowered for hint in _CAMPUS_HINTS):
        routes.append(ROUTE_CAMPUS)
    if any(hint in lowered for hint in _COURSE_HINTS):
        routes.append(ROUTE_COURSES)
    return routes


def chunk_specialist(chunk_id: str) -> str:
    lowered = chunk_id.lower()
    if any(part in lowered for part in _FACULTY_ID):
        return ROUTE_FACULTY
    if any(part in lowered for part in _COURSE_ID):
        return ROUTE_COURSES
    if any(part in lowered for part in _CAMPUS_ID):
        return ROUTE_CAMPUS
    return ROUTE_CAMPUS


def _prefixed(chunk: KnowledgeChunk, title: str) -> KnowledgeChunk:
    if chunk.text.startswith(title):
        return chunk
    return KnowledgeChunk(
        id=chunk.id,
        text=f"{title}\n{chunk.text}",
        sources=chunk.sources,
        tokens=chunk.tokens,
    )


def retrieve_specialists(
    question: str,
    history: list[dict] | None = None,
) -> RetrieveResult:
    result = retrieve_miit(question, history=history)
    intent = miit_retrieval_intent(retrieve_query(question, history))
    if intent == INTENT_OVERVIEW:
        filtered = [chunk for chunk in result.chunks if chunk.id.startswith("institute-")]
        if filtered:
            result = RetrieveResult(chunks=filtered, best_score=result.best_score)
    routes = classify_specialists(question)
    grouped: dict[str, list[KnowledgeChunk]] = {
        ROUTE_FACULTY: [],
        ROUTE_CAMPUS: [],
        ROUTE_COURSES: [],
    }
    for chunk in result.chunks:
        grouped[chunk_specialist(chunk.id)].append(chunk)
    wanted = routes or [key for key, rows in grouped.items() if rows]
    ordered: list[KnowledgeChunk] = []
    for route in (ROUTE_FACULTY, ROUTE_CAMPUS, ROUTE_COURSES):
        if route not in wanted:
            continue
        title = _TITLES[route]
        for chunk in grouped[route]:
            ordered.append(_prefixed(chunk, title))
    if not ordered:
        return result
    return RetrieveResult(chunks=ordered, best_score=result.best_score)
