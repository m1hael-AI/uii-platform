"""Make memory_max_tokens and trigger_max_tokens nullable

Revision ID: c1d2e3f4g5h6
Revises: d9296f4bc0b3
Create Date: 2026-02-06 22:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'd9296f4bc0b3'
branch_labels = None
depends_on = None


def upgrade():
    # Make memory_max_tokens nullable
    op.alter_column('proactivity_settings', 'memory_max_tokens',
               existing_type=sa.INTEGER(),
               nullable=True)
    
    # Make trigger_max_tokens nullable
    op.alter_column('proactivity_settings', 'trigger_max_tokens',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade():
    # Revert memory_max_tokens to non-nullable (with default)
    op.alter_column('proactivity_settings', 'memory_max_tokens',
               existing_type=sa.INTEGER(),
               nullable=False,
               server_default='800')
    
    # Revert trigger_max_tokens to non-nullable (with default)
    op.alter_column('proactivity_settings', 'trigger_max_tokens',
               existing_type=sa.INTEGER(),
               nullable=False,
               server_default='500')
