"""add_suggested_questions_to_agents

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-02-21 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j4k5l6m7n8o9'
down_revision: Union[str, Sequence[str], None] = 'i3j4k5l6m7n8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add suggested_questions column to agents table."""
    op.add_column('agents', sa.Column('suggested_questions', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove suggested_questions column from agents table."""
    op.drop_column('agents', 'suggested_questions')
