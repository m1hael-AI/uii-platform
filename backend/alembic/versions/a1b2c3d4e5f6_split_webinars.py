"""split webinars

Revision ID: a1b2c3d4e5f6
Revises: 994bd1bb6705
Create Date: 2026-02-04 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '994bd1bb6705'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop constraints and indexes on old columns
    # Note: Constraint names usually follow a pattern or are auto-generated. 
    # PostgreSQL often names them table_column_fkey.
    # If explicit names were not given in initial_schema, we rely on naming conventions or we might need to reflect.
    # But since we are upgrading from a fresh DB state (mostly), we can try standard names.
    # However, create_table in initial_schema didn't name them explicitly.
    # Alembic's drop_constraint usually needs the name.
    
    # Since we know the user wiped the DB, strictly speaking we are upgrading an empty DB (after initial_schema).
    # We can try to guess the constraint name. 
    # 'chat_sessions_webinar_id_fkey' is standard for Postgres.
    
    op.drop_constraint('chat_sessions_webinar_id_fkey', 'chat_sessions', type_='foreignkey')
    op.drop_index(op.f('ix_chat_sessions_webinar_id'), table_name='chat_sessions')
    op.drop_column('chat_sessions', 'webinar_id')

    op.drop_constraint('webinar_signups_webinar_id_fkey', 'webinar_signups', type_='foreignkey')
    op.drop_index(op.f('ix_webinar_signups_webinar_id'), table_name='webinar_signups')
    op.drop_column('webinar_signups', 'webinar_id')

    # Drop old table
    op.drop_table('webinars')

    # 2. Create 'webinar_schedules'
    op.create_table('webinar_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('connection_link', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('thumbnail_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('speaker_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('reminder_1h_sent', sa.Boolean(), nullable=False),
        sa.Column('reminder_15m_sent', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create 'webinar_libraries'
    op.create_table('webinar_libraries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('video_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('thumbnail_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('speaker_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('transcript_context', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False),
        sa.Column('conducted_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Add columns to 'chat_sessions'
    op.add_column('chat_sessions', sa.Column('schedule_id', sa.Integer(), nullable=True))
    op.add_column('chat_sessions', sa.Column('library_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_chat_sessions_schedule_id'), 'chat_sessions', ['schedule_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_library_id'), 'chat_sessions', ['library_id'], unique=False)
    op.create_foreign_key(None, 'chat_sessions', 'webinar_schedules', ['schedule_id'], ['id'])
    op.create_foreign_key(None, 'chat_sessions', 'webinar_libraries', ['library_id'], ['id'])

    # 5. Add columns to 'webinar_signups'
    op.add_column('webinar_signups', sa.Column('schedule_id', sa.Integer(), nullable=False))
    op.create_index(op.f('ix_webinar_signups_schedule_id'), 'webinar_signups', ['schedule_id'], unique=False)
    op.create_foreign_key(None, 'webinar_signups', 'webinar_schedules', ['schedule_id'], ['id'])


def downgrade() -> None:
    # Downgrade logic (simplified reversal)
    op.drop_constraint(None, 'webinar_signups', type_='foreignkey')
    op.drop_index(op.f('ix_webinar_signups_schedule_id'), table_name='webinar_signups')
    op.drop_column('webinar_signups', 'schedule_id')
    
    op.drop_constraint(None, 'chat_sessions', type_='foreignkey')
    op.drop_constraint(None, 'chat_sessions', type_='foreignkey')
    op.drop_index(op.f('ix_chat_sessions_library_id'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_schedule_id'), table_name='chat_sessions')
    op.drop_column('chat_sessions', 'library_id')
    op.drop_column('chat_sessions', 'schedule_id')

    op.drop_table('webinar_libraries')
    op.drop_table('webinar_schedules')

    op.create_table('webinars',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('video_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('connection_link', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('thumbnail_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('speaker_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('transcript_context', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_upcoming', sa.Boolean(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('reminder_1h_sent', sa.Boolean(), nullable=False),
        sa.Column('reminder_15m_sent', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.add_column('webinar_signups', sa.Column('webinar_id', sa.Integer(), nullable=False))
    op.create_index(op.f('ix_webinar_signups_webinar_id'), 'webinar_signups', ['webinar_id'], unique=False)
    op.create_foreign_key('webinar_signups_webinar_id_fkey', 'webinar_signups', 'webinars', ['webinar_id'], ['id'])
    
    op.add_column('chat_sessions', sa.Column('webinar_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_chat_sessions_webinar_id'), 'chat_sessions', ['webinar_id'], unique=False)
    op.create_foreign_key('chat_sessions_webinar_id_fkey', 'chat_sessions', 'webinars', ['webinar_id'], ['id'])
