"""add_soft_delete_and_proactivity_settings

Revision ID: edf786632b0f
Revises: d036b646f0c3
Create Date: 2026-02-06 19:41:50.620895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# revision identifiers, used by Alembic.
revision: str = 'edf786632b0f'
down_revision: Union[str, Sequence[str], None] = 'fb0ef2d69e78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_archived to messages table
    op.add_column('messages', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    
    # Add new settings to proactivity_settings table
    op.add_column('proactivity_settings', sa.Column('memory_update_interval', sa.Integer(), nullable=False, server_default='2'))
    op.add_column('proactivity_settings', sa.Column('proactivity_timeout', sa.Integer(), nullable=False, server_default='24'))
    op.add_column('proactivity_settings', sa.Column('max_consecutive_messages', sa.Integer(), nullable=False, server_default='3'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('proactivity_settings', 'max_consecutive_messages')
    op.drop_column('proactivity_settings', 'proactivity_timeout')
    op.drop_column('proactivity_settings', 'memory_update_interval')
    op.drop_column('messages', 'is_archived')
