"""fix memory_update_interval and proactivity_timeout to float

Revision ID: beb5c93c3eae
Revises: 3c717262ed69
Create Date: 2026-02-07 02:50:06.239033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'beb5c93c3eae'
down_revision: Union[str, Sequence[str], None] = '3c717262ed69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change memory_update_interval from INTEGER to FLOAT
    op.alter_column('proactivity_settings', 'memory_update_interval',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=False)
    
    # Change proactivity_timeout from INTEGER to FLOAT
    op.alter_column('proactivity_settings', 'proactivity_timeout',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert proactivity_timeout to INTEGER
    op.alter_column('proactivity_settings', 'proactivity_timeout',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    
    # Revert memory_update_interval to INTEGER
    op.alter_column('proactivity_settings', 'memory_update_interval',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=False)
