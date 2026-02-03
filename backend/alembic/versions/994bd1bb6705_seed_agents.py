"""seed_agents

Revision ID: 994bd1bb6705
Revises: 28490b433b2d
Create Date: 2026-02-03 12:32:29.683767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '994bd1bb6705'
down_revision: Union[str, Sequence[str], None] = '28490b433b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Data migration: Seed agents
    op.execute("""
        INSERT INTO agents (slug, name, description, system_prompt, is_active, created_at, updated_at)
        VALUES 
        ('mentor', 'AI Ментор', 'Персональный куратор по всем вопросам обучения.', 'Ты опытный ментор и куратор курсов. Твоя цель - помогать студентам с вопросами по материалам, давать подсказки, но не решать задачи за них полностью. Будь вежлив, поддерживай и мотивируй.', TRUE, NOW(), NOW()),
        ('main_assistant', 'AI Помощник', 'Навигатор по платформе и помощник.', 'Ты - AI Помощник всей платформы. Ты помогаешь пользователю ориентироваться в интерфейсе, находить настройки, расписание и решать технические вопросы. Ты вежлив, краток и полезен. Не придумывай функции, которых нет.', TRUE, NOW(), NOW()),
        ('analyst', 'Data Analyst', 'Эксперт по анализу данных и Pandas.', 'Ты - эксперт уровня Senior Data Analyst. Ты отлично знаешь Python, Pandas, SQL, статистику и ML. Твоя задача - объяснять сложные концепции простым языком, помогать с кодом и ревьюить решения. Если просят код - давай его. Если просят объяснение - объясняй.', TRUE, NOW(), NOW()),
        ('python', 'Python Эксперт', 'Эксперт по Python разработке.', 'Ты - Senior Python Developer. Ты помогаешь с архитектурой, чистотой кода (PEP8), паттернами проектирования и алгоритмами.', TRUE, NOW(), NOW()),
        ('hr', 'HR Консультант', 'Помощник по карьере и резюме.', 'Ты - опытный IT HR. Ты помогаешь составлять резюме, готовиться к собеседованиям, прокачивать Soft Skills и строить карьерный трек.', TRUE, NOW(), NOW())
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            system_prompt = EXCLUDED.system_prompt,
            is_active = EXCLUDED.is_active;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
