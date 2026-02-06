"""add_proactivity_v2_fields

Revision ID: b012c504ef6d
Revises: edf786632b0f
Create Date: 2026-02-06 20:04:05.111776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b012c504ef6d'
down_revision: Union[str, Sequence[str], None] = 'edf786632b0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add column to chat_sessions
    op.add_column('chat_sessions', sa.Column('last_proactivity_check_at', sa.DateTime(), nullable=True))

    # 2. Add columns to proactivity_settings
    op.add_column('proactivity_settings', sa.Column('compression_prompt', sa.Text(), nullable=True))
    op.add_column('proactivity_settings', sa.Column('proactivity_trigger_prompt', sa.Text(), nullable=True))
    
    # 3. Populate default prompts
    # Note: We use execute to set defaults for existing rows (if any)
    compression_prompt = """Ниже приведен фрагмент диалога между пользователем и AI-ассистентом.
Твоя задача — создать ПОДРОБНОЕ структурированное саммари этого диалога.

ТРЕБОВАНИЯ:
1. Перечисли ВСЕ основные темы, которые обсуждались
2. Сохрани ключевые вопросы пользователя и ответы AI
3. Укажи важные факты, имена, даты, технические термины
4. Структурируй по темам (используй маркеры или нумерацию)
5. Игнорируй только приветствия и общие фразы
6. Саммари должно быть достаточно детальным, чтобы AI мог продолжить разговор без потери контекста

=== ДИАЛОГ ===
{text_to_compress}
=== КОНЕЦ ДИАЛОГА ===

Создай подробное структурированное саммари:"""

    proactivity_trigger_prompt = """Ты — AI-ассистент, который заботится о пользователе.
Твоя задача — определить, стоит ли написать проактивное сообщение, чтобы вернуть пользователя к диалогу.

=== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ===
{user_profile}

=== ПОСЛЕДНИЕ СООБЩЕНИЯ ===
{recent_history}

=== ТЕКУЩАЯ ПАМЯТЬ ===
{current_memory}

=== ТВОЯ ЗАДАЧА ===
1. Проанализируй контекст. Прошло {hours_since_last_msg} часов молчания.
2. Определи, есть ли НЕЗАВЕРШЕННАЯ тема или ПОВОД написать?
   - Не пиши просто "Привет, как дела?".
   - Предложи продолжить конкретную тему.
   - Или предложи новый материал, релевантный интересам.
   - Если повода нет — не пиши.

Верни JSON:
{{
  "should_message": true,
  "reason": "Почему мы пишем (для логов)",
  "topic_context": "Сжатый контекст темы, которую нужно поднять (это пойдет в промпт генерации сообщения)"
}}

Если писать НЕ надо:
{{
  "should_message": false,
  "reason": "Нет явной темы для разговора"
}}"""

    # Escape single quotes in SQL
    compression_prompt_sql = compression_prompt.replace("'", "''")
    proactivity_trigger_prompt_sql = proactivity_trigger_prompt.replace("'", "''")

    op.execute(f"UPDATE proactivity_settings SET compression_prompt = '{compression_prompt_sql}'")
    op.execute(f"UPDATE proactivity_settings SET proactivity_trigger_prompt = '{proactivity_trigger_prompt_sql}'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('proactivity_settings', 'proactivity_trigger_prompt')
    op.drop_column('proactivity_settings', 'compression_prompt')
    op.drop_column('chat_sessions', 'last_proactivity_check_at')
