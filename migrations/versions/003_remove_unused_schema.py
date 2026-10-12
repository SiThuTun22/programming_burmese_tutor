from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = '003_remove_unused_schema'
down_revision: str | None = '002_session_documents'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table('submissions')
    op.drop_column('chat_messages', 'keyword_context')


def downgrade() -> None:
    op.add_column(
        'chat_messages',
        sa.Column('keyword_context', sa.String(length=255), nullable=True),
    )
    op.create_table(
        'submissions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('chat_session_id', sa.Uuid(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('reference_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
