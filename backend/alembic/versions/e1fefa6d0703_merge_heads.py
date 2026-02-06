"""merge_heads

Revision ID: e1fefa6d0703
Revises: b012c504ef6d, d036b646f0c3
Create Date: 2026-02-06 20:45:16.170020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1fefa6d0703'
down_revision: Union[str, Sequence[str], None] = ('b012c504ef6d', 'd036b646f0c3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
