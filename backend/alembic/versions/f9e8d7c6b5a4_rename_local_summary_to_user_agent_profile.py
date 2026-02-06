"""rename_local_summary_to_user_agent_profile

Revision ID: f9e8d7c6b5a4
Revises: b012c504ef6d
Create Date: 2026-02-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9e8d7c6b5a4'
down_revision: Union[str, Sequence[str], None] = 'b012c504ef6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename column local_summary to user_agent_profile
    op.alter_column('chat_sessions', 'local_summary', new_column_name='user_agent_profile')


def downgrade() -> None:
    # Rename back
    op.alter_column('chat_sessions', 'user_agent_profile', new_column_name='local_summary')
