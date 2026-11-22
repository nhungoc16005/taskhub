"""Unique label names per project and explicit author deletion policy.

Revision ID: a24d5e9b0011
Revises: f2df42833566
"""
import sqlalchemy as sa

from alembic import op

revision = "a24d5e9b0011"
down_revision = "f2df42833566"
branch_labels = None
depends_on = None

NAMING = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}


def _check_sqlite_batch_mode() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite" and connection.exec_driver_sql("PRAGMA foreign_keys").scalar():
        raise RuntimeError("SQLite batch migration requires foreign_keys=OFF before the transaction; re-enable and check foreign keys after migration")


def _author_fk(table: str, column: str, ondelete: str | None) -> None:
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys(table)
    fk = next(item for item in foreign_keys if item["constrained_columns"] == [column])
    name = fk["name"] or f"fk_{table}_{column}_users"
    with op.batch_alter_table(table, naming_convention=NAMING) as batch:
        batch.drop_constraint(name, type_="foreignkey")
        batch.create_foreign_key(name, "users", [column], ["id"], ondelete=ondelete)


def upgrade() -> None:
    _check_sqlite_batch_mode()
    # Do not silently rename or delete existing user data to resolve duplicates.
    duplicate = op.get_bind().execute(sa.text(
        "SELECT project_id, name FROM labels GROUP BY project_id, name "
        "HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicate is not None:
        raise RuntimeError("Resolve duplicate label names within each project before upgrading")
    with op.batch_alter_table("labels") as batch:
        batch.create_unique_constraint("uq_labels_project_name", ["project_id", "name"])
    _author_fk("tasks", "created_by", "RESTRICT")
    _author_fk("comments", "author_id", "RESTRICT")


def downgrade() -> None:
    _check_sqlite_batch_mode()
    _author_fk("comments", "author_id", None)
    _author_fk("tasks", "created_by", None)
    with op.batch_alter_table("labels") as batch:
        batch.drop_constraint("uq_labels_project_name", type_="unique")
