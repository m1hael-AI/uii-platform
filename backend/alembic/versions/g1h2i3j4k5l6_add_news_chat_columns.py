"""add_news_chat_columns

Revision ID: g1h2i3j4k5l6
Revises: f38290a1c2d3
Create Date: 2026-02-18 19:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'g1h2i3j4k5l6'
down_revision = 'f38290a1c2d3'
branch_labels = None
depends_on = None


def upgrade():
    # Add news_id column to chat_sessions
    op.add_column('chat_sessions', sa.Column('news_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_chat_sessions_news_id'), 'chat_sessions', ['news_id'], unique=False)
    op.create_foreign_key(None, 'chat_sessions', 'news_items', ['news_id'], ['id'])

    # Add news_chat_prompt column to news_settings
    op.add_column('news_settings', sa.Column('news_chat_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade():
    # Remove news_chat_prompt column from news_settings
    op.drop_column('news_settings', 'news_chat_prompt')

    # Remove news_id column from chat_sessions
    op.drop_constraint(None, 'chat_sessions', type_='foreignkey')
    op.drop_index(op.f('ix_chat_sessions_news_id'), table_name='chat_sessions')
    op.drop_column('chat_sessions', 'news_id')
