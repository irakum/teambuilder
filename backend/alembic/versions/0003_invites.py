"""add invites table

Revision ID: 0003_invites
Revises: 0002_auth
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_invites"
down_revision = "0002_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_invites_code", "invites", ["code"])
    op.create_index("ix_invites_session_id", "invites", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_invites_code", table_name="invites")
    op.drop_index("ix_invites_session_id", table_name="invites")
    op.drop_table("invites")
