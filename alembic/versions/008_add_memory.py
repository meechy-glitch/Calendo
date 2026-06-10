"""Add memory table for cross-session AI assistant memory

Revision ID: 008
Revises: 007
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="assistant"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_id", "memory", ["id"], unique=False)
    op.create_index("ix_memory_user_id", "memory", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_memory_user_id", table_name="memory")
    op.drop_index("ix_memory_id", table_name="memory")
    op.drop_table("memory")
