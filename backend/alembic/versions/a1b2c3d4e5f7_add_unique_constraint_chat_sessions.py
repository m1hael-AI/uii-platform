"""add unique constraint chat sessions

Revision ID: a1b2c3d4e5f7
Revises: 02401e2ae68d
Create Date: 2026-02-07 11:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = '02401e2ae68d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint to prevent duplicate chat sessions."""
    
    # First, remove any existing duplicates
    op.execute("""
        DELETE FROM chat_sessions 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM chat_sessions 
            GROUP BY user_id, agent_slug, 
                     COALESCE(schedule_id, -1), 
                     COALESCE(library_id, -1)
        )
    """)
    
    # Add unique constraint
    # Note: PostgreSQL allows multiple NULL values in unique constraints,
    # so we use COALESCE to handle NULLs properly
    op.create_index(
        'uq_chat_sessions_user_agent_context',
        'chat_sessions',
        [
            'user_id', 
            'agent_slug', 
            sa.text('COALESCE(schedule_id, -1)'),
            sa.text('COALESCE(library_id, -1)')
        ],
        unique=True
    )


def downgrade() -> None:
    """Remove unique constraint."""
    op.drop_index('uq_chat_sessions_user_agent_context', table_name='chat_sessions')
