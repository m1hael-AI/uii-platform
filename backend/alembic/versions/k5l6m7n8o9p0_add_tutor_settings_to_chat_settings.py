"""add_tutor_settings_to_chat_settings

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-02-21 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k5l6m7n8o9p0'
down_revision: Union[str, Sequence[str], None] = 'j4k5l6m7n8o9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tutor_* columns to chat_settings table."""
    op.add_column('chat_settings', sa.Column('tutor_model', sa.String(), nullable=False, server_default='gpt-4o-mini'))
    op.add_column('chat_settings', sa.Column('tutor_temperature', sa.Float(), nullable=False, server_default='0.2'))
    op.add_column('chat_settings', sa.Column('tutor_max_tokens', sa.Integer(), nullable=True))
    op.add_column('chat_settings', sa.Column('tutor_rate_limit_per_minute', sa.Integer(), nullable=False, server_default='10'))


def downgrade() -> None:
    """Remove tutor_* columns from chat_settings table."""
    op.drop_column('chat_settings', 'tutor_rate_limit_per_minute')
    op.drop_column('chat_settings', 'tutor_max_tokens')
    op.drop_column('chat_settings', 'tutor_temperature')
    op.drop_column('chat_settings', 'tutor_model')
