import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


def load_revision():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/a24d5e9b0011_label_names_and_author_fks.py"
    spec = importlib.util.spec_from_file_location("day5_revision", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    return revision


def seed(connection):
    for statement in (
        "CREATE TABLE users (id INTEGER PRIMARY KEY)",
        "CREATE TABLE projects (id INTEGER PRIMARY KEY)",
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, created_by INTEGER NOT NULL REFERENCES users(id))",
        "CREATE TABLE comments (id INTEGER PRIMARY KEY, task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE, author_id INTEGER NOT NULL REFERENCES users(id))",
        "CREATE TABLE labels (id INTEGER PRIMARY KEY, project_id INTEGER REFERENCES projects(id), name VARCHAR(100) NOT NULL)",
        "INSERT INTO users VALUES (1)", "INSERT INTO projects VALUES (1)",
        "INSERT INTO tasks VALUES (1, 1)", "INSERT INTO comments VALUES (1, 1, 1)",
        "INSERT INTO labels VALUES (1, 1, 'Bug')",
    ):
        connection.execute(text(statement))


def test_migration_upgrade_downgrade_preserves_rows():
    engine = create_engine("sqlite://")
    revision = load_revision()
    with engine.begin() as connection:
        seed(connection)
        revision.op = Operations(MigrationContext.configure(connection))
        revision.upgrade()
        for table in ("tasks", "comments", "labels"):
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert inspect(connection).get_foreign_keys("tasks")[0]["options"]["ondelete"] == "RESTRICT"
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO labels VALUES (2, 1, 'Bug')"))
        revision.downgrade()
        connection.execute(text("INSERT INTO labels VALUES (2, 1, 'Bug')"))
        assert connection.execute(text("SELECT count(*) FROM comments")).scalar_one() == 1
    engine.dispose()


def test_migration_rejects_existing_duplicates_without_deleting_data():
    engine = create_engine("sqlite://")
    revision = load_revision()
    with engine.begin() as connection:
        seed(connection)
        connection.execute(text("INSERT INTO labels VALUES (2, 1, 'Bug')"))
        revision.op = Operations(MigrationContext.configure(connection))
        with pytest.raises(RuntimeError, match="duplicate label"):
            revision.upgrade()
        assert connection.execute(text("SELECT count(*) FROM labels")).scalar_one() == 2
    engine.dispose()
