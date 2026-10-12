"""MIIT retrieval (no live Gemini embed)."""

from __future__ import annotations

import numpy as np

from tutor import config
from tutor.knowledge import (
    CURRICULUM_TOP_K,
    INTENT_ADMISSION,
    INTENT_OVERVIEW,
    IndexedChunk,
    MiitIndex,
    PAPER_TOP_K,
    effective_miit_limit,
    load_miit_chunks,
    looks_like_admission,
    looks_like_curriculum,
    looks_like_institute_overview,
    looks_like_miit,
    looks_like_papers,
    miit_retrieval_intent,
    rank_by_embeddings,
    retrieve_miit_embed,
    retrieve_miit_token,
    retrieve_query,
)


def _index_with_vectors(
    a: list[float],
    b: list[float],
) -> MiitIndex:
    return MiitIndex(
        embed_model="test",
        built_at="2026-01-01T00:00:00+00:00",
        chunks=(
            IndexedChunk(
                id="chunk-a",
                text="Professor A at MIIT",
                sources=("https://example.com/a",),
                embedding=tuple(a),
            ),
            IndexedChunk(
                id="chunk-b",
                text="Professor B research",
                sources=("https://example.com/b",),
                embedding=tuple(b),
            ),
        ),
    )


def test_rank_by_embeddings_prefers_nearest() -> None:
    index = _index_with_vectors([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
    result = rank_by_embeddings(
        [0.99, 0.01, 0.0],
        index.chunks,
        limit=1,
        min_similarity=0.5,
    )
    assert len(result.chunks) == 1
    assert result.chunks[0].id == "chunk-a"
    assert result.best_score is not None
    assert result.best_score > 0.9


def test_rank_below_threshold_returns_empty() -> None:
    index = _index_with_vectors([1.0, 0.0], [0.0, 1.0])
    result = rank_by_embeddings(
        [1.0, 0.0],
        index.chunks,
        limit=3,
        min_similarity=1.1,
    )
    assert result.chunks == []
    assert result.best_score is None


def test_typo_query_near_same_vector_hits_chunk() -> None:
    base = np.asarray([0.3, 0.4, 0.5], dtype=np.float64)
    base = base / np.linalg.norm(base)
    typo = base + np.asarray([0.01, -0.01, 0.005], dtype=np.float64)
    typo = typo / np.linalg.norm(typo)
    index = MiitIndex(
        embed_model="test",
        built_at="",
        chunks=(
            IndexedChunk(
                id="cynthia",
                text="Cynthia Myint at MIIT",
                sources=("https://example.com/cynthia",),
                embedding=tuple(float(x) for x in base),
            ),
        ),
    )

    def fake_embed(texts: list[str]) -> list[list[float]]:
        assert texts[0] == "Cynthida Myint ဆိုတာ ဘယ်သူလဲ?"
        return [typo.tolist()]

    result = retrieve_miit_embed(
        "Cynthida Myint ဆိုတာ ဘယ်သူလဲ?",
        index=index,
        min_similarity=0.85,
        embed_fn=fake_embed,
    )
    assert len(result.chunks) == 1
    assert result.chunks[0].id == "cynthia"


def test_looks_like_miit_gate() -> None:
    assert looks_like_miit("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?")
    assert looks_like_miit("Cynthida Myint ဆိုတာ ဘယ်သူလဲ?")
    assert looks_like_miit("ဒေါ်စင်သီယာမြင့် ဆိုတာ ဘယ်သူလဲ?")
    assert looks_like_miit("Cynthia Sin Thi Yar Myint")
    assert looks_like_miit("MIIT မှာ ဘယ်သူ သင်လဲ?")
    assert looks_like_miit("ပါမောက္ခ ဘယ်သူလဲ?")
    assert looks_like_miit("ဒေါက်တာဝင်းအေး")
    assert looks_like_miit("IIIT-B mentor")
    assert looks_like_miit("B.E. CSE")
    assert looks_like_miit("Aye Aye Thant ဆိုတာ ဘယ်သူလဲ?")
    assert looks_like_miit("ဘွဲ့ကြို ဝင်ခွင့်")
    assert not looks_like_miit("useState hook ကို ဘယ်လို သုံးမလဲ?")


def test_looks_like_papers_on_detail_question() -> None:
    assert looks_like_papers("what are her research papers? tell me in detail")
    assert not looks_like_papers("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?")


def test_miit_overview_intent_classifiers() -> None:
    assert looks_like_institute_overview("MIIT ဆိုတာ ဘာလဲ?")
    assert looks_like_institute_overview("what is MIIT")
    assert miit_retrieval_intent("MIIT ဆိုတာ ဘာလဲ?") == INTENT_OVERVIEW
    assert looks_like_admission("MIIT ဘွဲ့ကြို ဝင်ခွင့် ဦးရေ ဘယ်လောက်လဲ။")
    assert miit_retrieval_intent("MIIT ဘွဲ့ကြို ဝင်ခွင့် ဦးရေ ဘယ်လောက်လဲ။") == INTENT_ADMISSION
    assert not looks_like_institute_overview("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?")
    assert miit_retrieval_intent("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?") is None


def test_overview_embed_returns_institute_chunks_only() -> None:
    vec = (1.0, 0.0)
    index = MiitIndex(
        embed_model="test",
        built_at="",
        chunks=(
            IndexedChunk(
                id="institute-overview",
                text="MIIT Mandalay NCoE founded 2015",
                sources=(),
                embedding=vec,
            ),
            IndexedChunk(
                id="admission-bachelor-exam",
                text="MIIT entrance exam 60 40 weight 120 seats",
                sources=(),
                embedding=vec,
            ),
        ),
    )

    def fake_embed(texts: list[str]) -> list[list[float]]:
        del texts
        return [[1.0, 0.0]]

    result = retrieve_miit_embed(
        "MIIT ဆိုတာ ဘာလဲ?",
        index=index,
        min_similarity=0.5,
        embed_fn=fake_embed,
    )
    ids = [chunk.id for chunk in result.chunks]
    assert ids
    assert all(chunk_id.startswith("institute-") for chunk_id in ids)
    assert "institute-overview" in ids


def test_looks_like_curriculum_on_semester_question() -> None:
    assert looks_like_curriculum("CSE year 1 semester courses")
    assert looks_like_curriculum(
        "B.E (Hons.) CSE မှာခုနှစ် ဘယ်ဘာသာတွေကို သင်ကြားပေးပါသလဲ။"
    )
    assert not looks_like_curriculum("Cynthia Myint ဆိုတာ ဘယ်သူလဲ?")


def test_cse_detail_followup_uses_curriculum_limit() -> None:
    prior = "B.E (Hons.) CSE မှာခုနှစ် ဘယ်ဘာသာတွေကို သင်ကြားပေးပါသလဲ။"
    query = retrieve_query(
        "ကျွန်တော့်ကို အသေးစိတ် ပြောပြပါ။",
        [{"question": prior, "answer": "Year I"}],
    )
    assert effective_miit_limit(query) == CURRICULUM_TOP_K
    assert CURRICULUM_TOP_K == 12
    assert effective_miit_limit(
        "who is Daw Sin thi yar myint? what are her research papers? tell me in detail."
    ) == PAPER_TOP_K


def _index_five_same_vector() -> MiitIndex:
    vec = (1.0, 0.0)
    return MiitIndex(
        embed_model="test",
        built_at="",
        chunks=tuple(
            IndexedChunk(
                id=f"chunk-{i}",
                text="Cynthia Myint MIIT",
                sources=(),
                embedding=vec,
            )
            for i in range(5)
        ),
    )


def test_papers_question_retrieves_five_chunks() -> None:
    index = _index_five_same_vector()

    def fake_embed(texts: list[str]) -> list[list[float]]:
        del texts
        return [[1.0, 0.0]]

    papers = retrieve_miit_embed(
        "who is Daw Sin thi yar myint? what are her research papers? tell me in detail.",
        index=index,
        min_similarity=0.5,
        embed_fn=fake_embed,
    )
    assert len(papers.chunks) == 5

    who = retrieve_miit_embed(
        "Cynthia Myint ဆိုတာ ဘယ်သူလဲ?",
        index=index,
        min_similarity=0.5,
        embed_fn=fake_embed,
    )
    assert len(who.chunks) == config.MIIT_TOP_K


def _index_n_same_vector(n: int) -> MiitIndex:
    vec = (1.0, 0.0)
    return MiitIndex(
        embed_model="test",
        built_at="",
        chunks=tuple(
            IndexedChunk(
                id=f"chunk-{i}",
                text="CSE B.E. Hons MIIT",
                sources=(),
                embedding=vec,
            )
            for i in range(n)
        ),
    )


def test_curriculum_question_retrieves_twelve_chunks() -> None:
    index = _index_n_same_vector(12)

    def fake_embed(texts: list[str]) -> list[list[float]]:
        del texts
        return [[1.0, 0.0]]

    curriculum = retrieve_miit_embed(
        "CSE year 1 semester courses",
        index=index,
        min_similarity=0.5,
        embed_fn=fake_embed,
    )
    assert len(curriculum.chunks) == 12

    who = retrieve_miit_embed(
        "Cynthia Myint ဆိုတာ ဘယ်သူလဲ?",
        index=index,
        min_similarity=0.5,
        embed_fn=fake_embed,
    )
    assert len(who.chunks) == config.MIIT_TOP_K


def test_institute_overview_loads_from_disk() -> None:
    ids = {chunk.id for chunk in load_miit_chunks()}
    assert "institute-overview" in ids
    assert "institute-governance" in ids
    assert "cynthia-role" in ids
    assert "cynthia-email" in ids
    assert "cse-overview" in ids
    assert "cse-y1-s1" in ids


def test_usestate_skips_embed_fn() -> None:
    calls: list[list[str]] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        raise AssertionError("programming questions must not call embed")

    result = retrieve_miit_embed(
        "useState hook ကို ဘယ်လို သုံးမလဲ?",
        index=_index_with_vectors([1.0, 0.0], [0.0, 1.0]),
        embed_fn=fake_embed,
    )
    assert result.chunks == []
    assert calls == []


def test_burmese_name_calls_embed_fn() -> None:
    calls: list[list[str]] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return [[1.0, 0.0]]

    result = retrieve_miit_embed(
        "ဒေါ်စင်သီယာမြင့် ဆိုတာ ဘယ်သူလဲ?",
        index=_index_with_vectors([1.0, 0.0], [0.0, 1.0]),
        min_similarity=0.5,
        embed_fn=fake_embed,
    )
    assert calls
    assert result.chunks
    assert result.chunks[0].id == "chunk-a"


def test_cynthida_calls_embed_fn() -> None:
    calls: list[list[str]] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return [[1.0, 0.0]]

    result = retrieve_miit_embed(
        "Cynthida Myint ဆိုတာ ဘယ်သူလဲ?",
        index=_index_with_vectors([1.0, 0.0], [0.0, 1.0]),
        min_similarity=0.5,
        embed_fn=fake_embed,
    )
    assert calls
    assert result.chunks
    assert result.chunks[0].id == "chunk-a"


def test_embed_429_falls_back_to_token(monkeypatch) -> None:
    from google.genai.errors import ClientError

    from tutor.knowledge import KnowledgeChunk, tokenize

    chunk = KnowledgeChunk(
        id="cynthia-role",
        text="Cynthia Myint MIIT professor",
        sources=(),
        tokens=tokenize("Cynthia Myint MIIT professor"),
    )
    monkeypatch.setattr("tutor.knowledge.miit_chunks", lambda: (chunk,))

    def boom(_texts: list[str]) -> list[list[float]]:
        raise ClientError(429, {"error": {"status": "RESOURCE_EXHAUSTED"}}, None)

    result = retrieve_miit_embed(
        "Cynthia Myint ဆိုတာ ဘယ်သူလဲ?",
        index=_index_with_vectors([1.0, 0.0], [0.0, 1.0]),
        embed_fn=boom,
    )
    assert result.chunks
    assert result.chunks[0].id == "cynthia-role"


def test_token_retrieval_cynthia_name() -> None:
    from tutor.knowledge import KnowledgeChunk, tokenize

    chunk = KnowledgeChunk(
        id="cynthia-role",
        text="Cynthia Myint MIIT professor",
        sources=(),
        tokens=tokenize("Cynthia Myint MIIT professor"),
    )
    result = retrieve_miit_token(
        "Cynthia Myint ဆိုတာ ဘယ်သူလဲ?",
        chunks=[chunk],
    )
    assert result.chunks
    assert result.chunks[0].id == "cynthia-role"


def test_retrieve_query_includes_prior_cynthia() -> None:
    history = [{"question": "Cynthia Myint ဆိုတာ ဘယ်သူလဲ?", "answer": "MIIT professor"}]
    query = retrieve_query("သူမ papers", history)
    assert "Cynthia" in query
    assert "သူမ papers" in query
