"""add users auth

Revision ID: 0002_auth
Revises: 0001_initial
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_auth"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("google_id", sa.String(128), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=True),
    )
    op.create_index("ix_users_google_id", "users", ["google_id"])

    # ── sessions.owner_id ─────────────────────────────────────
    op.add_column("sessions", sa.Column(
        "owner_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.create_index("ix_sessions_owner_id", "sessions", ["owner_id"])

    # ── participants.user_id ──────────────────────────────────
    op.add_column("participants", sa.Column(
        "user_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.create_index("ix_participants_user_id", "participants", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_participants_user_id", table_name="participants")
    op.drop_column("participants", "user_id")
    op.drop_index("ix_sessions_owner_id", table_name="sessions")
    op.drop_column("sessions", "owner_id")
    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_table("users")
