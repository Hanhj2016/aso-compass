"""Add drug and trial enrichment fields.

Revision ID: 20261020_0002
Revises: 20261019_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20261020_0002"
down_revision = "20261019_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing = {column["name"] for column in inspector.get_columns("candidates")}
    columns = [
        sa.Column("n_drugs", sa.Integer(), nullable=True),
        sa.Column("drug_max_stage", sa.String(length=64), nullable=True),
        sa.Column("approved_drugs", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("oligo_drug", sa.String(length=64), nullable=True),
        sa.Column("oligo_names", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("aso_drug", sa.String(length=64), nullable=True),
        sa.Column("aso_names", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("aso_trial_n", sa.Integer(), nullable=True),
        sa.Column("aso_trial_weak", sa.Integer(), nullable=True),
        sa.Column("aso_trial_best", sa.String(length=128), nullable=True),
        sa.Column("aso_trial_ids", sa.String(length=500), nullable=False, server_default=""),
    ]
    for column in columns:
        if column.name not in existing:
            op.add_column("candidates", column)
    indexes = {index["name"] for index in inspector.get_indexes("evidence")}
    if "ix_evidence_run_source" not in indexes:
        op.create_index("ix_evidence_run_source", "evidence", ["run_id", "source"])


def downgrade() -> None:
    op.drop_index("ix_evidence_run_source", table_name="evidence")
    for name in (
        "aso_trial_ids",
        "aso_trial_best",
        "aso_trial_weak",
        "aso_trial_n",
        "aso_names",
        "aso_drug",
        "oligo_names",
        "oligo_drug",
        "approved_drugs",
        "drug_max_stage",
        "n_drugs",
    ):
        op.drop_column("candidates", name)
