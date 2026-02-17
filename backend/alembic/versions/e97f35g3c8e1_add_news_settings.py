"""add_news_settings

Revision ID: e97f35g3c8e1
Revises: d86d05bb73d7
Create Date: 2026-02-18 01:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e97f35g3c8e1'
down_revision: Union[str, Sequence[str], None] = 'd86d05bb73d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('news_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('harvester_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('writer_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('harvester_enabled', sa.Boolean(), nullable=False),
    sa.Column('harvester_cron', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('generator_enabled', sa.Boolean(), nullable=False),
    sa.Column('generator_cron', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('dedup_threshold', sa.Float(), nullable=False),
    sa.Column('generator_batch_size', sa.Integer(), nullable=False),
    sa.Column('generator_delay', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default settings
    op.execute("""
        INSERT INTO news_settings (
            id, harvester_prompt, writer_prompt,
            harvester_enabled, harvester_cron,
            generator_enabled, generator_cron,
            dedup_threshold, generator_batch_size, generator_delay,
            updated_at
        ) VALUES (
            1,
            'You are a news aggregator AI. Find the most important and recent AI/ML news.',
            'You are a professional tech writer. Create a comprehensive article about the given news.',
            true, '0 2 * * *',
            true, '*/15 * * * *',
            0.84, 5, 2,
            NOW()
        )
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('news_settings')
