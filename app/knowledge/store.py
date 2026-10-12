from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.ai.errors import LlmUnavailableError
from app.ai.gemini_embed import TASK_DOCUMENT, TASK_QUERY, embed_text, embedding_to_literal
from app.ai.gemini_pool import is_not_found_error
from app.lib.config import get_database_url, get_knowledge_dir, get_rag_top_k
from app.services.documents.pdf_extract import extract_pdf_words

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1500
_SKIP_PREFIX = '_'
_NGRAM_SIZE = 3

CATEGORY_FACULTY = 'faculty'
CATEGORY_CAMPUS = 'campus'
CATEGORY_COURSES = 'courses'

_engine: AsyncEngine | None = None
_ingest_lock = asyncio.Lock()
_last_ingest_stamp = 0.0
_embed_model_missing = False


@dataclass
class KnowledgeChunk:
    id: str
    text: str
    sources: list[str]
    category: str
    source_file: str = ''
    score: float = 0.0


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        database_url = get_database_url()
        created = create_async_engine(database_url)
        _engine = created
    return _engine


def _is_loadable_jsonl(path: Path) -> bool:
    if path.suffix != '.jsonl':
        return False
    if path.name.startswith(_SKIP_PREFIX):
        return False
    return True


def _parse_sources(raw: object) -> list[str]:
    sources: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and len(item.strip()) > 0:
                sources.append(item)
        return sources
    if isinstance(raw, str) and len(raw.strip()) > 0:
        sources.append(raw)
    return sources


def _chunk_text(text: str) -> list[str]:
    trimmed = text.strip()
    if len(trimmed) == 0:
        return []
    parts: list[str] = []
    start = 0
    length = len(trimmed)
    while start < length:
        end = start + _CHUNK_SIZE
        piece = trimmed[start:end]
        parts.append(piece)
        start = end
    return parts


def _hash_text(text: str) -> str:
    encoded = text.encode('utf-8')
    digest = hashlib.sha256(encoded)
    hex_digest = digest.hexdigest()
    return hex_digest


def _relative_source(path: Path) -> str:
    knowledge_dir = get_knowledge_dir()
    try:
        relative = path.relative_to(knowledge_dir)
        return str(relative)
    except ValueError:
        return path.name


def _chunks_from_jsonl(path: Path, category: str) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    try:
        raw = path.read_text(encoding='utf-8')
    except OSError as error:
        logger.warning('Could not read knowledge file %s: %s', path, error)
        return chunks
    source_file = _relative_source(path)
    lines = raw.splitlines()
    for line in lines:
        stripped = line.strip()
        if len(stripped) == 0:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as error:
            logger.warning('Skip invalid JSONL in %s: %s', path, error)
            continue
        if not isinstance(payload, dict):
            continue
        record_id = payload.get('id')
        text = payload.get('text')
        if not isinstance(record_id, str) or not isinstance(text, str):
            continue
        if len(text.strip()) == 0:
            continue
        sources = _parse_sources(payload.get('sources'))
        extras: list[str] = []
        extra_keys = ['name', 'role', 'department', 'course_code', 'title', 'teacher', 'code']
        for key in extra_keys:
            value = payload.get(key)
            if isinstance(value, str) and len(value.strip()) > 0:
                extras.append(value)
        extra_blob = ' '.join(extras)
        if len(extra_blob) > 0:
            combined = extra_blob + '\n' + text
        else:
            combined = text
        chunk = KnowledgeChunk(
            id=record_id,
            text=combined,
            sources=sources,
            category=category,
            source_file=source_file,
        )
        chunks.append(chunk)
    return chunks


def _chunks_from_pdf(path: Path) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    try:
        extracted_text, _words = extract_pdf_words(path)
    except Exception as error:
        logger.warning('Could not extract handout PDF %s: %s', path, error)
        return chunks
    source_file = _relative_source(path)
    parts = _chunk_text(extracted_text)
    part_index = 0
    while part_index < len(parts):
        part = parts[part_index]
        chunk_id = f'{path.stem}-{part_index + 1}'
        sources: list[str] = []
        sources.append(path.name)
        chunk = KnowledgeChunk(
            id=chunk_id,
            text=part,
            sources=sources,
            category=CATEGORY_COURSES,
            source_file=source_file,
        )
        chunks.append(chunk)
        part_index = part_index + 1
    return chunks


