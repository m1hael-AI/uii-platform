"""separate_llm_settings_for_memory_and_trigger

Revision ID: 6c55f2882fb7
Revises: e1fefa6d0703
Create Date: 2026-02-06 20:45:29.440699

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c55f2882fb7'
down_revision: Union[str, Sequence[str], None] = 'e1fefa6d0703'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Separate LLM settings into Memory and Trigger configurations."""
    # Rename existing columns to memory_* prefix
    op.alter_column('proactivity_settings', 'model', new_column_name='memory_model')
    op.alter_column('proactivity_settings', 'temperature', new_column_name='memory_temperature')
    op.alter_column('proactivity_settings', 'max_tokens', new_column_name='memory_max_tokens')
    
    # Add new trigger_* columns
    op.add_column('proactivity_settings', sa.Column('trigger_model', sa.String(), nullable=False, server_default='gpt-4.1-mini'))
    op.add_column('proactivity_settings', sa.Column('trigger_temperature', sa.Float(), nullable=False, server_default='0.7'))
    op.add_column('proactivity_settings', sa.Column('trigger_max_tokens', sa.Integer(), nullable=False, server_default='500'))


def downgrade() -> None:
    """Downgrade schema: Revert to single LLM settings."""
    # Remove trigger_* columns
    op.drop_column('proactivity_settings', 'trigger_max_tokens')
    op.drop_column('proactivity_settings', 'trigger_temperature')
    op.drop_column('proactivity_settings', 'trigger_model')
    
    # Rename memory_* columns back to original names
    op.alter_column('proactivity_settings', 'memory_max_tokens', new_column_name='max_tokens')
    op.alter_column('proactivity_settings', 'memory_temperature', new_column_name='temperature')
    op.alter_column('proactivity_settings', 'memory_model', new_column_name='model')

