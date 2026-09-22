"""Add client identity for idempotent offline sync."""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("form_submissions", sa.Column("client_id", sa.VARCHAR(128), nullable=True))
    op.create_index(
        "ux_submissions_user_client_id",
        "form_submissions",
        ["user_id", "client_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_submissions_user_client_id", table_name="form_submissions")
    op.drop_column("form_submissions", "client_id")
