"""add_news_settings_columns

Revision ID: f38290a1c2d3
Revises: e97f35g3c8e1
Create Date: 2026-02-18 10:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f38290a1c2d3'
down_revision: Union[str, Sequence[str], None] = 'e97f35g3c8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns
    op.add_column('news_settings', sa.Column('harvester_nightly_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('news_settings', sa.Column('harvester_search_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('news_settings', sa.Column('allowed_tags', sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # Populate with defaults (important for existing row)
    op.execute("""
        UPDATE news_settings 
        SET 
            harvester_nightly_prompt = 'Find top AI news for the last 24 hours. Focus on major releases, research, and industry shifts.',
            harvester_search_prompt = 'User is searching for: {query}.\\nWe ALREADY KNOW these news:\\n{context}\\n\\nFind NEW information, updates, or missed details. Do NOT repeat what we already know.',
            allowed_tags = 'AI, LLM, Robotics, Hardware, Startups, Policy, Science, Business, Generative AI, Computer Vision, NLP, MLOps, Data Science'
        WHERE id = 1
    """)


def downgrade() -> None:
    op.drop_column('news_settings', 'allowed_tags')
    op.drop_column('news_settings', 'harvester_search_prompt')
    op.drop_column('news_settings', 'harvester_nightly_prompt')
