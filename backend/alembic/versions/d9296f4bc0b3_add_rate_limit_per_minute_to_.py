"""add rate_limit_per_minute to proactivity_settings

Revision ID: d9296f4bc0b3
Revises: b2c3d4e5f6a7
Create Date: 2026-02-06 15:44:39.127185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9296f4bc0b3'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('proactivity_settings', 
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, server_default='15')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('proactivity_settings', 'rate_limit_per_minute')
