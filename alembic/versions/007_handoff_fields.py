"""Add handoff fields: scheduled_at, notification timestamps, posted_url, lead_reminders_enabled

Revision ID: 007
Revises: 006
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New columns on posts
    op.add_column("posts", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("lead_notified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("posted_url", sa.Text(), nullable=True))

    # lead_reminders_enabled on users
    op.add_column(
        "users",
        sa.Column("lead_reminders_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Backfill scheduled_at from scheduled_date + scheduled_time (treating as UTC)
    op.execute(
        sa.text(
            "UPDATE posts SET scheduled_at = (scheduled_date::text || ' ' || COALESCE(scheduled_time, '09:00'))::timestamptz WHERE scheduled_at IS NULL"
        )
    )

    # Partial index for the reminder cron query
    op.create_index(
        "idx_posts_due",
        "posts",
        ["status", "scheduled_at"],
        postgresql_where=sa.text("status = 'scheduled'"),
    )


def downgrade() -> None:
    op.drop_index("idx_posts_due", table_name="posts")
    op.drop_column("users", "lead_reminders_enabled")
    op.drop_column("posts", "posted_url")
    op.drop_column("posts", "posted_at")
    op.drop_column("posts", "lead_notified_at")
    op.drop_column("posts", "notified_at")
    op.drop_column("posts", "scheduled_at")
