"""Add document_id on chat_messages.

Revision ID: 007_message_document_id
Revises: 006_message_tutor_avatar
Create Date: 2026-10-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '007_message_document_id'
down_revision: str | None = '006_message_tutor_avatar'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'chat_messages',
        sa.Column('document_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_chat_messages_document_id',
        'chat_messages',
        'session_documents',
        ['document_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_chat_messages_document_id',
        'chat_messages',
        type_='foreignkey',
    )
    op.drop_column('chat_messages', 'document_id')
