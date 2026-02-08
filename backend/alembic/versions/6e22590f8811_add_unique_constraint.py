"""add_unique_constraint_to_chat_sessions

Revision ID: 6e22590f8811
Revises: 5e22590f8810
Create Date: 2026-02-08 18:18:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6e22590f8811'
down_revision: Union[str, Sequence[str], None] = '5e22590f8810'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add UniqueConstraint with NULLS NOT DISTINCT (Postgres 15+)
    # This prevents duplicate sessions even when schedule_id/library_id are NULL
    op.create_unique_constraint(
        'uq_chat_session_user_agent_context',
        'chat_sessions',
        ['user_id', 'agent_slug', 'schedule_id', 'library_id'],
        postgresql_nulls_not_distinct=True
    )


def downgrade() -> None:
    op.drop_constraint('uq_chat_session_user_agent_context', 'chat_sessions', type_='unique')
