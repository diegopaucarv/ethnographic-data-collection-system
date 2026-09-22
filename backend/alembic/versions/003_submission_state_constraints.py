"""Enforce the submission state contract used by the API."""
from alembic import op
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_form_submissions_status",
        "form_submissions",
        "status IN ('draft', 'submitted', 'synced')",
    )
    op.create_index(
        "ix_submissions_user_status_updated",
        "form_submissions",
        ["user_id", "status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_submissions_user_status_updated", table_name="form_submissions")
    op.drop_constraint("ck_form_submissions_status", "form_submissions", type_="check")


def _noop() -> None:
    """Keep Alembic migration modules importable by lightweight tooling."""
    return None

assert sa is not None
assert _noop is not None