def _collect_category(category: str) -> list[KnowledgeChunk]:
    knowledge_dir = get_knowledge_dir()
    chunks: list[KnowledgeChunk] = []
    if category == CATEGORY_FACULTY:
        folder = knowledge_dir / 'faculty'
        if folder.is_dir():
            for path in folder.iterdir():
                if _is_loadable_jsonl(path):
                    file_chunks = _chunks_from_jsonl(path, CATEGORY_FACULTY)
                    chunks.extend(file_chunks)
        return chunks
    if category == CATEGORY_CAMPUS:
        folder = knowledge_dir / 'campus'
        if folder.is_dir():
            for path in folder.iterdir():
                if _is_loadable_jsonl(path):
                    file_chunks = _chunks_from_jsonl(path, CATEGORY_CAMPUS)
                    chunks.extend(file_chunks)
        return chunks
    if category == CATEGORY_COURSES:
        folder = knowledge_dir / 'courses'
        if folder.is_dir():
            for path in folder.iterdir():
                if path.is_file() and _is_loadable_jsonl(path):
                    file_chunks = _chunks_from_jsonl(path, CATEGORY_COURSES)
                    chunks.extend(file_chunks)
        handouts = knowledge_dir / 'courses' / 'handouts'
        if handouts.is_dir():
            for path in handouts.iterdir():
                suffix = path.suffix
                lowered_suffix = suffix.lower()
                if lowered_suffix == '.pdf':
                    file_chunks = _chunks_from_pdf(path)
                    chunks.extend(file_chunks)
        return chunks
    return chunks


def _collect_all() -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    faculty = _collect_category(CATEGORY_FACULTY)
    chunks.extend(faculty)
    campus = _collect_category(CATEGORY_CAMPUS)
    chunks.extend(campus)
    courses = _collect_category(CATEGORY_COURSES)
    chunks.extend(courses)
    return chunks


def _knowledge_stamp() -> float:
    knowledge_dir = get_knowledge_dir()
    if not knowledge_dir.is_dir():
        return 0.0
    latest = 0.0
    for path in knowledge_dir.rglob('*'):
        if not path.is_file():
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime > latest:
            latest = mtime
    return latest


def _char_ngrams(text: str) -> set[str]:
    lowered = text.lower()
    grams: set[str] = set()
    length = len(lowered)
    if length == 0:
        return grams
    if length < _NGRAM_SIZE:
        grams.add(lowered)
        return grams
    start = 0
    last = length - _NGRAM_SIZE
    while start <= last:
        gram = lowered[start : start + _NGRAM_SIZE]
        grams.add(gram)
        start = start + 1
    return grams


def _ngram_score(query: str, chunk: KnowledgeChunk) -> float:
    query_grams = _char_ngrams(query)
    if len(query_grams) == 0:
        return 0.0
    text_grams = _char_ngrams(chunk.text)
    id_grams = _char_ngrams(chunk.id)
    combined = text_grams.union(id_grams)
    overlap = query_grams.intersection(combined)
    score = len(overlap) / len(query_grams)
    return score


def _ngram_retrieve(category: str, query: str, limit: int) -> list[KnowledgeChunk]:
    chunks = _collect_category(category)
    scored: list[KnowledgeChunk] = []
    for chunk in chunks:
        score = _ngram_score(query, chunk)
        if score <= 0:
            continue
        scored_chunk = KnowledgeChunk(
            id=chunk.id,
            text=chunk.text,
            sources=chunk.sources,
            category=chunk.category,
            source_file=chunk.source_file,
            score=score,
        )
        scored.append(scored_chunk)
    scored.sort(key=lambda item: item.score, reverse=True)
    top = scored[:limit]
    return top


def _parse_sources_db(raw: object) -> list[str]:
    if isinstance(raw, list):
        parsed: list[str] = []
        for item in raw:
            if isinstance(item, str):
                parsed.append(item)
        return parsed
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return _parse_sources_db(loaded)
    return []


