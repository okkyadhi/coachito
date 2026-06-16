"""Extensions, UUID helper, and sports table.

Revision ID: 0001
Revises:
Create Date: 2026-05-11
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # pg_uuidv7 for time-sortable UUIDs.  postgres:16-alpine doesn't ship it,
    # so install the shim unconditionally; override with the real extension on
    # managed Postgres (Neon, etc.) by running a separate one-time migration.
    op.execute("""
        CREATE OR REPLACE FUNCTION uuid_generate_v7()
        RETURNS UUID LANGUAGE SQL AS $$
            SELECT gen_random_uuid()
        $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sports (
            id            UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            code          VARCHAR(20) UNIQUE NOT NULL,
            name_en       VARCHAR(50) NOT NULL,
            name_id       VARCHAR(50) NOT NULL,
            is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
            display_order INTEGER     NOT NULL DEFAULT 0,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_sports_code ON sports (code)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sports")
    op.execute("DROP FUNCTION IF EXISTS uuid_generate_v7()")
