"""Store PDF bytes in DB instead of S3.

When no S3/R2 storage is configured, the worker can persist the
generated PDF directly in the reports row.  The API serves it via an
authenticated GET /reports/{id}/pdf endpoint.
"""

from alembic import op
import sqlalchemy as sa

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("pdf_bytes", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "pdf_bytes")
