"""add_type_and_landing_bullets

Revision ID: 6c673af2509e
Revises: 722f23e1b5a9
Create Date: 2026-02-12 14:02:52.552031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c673af2509e'
down_revision: Union[str, Sequence[str], None] = '722f23e1b5a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('webinar_schedules', sa.Column('type', sa.String(), nullable=False, server_default='webinar'))
    op.add_column('webinar_schedules', sa.Column('landing_bullets', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('webinar_schedules', 'landing_bullets')
    op.drop_column('webinar_schedules', 'type')
