from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
revision: str = '001_tutoring_skeleton'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table('users', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('email', sa.String(length=255), nullable=False), sa.Column('display_name', sa.String(length=255), nullable=False), sa.Column('password_hash', sa.String(length=255), nullable=False), sa.Column('is_active', sa.Boolean(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.PrimaryKeyConstraint('id'))
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('chat_sessions', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('title', sa.String(length=500), nullable=False), sa.Column('tutor_tone', sa.String(length=50), nullable=False), sa.Column('tutor_avatar', sa.String(length=50), nullable=False), sa.Column('status', sa.String(length=50), nullable=False), sa.Column('owner_id', sa.Uuid(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'), sa.PrimaryKeyConstraint('id'))
    op.create_table('submissions', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('chat_session_id', sa.Uuid(), nullable=False), sa.Column('question_text', sa.Text(), nullable=False), sa.Column('reference_text', sa.Text(), nullable=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.ForeignKeyConstraint(['chat_session_id'], ['chat_sessions.id'], ondelete='CASCADE'), sa.PrimaryKeyConstraint('id'))
    op.create_table('chat_messages', sa.Column('id', sa.Uuid(), nullable=False), sa.Column('chat_session_id', sa.Uuid(), nullable=False), sa.Column('role', sa.String(length=50), nullable=False), sa.Column('content', sa.Text(), nullable=False), sa.Column('keyword_context', sa.String(length=255), nullable=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), sa.ForeignKeyConstraint(['chat_session_id'], ['chat_sessions.id'], ondelete='CASCADE'), sa.PrimaryKeyConstraint('id'))

def downgrade() -> None:
    op.drop_table('chat_messages')
    op.drop_table('submissions')
    op.drop_table('chat_sessions')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
