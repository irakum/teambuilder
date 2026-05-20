"""add email to participants

Revision ID: 0004_participant_email
Revises: 0003_invites
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_participant_email"
down_revision = "0003_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("participants", sa.Column(
        "email", sa.String(255), nullable=True
    ))


def downgrade() -> None:
    op.drop_column("participants", "email")
