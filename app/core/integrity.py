from sqlalchemy.exc import IntegrityError


def is_unique_violation(error: IntegrityError, constraint: str, sqlite_columns: str) -> bool:
    """Distinguish the expected unique conflict from FK/other integrity failures."""
    original = error.orig
    cause = getattr(original, "__cause__", None)
    sqlstate = getattr(original, "sqlstate", None) or getattr(cause, "sqlstate", None)
    name = getattr(original, "constraint_name", None) or getattr(cause, "constraint_name", None)
    if sqlstate == "23505":
        return name == constraint or constraint in str(original)
    return f"UNIQUE constraint failed: {sqlite_columns}" in str(original)
