"""Deny direct browser-role access with row level security.

Revision ID: 20261020_0003
Revises: 20261020_0002
"""

from alembic import op

revision = "20261020_0003"
down_revision = "20261020_0002"
branch_labels = None
depends_on = None

TABLES = (
    "runs",
    "candidates",
    "evidence",
    "run_events",
    "export_artifacts",
    "ai_insights",
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in reversed(TABLES):
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
