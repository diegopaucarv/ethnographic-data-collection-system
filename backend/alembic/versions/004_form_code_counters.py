"""Enforce concurrent, per-form-type code generation."""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "form_code_counters",
        sa.Column("form_type", sa.VARCHAR(10), primary_key=True),
        sa.Column("next_number", sa.INTEGER, nullable=False),
        sa.CheckConstraint("next_number > 0", name="ck_form_code_counters_next_number"),
    )
    op.execute("""
        INSERT INTO form_code_counters (form_type, next_number)
        SELECT form_type, COALESCE(MAX(CAST(SUBSTRING(form_code FROM LENGTH(form_type) + 2) AS INTEGER)), 0) + 1
        FROM form_submissions
        GROUP BY form_type
    """)


def downgrade() -> None:
    op.drop_table("form_code_counters")


def _noop() -> None:
    return None

assert _noop is not None
assert sa is not None
