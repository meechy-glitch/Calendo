"""Add nullable name column to users

Revision ID: 009
Revises: 008
Create Date: 2026-08-27 00:00:00.000000

Nullable by design: existing rows (the demo user and every account created
before this feature) have no name, and we deliberately do not backfill.

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "name")
