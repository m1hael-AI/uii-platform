"""seed_proactivity_settings

Revision ID: 20260208_seed
Revises: b012c504ef6d
Create Date: 2026-02-08 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '20260208_seed'
down_revision: Union[str, None] = 'b012c504ef6d' # Assuming this is the latest one from user logs
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Insert default settings if table is empty
    # We use raw SQL to avoid model dependency issues during migration
    op.execute("""
        INSERT INTO proactivity_settings (
            enabled,
            memory_update_interval,
            proactivity_timeout,
            check_interval,
            max_messages_per_day_agents,
            max_messages_per_day_assistant,
            summarizer_check_interval,
            summarizer_idle_threshold,
            context_soft_limit,
            context_threshold,
            context_compression_keep_last,
            rate_limit_per_minute,
            cron_expression,
            quiet_hours_start,
            quiet_hours_end,
            updated_at
        )
        SELECT 
            true,  -- enabled
            2.0,   -- memory_update_interval (hours)
            24.0,  -- proactivity_timeout (hours)
            2,     -- check_interval (minutes)
            3,     -- max_messages_per_day_agents
            3,     -- max_messages_per_day_assistant
            2,     -- summarizer_check_interval
            5,     -- summarizer_idle_threshold
            350000, -- context_soft_limit
            0.9,    -- context_threshold
            20,     -- context_compression_keep_last
            15,     -- rate_limit_per_minute
            '0 */2 * * *', -- cron_expression
            '22:00', -- quiet_hours_start
            '10:00', -- quiet_hours_end
            NOW()
        WHERE NOT EXISTS (SELECT 1 FROM proactivity_settings);
    """)


def downgrade() -> None:
    # We don't delete settings on downgrade usually, but for completeness:
    # op.execute("DELETE FROM proactivity_settings;")
    pass
