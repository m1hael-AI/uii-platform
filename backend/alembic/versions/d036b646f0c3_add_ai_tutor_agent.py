"""add ai_tutor agent

Revision ID: d036b646f0c3
Revises: fb0ef2d69e78
Create Date: 2026-02-06 16:19:50.886990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd036b646f0c3'
down_revision: Union[str, Sequence[str], None] = 'fb0ef2d69e78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        INSERT INTO agents (slug, name, description, system_prompt, is_active, greeting_message, created_at, updated_at)
        VALUES (
            'ai_tutor',
            'AI-тьютор',
            'Персональный тьютор для работы с материалами библиотеки',
            'Ты AI-тьютор. Твоя задача — помогать студентам разбираться с учебными материалами из библиотеки. Отвечай понятно, структурированно, приводи примеры. Если студент не понял, объясни проще.',
            true,
            'Привет! Я AI-тьютор. Готов помочь разобраться с материалами из библиотеки. О чём хочешь узнать?',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (slug) DO NOTHING;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM agents WHERE slug = 'ai_tutor';")

