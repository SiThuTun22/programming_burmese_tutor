"""Add vision_description to session_documents.

Revision ID: 004_vision_description
Revises: 003_remove_unused_schema
Create Date: 2026-07-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '004_vision_description'
down_revision: str | None = '003_remove_unused_schema'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'session_documents',
        sa.Column('vision_description', sa.Text(), nullable=False, server_default=''),
    )


def downgrade() -> None:
    op.drop_column('session_documents', 'vision_description')
