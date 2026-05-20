"""add session_organizers table

Revision ID: 0005_session_organizers
Revises: 0004_participant_email
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_session_organizers"
down_revision = "0004_participant_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_organizers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="co-organizer"),
    )
    op.create_index("ix_session_organizers_session_id", "session_organizers", ["session_id"])
    op.create_index("ix_session_organizers_user_id", "session_organizers", ["user_id"])
    op.create_unique_constraint(
        "uq_session_organizers_session_user",
        "session_organizers",
        ["session_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_session_organizers_session_user", "session_organizers")
    op.drop_index("ix_session_organizers_user_id", table_name="session_organizers")
    op.drop_index("ix_session_organizers_session_id", table_name="session_organizers")
    op.drop_table("session_organizers")
