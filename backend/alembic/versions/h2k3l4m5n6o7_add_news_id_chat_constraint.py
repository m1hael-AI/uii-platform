"""Add news_id to ChatSession unique constraint

Revision ID: h2k3l4m5n6o7
Revises: g1h2i3j4k5l6
Create Date: 2026-02-19 13:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'h2k3l4m5n6o7'
down_revision = '1efbd166ed12'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Drop old constraint
    try:
        op.drop_constraint('uq_chat_session_user_agent_context', 'chat_sessions', type_='unique')
    except Exception as e:
        print(f"Warning: Constraint uq_chat_session_user_agent_context might not exist: {e}")

    # 2. Add new constraint including news_id
    # We use CREATE UNIQUE INDEX ... NULLS NOT DISTINCT logic which is standard for PG15+ unique constraints 
    # but SQLAlchemy op.create_unique_constraint usually maps to standard constraint.
    # The user model has `postgresql_nulls_not_distinct=True`.
    # Alembic supports this via `postgresql_nulls_not_distinct=True` in create_unique_constraint since 1.11
    
    op.create_unique_constraint(
        'uq_chat_session_user_agent_context',
        'chat_sessions',
        ['user_id', 'agent_slug', 'schedule_id', 'library_id', 'news_id'],
        postgresql_nulls_not_distinct=True
    )

def downgrade():
    # 1. Drop new constraint
    op.drop_constraint('uq_chat_session_user_agent_context', 'chat_sessions', type_='unique')

    # 2. Revert to old constraint (without news_id)
    op.create_unique_constraint(
        'uq_chat_session_user_agent_context',
        'chat_sessions',
        ['user_id', 'agent_slug', 'schedule_id', 'library_id'],
        postgresql_nulls_not_distinct=True
    )
