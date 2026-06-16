"""Add password_hash to users so coaches who don't want to deal with magic
links / Google sign-in have a password option.

Nullable: existing users keep working unchanged.  Setting a password is an
opt-in step from /settings → "Set password".

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-14
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_hash")
