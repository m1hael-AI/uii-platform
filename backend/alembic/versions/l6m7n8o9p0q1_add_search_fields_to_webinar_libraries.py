"""add_search_fields_to_webinar_libraries

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-02-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l6m7n8o9p0q1'
down_revision: Union[str, Sequence[str], None] = 'k5l6m7n8o9p0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add short_description and search_embedding to webinar_libraries."""
    # Enable pgvector extension (safe — idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    op.add_column(
        'webinar_libraries',
        sa.Column('short_description', sa.Text(), nullable=True)
    )
    op.add_column(
        'webinar_libraries',
        sa.Column('search_embedding', sa.Text(), nullable=True)  # Will be cast to vector type via raw SQL below
    )
    
    # Drop the placeholder text column and recreate as vector type
    op.drop_column('webinar_libraries', 'search_embedding')
    op.execute(
        "ALTER TABLE webinar_libraries ADD COLUMN search_embedding vector(1536)"
    )
    
    # Create HNSW index for fast cosine similarity search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_webinar_libraries_search_embedding "
        "ON webinar_libraries USING hnsw (search_embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Remove search fields from webinar_libraries."""
    op.execute("DROP INDEX IF EXISTS ix_webinar_libraries_search_embedding")
    op.drop_column('webinar_libraries', 'search_embedding')
    op.drop_column('webinar_libraries', 'short_description')
