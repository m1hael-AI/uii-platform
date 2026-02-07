"""separate memory and proactivity prompts

Revision ID: 02401e2ae68d
Revises: beb5c93c3eae
Create Date: 2026-02-07 03:04:22.415991

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02401e2ae68d'
down_revision: Union[str, Sequence[str], None] = 'beb5c93c3eae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Update agent_memory_prompt (for regular agents)
    op.execute("""
        UPDATE proactivity_settings
        SET agent_memory_prompt = 'Ты — аналитик памяти агента.

КОНТЕКСТ:
- Текущая память агента: {current_memory}
- Глобальный профиль пользователя: {user_profile}
- Новые сообщения: {full_chat_history}

ЗАДАЧА:
Извлеки ТОЛЬКО новые факты о пользователе из диалога. Добавь их к текущей памяти.
Будь лаконичен. Только факты, без воды.

ФОРМАТ:
Верни ТОЛЬКО валидный JSON:
{{
  "memory_update": "Лаконичные факты о пользователе (2-3 предложения)"
}}'
    """)
    
    # Update assistant_memory_prompt (for Main Assistant)
    op.execute("""
        UPDATE proactivity_settings
        SET assistant_memory_prompt = 'Ты — аналитик памяти AI Помощника.

КОНТЕКСТ:
- Глобальный профиль пользователя: {user_profile}
- Память других агентов: {all_agent_memories}
- Текущая память помощника: {current_memory}
- Новые сообщения: {full_chat_history}

ЗАДАЧА:
1. Обнови память помощника новыми фактами
2. Обнови глобальный профиль пользователя (синтез всех агентов)

ФОРМАТ:
Верни ТОЛЬКО валидный JSON:
{{
  "memory_update": "Память помощника (2-3 предложения)",
  "global_profile_update": "Глобальный профиль (3-5 предложений)"
}}'
    """)
    
    # Update proactivity_trigger_prompt (for all agents)
    op.execute("""
        UPDATE proactivity_settings
        SET proactivity_trigger_prompt = 'Ты — аналитик проактивности.

КОНТЕКСТ:
- Глобальный профиль пользователя: {user_profile}
- Память агента о диалоге: {agent_memory}
- История диалога: {full_chat_history}
- Время молчания: {silence_hours} часов

ЗАДАЧА:
Реши, стоит ли написать пользователю проактивно.

КРИТЕРИИ ДЛЯ СОЗДАНИЯ ЗАДАЧИ:
✅ Есть незавершённая тема или вопрос
✅ Агент может реально помочь
✅ Прошло достаточно времени (не навязчиво)

❌ НЕ ПИШИ, ЕСЛИ:
- Диалог завершён естественно
- Пользователь явно попрощался
- Нет конкретной темы для обсуждения

ФОРМАТ:
Верни ТОЛЬКО валидный JSON:
{{
  "create_task": true,
  "topic": "Конкретная тема для сообщения (1 предложение)"
}}

Если НЕ нужно писать:
{{
  "create_task": false,
  "topic": ""
}}'
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to old combined prompts (optional, can leave empty)
    pass
