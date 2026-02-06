"""merge max_tokens and rename migrations

Revision ID: 3c717262ed69
Revises: c1d2e3f4g5h6, f9e8d7c6b5a4
Create Date: 2026-02-07 02:44:57.315098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c717262ed69'
down_revision: Union[str, Sequence[str], None] = ('c1d2e3f4g5h6', 'f9e8d7c6b5a4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
