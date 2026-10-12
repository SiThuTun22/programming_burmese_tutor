"""Add pgvector knowledge_chunks for RAG.

Revision ID: 005_knowledge_chunks
Revises: 004_vision_description
Create Date: 2026-10-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '005_knowledge_chunks'
down_revision: str | None = '004_vision_description'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute(
        """
        CREATE TABLE knowledge_chunks (
            id UUID PRIMARY KEY,
            category VARCHAR(50) NOT NULL,
            source_file VARCHAR(1000) NOT NULL,
            record_id VARCHAR(255) NOT NULL,
            text TEXT NOT NULL,
            sources JSONB NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            embedding vector(768) NOT NULL
        )
        """
    )
    op.execute(
        """
        ALTER TABLE knowledge_chunks
        ADD CONSTRAINT uq_knowledge_chunks_source_record
        UNIQUE (source_file, record_id)
        """
    )
    op.execute(
        'CREATE INDEX ix_knowledge_chunks_category ON knowledge_chunks (category)'
    )
    op.execute(
        """
        CREATE INDEX knowledge_chunks_embedding_idx
        ON knowledge_chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS knowledge_chunks')
