"""Enforce idempotency and form-code uniqueness at the database boundary."""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fail loudly rather than silently deleting historical data if an existing
    # database contains duplicates that need an explicit operator decision.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM form_submissions
            WHERE client_id IS NOT NULL
            GROUP BY user_id, client_id
            HAVING COUNT(*) > 1
          ) THEN
            RAISE EXCEPTION 'duplicate (user_id, client_id) values exist; resolve before migration 005';
          END IF;
          IF EXISTS (
            SELECT 1 FROM form_submissions
            GROUP BY form_code
            HAVING COUNT(*) > 1
          ) THEN
            RAISE EXCEPTION 'duplicate form_code values exist; resolve before migration 005';
          END IF;
        END $$;
        """
    )
    op.create_index(
        "uq_form_submissions_user_client_id",
        "form_submissions",
        ["user_id", "client_id"],
        unique=True,
        postgresql_where="client_id IS NOT NULL",
    )
    op.create_index(
        "uq_form_submissions_form_code",
        "form_submissions",
        ["form_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_form_submissions_form_code", table_name="form_submissions")
    op.drop_index("uq_form_submissions_user_client_id", table_name="form_submissions")


assert revision and down_revision
