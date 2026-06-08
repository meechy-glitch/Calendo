"""Add video support and post_media junction table

Revision ID: 006
Revises: 005
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend media_asset with video metadata columns
    op.add_column("media_asset", sa.Column("duration_seconds", sa.Float(), nullable=True))
    op.add_column("media_asset", sa.Column("thumbnail_key", sa.Text(), nullable=True))

    # 2. Create post_media junction table
    op.create_table(
        "post_media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("media_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["media_asset.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "position", name="uq_post_media_position"),
    )
    op.create_index("ix_post_media_post_id", "post_media", ["post_id"])

    # 3. Data migration: copy existing post→media relationship into junction table
    op.execute(
        """
        INSERT INTO post_media (post_id, media_id, position)
        SELECT id, media_asset_id, 0
        FROM posts
        WHERE media_asset_id IS NOT NULL
        """
    )

    # 4. Drop the legacy single-media FK and column from posts
    op.drop_constraint("fk_posts_media_asset_id", "posts", type_="foreignkey")
    op.drop_column("posts", "media_asset_id")


def downgrade() -> None:
    # Restore the single media_asset_id column on posts
    op.add_column("posts", sa.Column("media_asset_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_posts_media_asset_id", "posts", "media_asset", ["media_asset_id"], ["id"]
    )
    # Restore first media item (position=0) back to posts.media_asset_id
    op.execute(
        """
        UPDATE posts
        SET media_asset_id = pm.media_id
        FROM post_media pm
        WHERE posts.id = pm.post_id AND pm.position = 0
        """
    )
    # Drop junction table
    op.drop_index("ix_post_media_post_id", table_name="post_media")
    op.drop_table("post_media")
    # Remove video columns
    op.drop_column("media_asset", "thumbnail_key")
    op.drop_column("media_asset", "duration_seconds")
