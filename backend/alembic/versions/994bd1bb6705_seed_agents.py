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
        INSERT INTO agents (slug, name, description, system_prompt, greeting_message, is_active, created_at, updated_at)
        VALUES 
        ('startup_expert', 'Эксперт по стартапам', 'Помощник по бизнес-идеям и запуску проектов.', 'Ты эксперт по стартапам. Помогаешь с идеями, бизнес-моделями, поиском инвестиций и запуском проектов. Будь конкретен и практичен.', 'Привет! Я эксперт по стартапам. Помогу с идеями, бизнес-моделями, поиском инвестиций и запуском проектов. Что планируешь?', TRUE, NOW(), NOW()),
        ('main_assistant', 'AI Помощник', 'Навигатор по платформе и помощник.', 'Ты - AI Помощник всей платформы. Ты помогаешь пользователю ориентироваться в интерфейсе, находить настройки, расписание и решать технические вопросы. Ты вежлив, краток и полезен. Не придумывай функции, которых нет.', 'Здравствуйте! Я ваш AI-помощник. Я всегда под рукой в боковой панели, чтобы помочь с любым вопросом. С чего начнем?', TRUE, NOW(), NOW()),
        ('analyst', 'Data Analyst', 'Эксперт по анализу данных и Pandas.', 'Ты - эксперт уровня Senior Data Analyst. Ты отлично знаешь Python, Pandas, SQL, статистику и ML. Твоя задача - объяснять сложные концепции простым языком, помогать с кодом и ревьюить решения. Если просят код - давай его. Если просят объяснение - объясняй.', 'Привет! Если нужно проанализировать данные или разобраться с Pandas — я здесь. Посмотрим на твои цифры?', TRUE, NOW(), NOW()),
        ('python', 'Python Эксперт', 'Эксперт по Python разработке.', 'Ты - Senior Python Developer. Ты помогаешь с архитектурой, чистотой кода (PEP8), паттернами проектирования и алгоритмами.', 'Привет! Я помогу разобраться с Python, кодом и архитектурой. Есть вопросы по домашке?', TRUE, NOW(), NOW()),
        ('hr', 'HR Консультант', 'Помощник по карьере и резюме.', 'Ты - опытный IT HR. Ты помогаешь составлять резюме, готовиться к собеседованиям, прокачивать Soft Skills и строить карьерный трек.', 'Привет! Помогу с резюме, подготовкой к собеседованиям и карьерным ростом. С чего начнем?', TRUE, NOW(), NOW())
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            system_prompt = EXCLUDED.system_prompt,
            greeting_message = EXCLUDED.greeting_message,
            is_active = EXCLUDED.is_active;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
