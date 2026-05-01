"""create initial thread, message, and booking schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260501_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the initial application tables."""
    op.create_table(
        "threads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("prospect_email", sa.String(length=320), nullable=False),
        sa.Column("prospect_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_threads_prospect_email"), "threads", ["prospect_email"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("email_message_id", sa.String(length=255), nullable=True),
        sa.Column("intent", sa.String(length=64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_email_message_id"), "messages", ["email_message_id"], unique=False)
    op.create_index(op.f("ix_messages_thread_id"), "messages", ["thread_id"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("slot", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("cal_event_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bookings_thread_id"), "bookings", ["thread_id"], unique=False)


def downgrade() -> None:
    """Drop the initial application tables."""
    op.drop_index(op.f("ix_bookings_thread_id"), table_name="bookings")
    op.drop_table("bookings")
    op.drop_index(op.f("ix_messages_thread_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_email_message_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_threads_prospect_email"), table_name="threads")
    op.drop_table("threads")
