"""Add tutor_avatar on chat_messages.

Revision ID: 006_message_tutor_avatar
Revises: 005_knowledge_chunks
Create Date: 2026-10-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '006_message_tutor_avatar'
down_revision: str | None = '005_knowledge_chunks'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'chat_messages',
        sa.Column('tutor_avatar', sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('chat_messages', 'tutor_avatar')
