"""add chat_settings table

Revision ID: fb0ef2d69e78
Revises: d9296f4bc0b3
Create Date: 2026-02-06 16:13:20.757893

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb0ef2d69e78'
down_revision: Union[str, Sequence[str], None] = 'd9296f4bc0b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'chat_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        # Блок 1: Общение с пользователями
        sa.Column('user_chat_model', sa.String(), nullable=False, server_default='gpt-4o'),
        sa.Column('user_chat_temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('user_chat_max_tokens', sa.Integer(), nullable=True, server_default='4096'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, server_default='15'),
        # Блок 2: Вечный диалог (Сжатие контекста)
        sa.Column('compression_model', sa.String(), nullable=False, server_default='gpt-4.1-mini'),
        sa.Column('compression_temperature', sa.Float(), nullable=False, server_default='0.2'),
        sa.Column('compression_max_tokens', sa.Integer(), nullable=True),
        sa.Column('context_threshold', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('context_compression_keep_last', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('context_soft_limit', sa.Integer(), nullable=False, server_default='350000'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('chat_settings')
