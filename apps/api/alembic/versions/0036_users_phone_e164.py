"""Capture user's WhatsApp number at signup.

The admin upgrade-requests queue used to fall back to email because we
had no other contact method on file.  Indonesian SMB pilots prefer
WhatsApp over email, so we add ``users.phone_e164`` (E.164 format,
including leading "+") at signup time.  Optional: existing users get
NULL and the admin UI falls back to email.

No index — we don't query by phone, only display it.

Revision ID: 0036
Revises: 0035
Create Date: 2026-06-17
"""

import sqlalchemy as sa

from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("phone_e164", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "phone_e164")
