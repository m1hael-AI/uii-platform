"""add_image_url_to_news_items

Revision ID: i3j4k5l6m7n8
Revises: h2k3l4m5n6o7
Create Date: 2026-02-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i3j4k5l6m7n8'
down_revision: Union[str, Sequence[str], None] = 'h2k3l4m5n6o7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add image_url column to news_items."""
    op.add_column('news_items', sa.Column('image_url', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove image_url column from news_items."""
    op.drop_column('news_items', 'image_url')