async def ingest_knowledge() -> None:
    global _last_ingest_stamp
    global _embed_model_missing
    if _embed_model_missing:
        return
    stamp = _knowledge_stamp()
    async with _ingest_lock:
        if _embed_model_missing:
            return
        if stamp > 0 and stamp <= _last_ingest_stamp:
            return
        chunks = _collect_all()
        engine = _get_engine()
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            existing_result = await session.execute(
                text('SELECT source_file, record_id, content_hash FROM knowledge_chunks')
            )
            existing_rows = existing_result.all()
            existing: dict[tuple[str, str], str] = {}
            for row in existing_rows:
                key = (str(row.source_file), str(row.record_id))
                existing[key] = str(row.content_hash)

            live_keys: set[tuple[str, str]] = set()
            for chunk in chunks:
                key = (chunk.source_file, chunk.id)
                live_keys.add(key)
                current_hash = _hash_text(chunk.text)
                previous = existing.get(key)
                if previous == current_hash:
                    continue
                try:
                    vector = await embed_text(chunk.text, TASK_DOCUMENT)
                except LlmUnavailableError as error:
                    if is_not_found_error(error):
                        _embed_model_missing = True
                        logger.error(
                            'Embedding model is not available; stopping ingest. Fix GEMINI_EMBEDDING_MODEL and restart.'
                        )
                        return
                    logger.warning('Skip embedding %s/%s: %s', chunk.source_file, chunk.id, error)
                    continue
                literal = embedding_to_literal(vector)
                sources_json = json.dumps(chunk.sources, ensure_ascii=False)
                params: dict[str, object] = {}
                params['category'] = chunk.category
                params['source_file'] = chunk.source_file
                params['record_id'] = chunk.id
                params['text'] = chunk.text
                params['sources'] = sources_json
                params['content_hash'] = current_hash
                params['embedding'] = literal
                if previous is None:
                    params['id'] = str(uuid.uuid4())
                    await session.execute(
                        text(
                            """
                            INSERT INTO knowledge_chunks (
                                id, category, source_file, record_id, text, sources, content_hash, embedding
                            )
                            VALUES (
                                CAST(:id AS uuid),
                                :category,
                                :source_file,
                                :record_id,
                                :text,
                                CAST(:sources AS jsonb),
                                :content_hash,
                                CAST(:embedding AS vector)
                            )
                            """
                        ),
                        params,
                    )
                else:
                    await session.execute(
                        text(
                            """
                            UPDATE knowledge_chunks
                            SET category = :category,
                                text = :text,
                                sources = CAST(:sources AS jsonb),
                                content_hash = :content_hash,
                                embedding = CAST(:embedding AS vector)
                            WHERE source_file = :source_file AND record_id = :record_id
                            """
                        ),
                        params,
                    )

            for key in existing:
                if key not in live_keys:
                    delete_params: dict[str, str] = {}
                    delete_params['source_file'] = key[0]
                    delete_params['record_id'] = key[1]
                    await session.execute(
                        text(
                            """
                            DELETE FROM knowledge_chunks
                            WHERE source_file = :source_file AND record_id = :record_id
                            """
                        ),
                        delete_params,
                    )
            await session.commit()
        _last_ingest_stamp = stamp
        logger.info('Knowledge ingest finished (%s file chunks).', len(chunks))


async def _vector_retrieve(
    category: str,
    query_embedding: list[float],
    limit: int,
) -> list[KnowledgeChunk]:
    literal = embedding_to_literal(query_embedding)
    engine = _get_engine()
    maker = async_sessionmaker(engine, expire_on_commit=False)
    params: dict[str, object] = {}
    params['category'] = category
    params['embedding'] = literal
    limit_int = int(limit)
    async with maker() as session:
        result = await session.execute(
            text(
                f"""
                SELECT record_id, text, sources, category, source_file,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS score
                FROM knowledge_chunks
                WHERE category = :category
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT {limit_int}
                """
            ),
            params,
        )
        rows = result.all()
    chunks: list[KnowledgeChunk] = []
    for row in rows:
        sources = _parse_sources_db(row.sources)
        score = float(row.score)
        chunk = KnowledgeChunk(
            id=str(row.record_id),
            text=str(row.text),
            sources=sources,
            category=str(row.category),
            source_file=str(row.source_file),
            score=score,
        )
        chunks.append(chunk)
    return chunks


async def retrieve(
    category: str,
    query: str,
    query_embedding: list[float] | None = None,
    limit: int | None = None,
) -> list[KnowledgeChunk]:
    if limit is None:
        limit = get_rag_top_k()
    stamp = _knowledge_stamp()
    if stamp > _last_ingest_stamp:
        try:
            await ingest_knowledge()
        except Exception as error:
            logger.warning('Knowledge ingest before retrieve failed: %s', error)

    if query_embedding is not None and len(query_embedding) > 0:
        try:
            chunks = await _vector_retrieve(category, query_embedding, limit)
            if len(chunks) > 0:
                return chunks
        except Exception as error:
            logger.warning('Vector retrieve failed; using n-gram fallback: %s', error)

    fallback = _ngram_retrieve(category, query, limit)
    return fallback


async def embed_query(query: str) -> list[float]:
    try:
        values = await embed_text(query, TASK_QUERY)
        return values
    except LlmUnavailableError as error:
        logger.warning('Query embedding failed; specialists will use n-gram fallback: %s', error)
        empty: list[float] = []
        return empty
