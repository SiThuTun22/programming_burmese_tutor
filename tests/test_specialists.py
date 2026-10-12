"""MIIT specialist routing (no live API)."""

from tutor.knowledge import KnowledgeChunk, RetrieveResult
from tutor.specialists import (
    ROUTE_CAMPUS,
    ROUTE_COURSES,
    ROUTE_FACULTY,
    chunk_specialist,
    classify_specialists,
    retrieve_specialists,
)


def test_faculty_question_routes_faculty() -> None:
    assert ROUTE_FACULTY in classify_specialists("Dr. Cynthia Myint က ဘယ်သူလဲ။")


def test_admission_routes_campus() -> None:
    assert ROUTE_CAMPUS in classify_specialists("MIIT ဘွဲ့ကြို ဝင်ခွင့် ဦးရေ ဘယ်လောက်လဲ။")


def test_cse_routes_courses() -> None:
    assert ROUTE_COURSES in classify_specialists("CSE B.E. Hons သင်တန်းက ဘယ်လောက် ကြာလဲ။")


def test_chunk_ids_bucket() -> None:
    chunk = KnowledgeChunk(id="cynthia-role", text="x", sources=(), tokens=frozenset())
    assert chunk_specialist(chunk.id) == ROUTE_FACULTY
    assert chunk_specialist("institute-overview") == ROUTE_CAMPUS
    assert chunk_specialist("cse-overview") == ROUTE_COURSES


def test_overview_question_drops_admission_chunks(monkeypatch) -> None:
    mixed = [
        KnowledgeChunk(
            id="admission-bachelor-exam",
            text="entrance exam",
            sources=(),
            tokens=frozenset(),
        ),
        KnowledgeChunk(
            id="institute-overview",
            text="MIIT overview",
            sources=(),
            tokens=frozenset(),
        ),
    ]

    def fake_retrieve(*_args, **_kwargs) -> RetrieveResult:
        return RetrieveResult(chunks=list(mixed), best_score=0.9)

    monkeypatch.setattr("tutor.specialists.retrieve_miit", fake_retrieve)
    result = retrieve_specialists("MIIT ဆိုတာ ဘာလဲ?")
    ids = [chunk.id for chunk in result.chunks]
    assert ids
    assert not any(chunk_id.startswith("admission-") for chunk_id in ids)
    assert "institute-overview" in ids
