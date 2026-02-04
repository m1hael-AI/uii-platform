"""fix tg_id bigint

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-04 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change tg_id from Integer to BigInteger to support 64-bit Telegram IDs
    # using postgresql_using to maintain data integrity if validation was needed, 
    # but strictly speaking mapping int -> bigint is safe.
    op.alter_column('users', 'tg_id',
               existing_type=sa.Integer(),
               type_=sa.BigInteger(),
               existing_nullable=True)


def downgrade() -> None:
    # Revert back to Integer
    op.alter_column('users', 'tg_id',
               existing_type=sa.BigInteger(),
               type_=sa.Integer(),
               existing_nullable=True)
