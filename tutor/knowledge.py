"""Load MIIT notes and retrieve by embeddings or token overlap."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from tutor.config import (
    MIIT_DIR,
    MIIT_INDEX_PATH,
    MIIT_MIN_SIMILARITY,
    MIIT_RETRIEVAL,
    MIIT_TOP_K,
)
LATIN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#-]*")
MYANMAR_RE = re.compile(r"[\u1000-\u109F]{2,}")
TOKEN_MIN_SCORE = 1.0
MIIT_HINTS = (
    "miit",
    "cynthia",
    "cynthida",
    "myint",
    "sin thi yar",
    "ucsm",
    "faculty",
    "professor",
    "campus",
    "ပါမောက္ခ",
    "ပါမောက္ခချုပ်",
    "မန္တလေးကွန်ပျူတာ",
    "စင်သီယာ",
    "ဒေါ်စင်သီယာ",
    "ဝင်းအေး",
    "win aye",
    "iiit",
    "iiit-b",
    "cse",
    "ece",
    "pgdsd",
    "aye aye thant",
    "kyawt",
    "phyu thwe",
    "tin moh",
    "zar chi",
    "hlaing",
    "admission",
    "ဝင်ခွင့်",
    "lecturer",
)
PAPER_HINTS = (
    "paper",
    "papers",
    "publication",
    "researchgate",
    "စာတမ်း",
    "သုတေသန",
    "detail",
    "အသေးစိတ်",
    "segmentation",
    "pos",
)
CURRICULUM_HINTS = (
    "curriculum",
    "semester",
    "elective",
    "capstone",
    "သင်ရိုး",
    "ခရက်ဒစ်",
    "ဘာသာရပ်ကုဒ်",
    "ပညာသင်နှစ်",
    "သင်တန်း",
    "သင်ကြား",
    "ဘာသာတွေ",
    "hons",
)
PROGRAM_DETAIL_HINTS = (
    "အသေးစိတ်",
    "detail",
    "အပြည့်",
)
PROGRAM_QUERY_HINTS = (
    "cse",
    "ece",
    "hons",
    "semester",
    "သင်တန်း",
    "ပညာသင်နှစ်",
    "elective",
    "capstone",
    "ဘာသာတွေ",
    "သင်ကြား",
)
PAPER_TOP_K = 5
CURRICULUM_TOP_K = 12
STOPWORDS = {
    "the",
    "and",
    "with",
    "for",
    "from",
    "using",
    "of",
    "in",
    "on",
    "to",
    "a",
    "an",
    "is",
    "or",
    "by",
    "at",
    "code",
    "language",
    "programming",
    "computer",
    "information",
    "technology",
    "systems",
    "research",
    "paper",
    "international",
    "journal",
    "text",
    "word",
    "written",
    "part",
    "speech",
    "natural",
    "processing",
    "ဆိုတာ",
    "ဘာလဲ",
    "ဘယ်လို",
    "ရှင်းပြပါ",
    "သုံးမလဲ",
    "ကွာခြားချက်",
    "ဒီ",
    "ကို",
    "သည်",
    "မှာ",
    "တွင်",
    "နှင့်",
    "တို့",
    "သော",
    "၍",
    "မှ",
    "၏",
    "ဟု",
    "လည်း",
    "အတွက်",
    "အကြောင်း",
    "ဖြစ်ပါသည်",
    "ရှိပါသည်",
}


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    text: str
    sources: tuple[str, ...]
    tokens: frozenset[str]


@dataclass(frozen=True)
class IndexedChunk:
    id: str
    text: str
    sources: tuple[str, ...]
    embedding: tuple[float, ...]

    def as_knowledge_chunk(self) -> KnowledgeChunk:
        return KnowledgeChunk(
            id=self.id,
            text=self.text,
            sources=self.sources,
            tokens=tokenize(self.text),
        )


@dataclass(frozen=True)
class MiitIndex:
    embed_model: str
    built_at: str
    chunks: tuple[IndexedChunk, ...]


@dataclass(frozen=True)
class RetrieveResult:
    chunks: list[KnowledgeChunk]
    best_score: float | None


def looks_like_miit(question: str) -> bool:
    lowered = question.lower()
    return any(hint in lowered for hint in MIIT_HINTS)


def looks_like_papers(question: str) -> bool:
    lowered = question.lower()
    return any(hint in lowered for hint in PAPER_HINTS)


def looks_like_curriculum(question: str) -> bool:
    lowered = question.lower()
    if any(hint in lowered for hint in CURRICULUM_HINTS):
        return True
    if any(hint in lowered for hint in PROGRAM_DETAIL_HINTS) and any(
        hint in lowered for hint in PROGRAM_QUERY_HINTS
    ):
        return True
    return False


def retrieve_query(question: str, history: list[dict] | None = None) -> str:
    parts: list[str] = []
    for turn in list(history or [])[-2:]:
        prior = str(turn.get("question", "")).strip()
        if prior:
            parts.append(prior)
    current = question.strip()
    if current:
        parts.append(current)
    return " ".join(parts)


def effective_miit_limit(question: str, limit: int = MIIT_TOP_K) -> int:
    if looks_like_curriculum(question):
        return max(limit, CURRICULUM_TOP_K)
    if looks_like_papers(question):
        return max(limit, PAPER_TOP_K)
    return limit


def _is_embed_quota_error(exc: BaseException) -> bool:
    code = getattr(exc, "code", None)
    if code == 429:
        return True
    message = str(exc)
    return "429" in message or "RESOURCE_EXHAUSTED" in message


@lru_cache(maxsize=64)
def _cached_query_embedding(question: str) -> tuple[float, ...]:
    from tutor.gemini_client import GeminiClient

    vectors = GeminiClient().embed([question])
    if not vectors:
        return ()
    return tuple(float(v) for v in vectors[0])


def tokenize(text: str) -> frozenset[str]:
    latin = {match.group(0).lower() for match in LATIN_RE.finditer(text)}
    myanmar = {match.group(0) for match in MYANMAR_RE.finditer(text)}
    return frozenset(token for token in latin | myanmar if token not in STOPWORDS)


def load_miit_chunks(directory: Path | None = None) -> list[KnowledgeChunk]:
    folder = directory or MIIT_DIR
    if not folder.is_dir():
        return []
    chunks: list[KnowledgeChunk] = []
    for path in sorted(folder.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = str(row.get("text", "")).strip()
            if not text:
                continue
            sources = tuple(str(url) for url in row.get("sources", []) if str(url).strip())
            chunks.append(
                KnowledgeChunk(
                    id=str(row.get("id", "")),
                    text=text,
                    sources=sources,
                    tokens=tokenize(text),
                )
            )
    return chunks


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def index_document_from_rows(
    rows: list[dict[str, Any]],
    *,
    embed_model: str,
    vectors: list[list[float]],
) -> dict[str, Any]:
    if len(rows) != len(vectors):
        raise ValueError("rows and vectors length mismatch")
    chunks: list[dict[str, Any]] = []
    for row, vector in zip(rows, vectors, strict=True):
        chunks.append(
            {
                "id": str(row["id"]),
                "text": str(row["text"]),
                "sources": list(row.get("sources", [])),
                "embedding": vector,
            }
        )
    return {
        "embed_model": embed_model,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "chunks": chunks,
    }


def parse_miit_index(data: dict[str, Any]) -> MiitIndex:
    indexed: list[IndexedChunk] = []
    for row in data.get("chunks", []):
        text = str(row.get("text", "")).strip()
        if not text:
            continue
        embedding = row.get("embedding")
        if not embedding:
            continue
        sources = tuple(str(url) for url in row.get("sources", []) if str(url).strip())
        indexed.append(
            IndexedChunk(
                id=str(row.get("id", "")),
                text=text,
                sources=sources,
                embedding=tuple(float(v) for v in embedding),
            )
        )
    return MiitIndex(
        embed_model=str(data.get("embed_model", "")),
        built_at=str(data.get("built_at", "")),
        chunks=tuple(indexed),
    )


def load_miit_index(path: Path | None = None) -> MiitIndex | None:
    index_path = path or MIIT_INDEX_PATH
    if not index_path.is_file():
        return None
    data = json.loads(index_path.read_text(encoding="utf-8"))
    index = parse_miit_index(data)
    return index if index.chunks else None


@lru_cache(maxsize=1)
def miit_index_cached() -> MiitIndex | None:
    return load_miit_index()


def clear_miit_caches() -> None:
    miit_index_cached.cache_clear()
    miit_chunks.cache_clear()
    _cached_query_embedding.cache_clear()


@lru_cache(maxsize=1)
def miit_chunks() -> tuple[KnowledgeChunk, ...]:
    return tuple(load_miit_chunks())


def retrieve_miit_token(
    question: str,
    *,
    chunks: list[KnowledgeChunk] | tuple[KnowledgeChunk, ...] | None = None,
    limit: int = MIIT_TOP_K,
    min_score: float = TOKEN_MIN_SCORE,
) -> RetrieveResult:
    query_tokens = tokenize(question)
    if not query_tokens:
        return RetrieveResult(chunks=[], best_score=None)
    pool = chunks if chunks is not None else miit_chunks()
    scored: list[tuple[float, KnowledgeChunk]] = []
    for chunk in pool:
        overlap = len(query_tokens & chunk.tokens)
        if overlap >= min_score:
            scored.append((float(overlap), chunk))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    picked = [chunk for _, chunk in scored[:limit]]
    best = scored[0][0] if scored else None
    return RetrieveResult(chunks=picked, best_score=best)


def rank_by_embeddings(
    query_vector: list[float],
    indexed: tuple[IndexedChunk, ...],
    *,
    limit: int = MIIT_TOP_K,
    min_similarity: float = MIIT_MIN_SIMILARITY,
) -> RetrieveResult:
    query = np.asarray(query_vector, dtype=np.float64)
    scored: list[tuple[float, IndexedChunk]] = []
    for chunk in indexed:
        sim = cosine_similarity(query, np.asarray(chunk.embedding, dtype=np.float64))
        if sim >= min_similarity:
            scored.append((sim, chunk))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    picked = [item[1].as_knowledge_chunk() for item in scored[:limit]]
    best = scored[0][0] if scored else None
    return RetrieveResult(chunks=picked, best_score=best)


def retrieve_miit_embed(
    question: str,
    *,
    history: list[dict] | None = None,
    index: MiitIndex | None = None,
    limit: int = MIIT_TOP_K,
    min_similarity: float = MIIT_MIN_SIMILARITY,
    embed_fn: Any | None = None,
) -> RetrieveResult:
    query = retrieve_query(question, history)
    if not looks_like_miit(query):
        return RetrieveResult(chunks=[], best_score=None)

    loaded = index if index is not None else miit_index_cached()
    if loaded is None:
        print(
            "miit: index missing; falling back to token overlap. Run: make miit-index",
            file=sys.stderr,
        )
        return retrieve_miit_token(query, limit=effective_miit_limit(query, limit))

    stripped = query.strip()
    try:
        if embed_fn is None:
            cached = _cached_query_embedding(stripped)
            vectors = [list(cached)] if cached else []
        else:
            vectors = embed_fn([stripped])
    except Exception as exc:
        if _is_embed_quota_error(exc):
            print("miit: embed quota hit; falling back to token overlap", file=sys.stderr)
            return retrieve_miit_token(query, limit=effective_miit_limit(query, limit))
        raise

    if not vectors:
        return RetrieveResult(chunks=[], best_score=None)
    return rank_by_embeddings(
        vectors[0],
        loaded.chunks,
        limit=effective_miit_limit(query, limit),
        min_similarity=min_similarity,
    )


def retrieve_miit(
    question: str,
    *,
    history: list[dict] | None = None,
    limit: int = MIIT_TOP_K,
    embed_fn: Any | None = None,
    index: MiitIndex | None = None,
) -> RetrieveResult:
    query = retrieve_query(question, history)
    if not looks_like_miit(query):
        return RetrieveResult(chunks=[], best_score=None)
    if MIIT_RETRIEVAL == "token":
        return retrieve_miit_token(query, limit=effective_miit_limit(query, limit))
    return retrieve_miit_embed(
        question,
        history=history,
        index=index,
        limit=limit,
        embed_fn=embed_fn,
    )
