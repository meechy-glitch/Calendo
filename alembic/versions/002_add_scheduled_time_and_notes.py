"""Add scheduled_time and notes to posts

Revision ID: 002
Revises: 001
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("scheduled_time", sa.String(5), nullable=True))
    op.add_column("posts", sa.Column("notes", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("posts", "notes")
    op.drop_column("posts", "scheduled_time")
