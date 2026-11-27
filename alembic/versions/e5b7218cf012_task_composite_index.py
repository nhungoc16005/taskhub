"""Index filtered task pages, including their stable id ordering.

Revision ID: e5b7218cf012
Revises: a24d5e9b0011
"""

from alembic import op

revision = "e5b7218cf012"
down_revision = "a24d5e9b0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_tasks_project_status_priority_id",
        "tasks",
        ["project_id", "status", "priority", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_project_status_priority_id", table_name="tasks")
