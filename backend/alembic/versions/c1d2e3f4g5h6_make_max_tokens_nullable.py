"""Make memory_max_tokens and trigger_max_tokens nullable

Revision ID: c1d2e3f4g5h6
Revises: d9296f4bc0b3
Create Date: 2026-02-06 22:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = '6c55f2882fb7'
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
    
    # Reset existing default values to NULL (for unlimited)
    op.execute("UPDATE proactivity_settings SET memory_max_tokens = NULL WHERE memory_max_tokens = 800")
    op.execute("UPDATE proactivity_settings SET trigger_max_tokens = NULL WHERE trigger_max_tokens = 500")
    op.execute("UPDATE chat_settings SET user_chat_max_tokens = NULL WHERE user_chat_max_tokens = 4096")


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
