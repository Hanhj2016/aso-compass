"""Initial Phase 1 persistence schema.

Revision ID: 20261019_0001
Revises: None
"""

from sqlmodel import SQLModel

from alembic import op
from app.models import AIInsight, Candidate, Evidence, ExportArtifact, Run, RunEvent  # noqa: F401

revision = "20261019_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    SQLModel.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    SQLModel.metadata.drop_all(bind=op.get_bind())
