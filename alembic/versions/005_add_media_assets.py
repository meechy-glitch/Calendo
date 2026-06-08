"""Add media_asset table and posts.media_asset_id

Revision ID: 005
Revises: 004
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_asset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False, server_default="r2"),
        sa.Column("public_url", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_asset_id"), "media_asset", ["id"], unique=False)

    op.add_column(
        "posts",
        sa.Column("media_asset_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_posts_media_asset_id",
        "posts",
        "media_asset",
        ["media_asset_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_posts_media_asset_id", "posts", type_="foreignkey")
    op.drop_column("posts", "media_asset_id")
    op.drop_index(op.f("ix_media_asset_id"), table_name="media_asset")
    op.drop_table("media_asset")
