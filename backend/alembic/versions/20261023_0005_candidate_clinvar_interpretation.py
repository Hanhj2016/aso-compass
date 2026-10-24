"""Add bounded ClinVar interpretation metadata to candidates.

Revision ID: 20261023_0005
Revises: 20261022_0004
"""

import json

import sqlalchemy as sa

from alembic import op

revision = "20261023_0005"
down_revision = "20261022_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("candidates")}
    if "clinvar_interpretation" in columns:
        return
    empty = json.dumps({})
    with op.batch_alter_table("candidates") as batch:
        batch.add_column(
            sa.Column(
                "clinvar_interpretation",
                sa.JSON(),
                nullable=False,
                server_default=sa.text(f"'{empty}'"),
            )
        )


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("candidates")}
    if "clinvar_interpretation" in columns:
        with op.batch_alter_table("candidates") as batch:
            batch.drop_column("clinvar_interpretation")
