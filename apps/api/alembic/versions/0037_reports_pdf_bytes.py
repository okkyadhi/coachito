"""Store PDF bytes in DB instead of S3.

When no S3/R2 storage is configured, the worker can persist the
generated PDF directly in the reports row.  The API serves it via an
authenticated GET /reports/{id}/pdf endpoint.
"""

from alembic import op
import sqlalchemy as sa

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS pdf_bytes BYTEA"))


def downgrade() -> None:
    op.drop_column("reports", "pdf_bytes")
