"""add rag chunks

Revision ID: 833f24f2b6b0
Revises: 722f23e1b5a9
Create Date: 2026-02-12 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '833f24f2b6b0'
down_revision: Union[str, None] = '6c673af2509e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable Vector Extension using raw SQL
    # We use op.execute because standard SA doesn't have "create extension"
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Create webinar_chunks table
    op.create_table('webinar_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('webinar_id', sa.Integer(), nullable=False),
    sa.Column('content', sa.VARCHAR(), nullable=False),
    # Using Vector type from pgvector
    sa.Column('embedding', Vector(1536), nullable=True),
    sa.Column('chunk_metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['webinar_id'], ['webinar_libraries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # 3. Create HNSW index for fast cosine search
    # This requires special syntax. 
    # op.create_index doesn't easily support 'postgresql_using' with operator classes in standard alembic < 1.13 sometimes,
    # but we can try generic method or raw sql.
    # Raw SQL is safest for vector indexes.
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_webinar_chunks_embedding 
        ON webinar_chunks 
        USING hnsw (embedding vector_cosine_ops)
    """)
    
    op.create_index(op.f('ix_webinar_chunks_webinar_id'), 'webinar_chunks', ['webinar_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_webinar_chunks_webinar_id'), table_name='webinar_chunks')
    op.execute("DROP INDEX IF EXISTS ix_webinar_chunks_embedding")
    op.drop_table('webinar_chunks')
    # We usually don't drop the extension in downgrade as other tables might use it, 
    # but for strict reversibility:
    # op.execute("DROP EXTENSION IF EXISTS vector") 
