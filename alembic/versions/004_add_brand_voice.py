"""Add brand_voice table

Revision ID: 004
Revises: 003
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brand_voice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tone", sa.String(200), nullable=True),
        sa.Column("dos", sa.String(1000), nullable=True),
        sa.Column("donts", sa.String(1000), nullable=True),
        sa.Column("sample_posts", sa.String(2000), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_brand_voice_id"), "brand_voice", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_brand_voice_id"), table_name="brand_voice")
    op.drop_table("brand_voice")
