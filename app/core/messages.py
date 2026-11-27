USER_NOT_FOUND = "User not found"
INTERNAL_SERVER_ERROR = "Internal server error"
INVALID_DATABASE_URL = "DATABASE_URL must be a postgresql+asyncpg URL with host, database, username and password; sqlite+aiosqlite is allowed only in test"
INVALID_REDIS_URL = "REDIS_URL must use redis:// or rediss:// with a host, a valid port and an optional non-negative database index; query strings and fragments are not supported"
PRODUCTION_SECRET_WEAK = "SECRET_KEY in prod must be a randomly generated secret, not a sample or a repetitive value"
PRODUCTION_DB_ECHO = "DB_ECHO must be false in prod"
PRODUCTION_REDIS_REQUIRED = "REDIS_URL must be explicitly configured in prod"
CACHE_UNAVAILABLE = "Task cache unavailable during %s; using database"
CACHE_INVALID_PAYLOAD = "Invalid task cache payload; using database"
UNEXPECTED_ERROR = "Unhandled exception request_id=%s"
ASSIGNMENT_EMAIL_SUBJECT = "Task assigned to you"
EMAIL_DELIVERY_FAILED = "Assignment email failed for task_id=%s"
NAME_CANNOT_BE_NULL = "name cannot be null"
EMAIL_ALREADY_EXISTS = "Email already exists"
USER_IN_USE = "User still owns workspaces or tasks and cannot be deleted"

INVALID_CREDENTIALS = "Incorrect email or password"
COULD_NOT_VALIDATE = "Could not validate credentials"
INACTIVE_USER = "Inactive user"
INVALID_REFRESH_TOKEN = "Invalid refresh token"

CURRENT_PASSWORD_INCORRECT = "Current password is incorrect"
NEW_PASSWORD_SAME_AS_CURRENT = (
    "New password must be different from the current password"
)
PERMISSION_DENIED = "You do not have permission to perform this action"

TOKEN_EXPIRED = "Token has expired"
TOKEN_INVALID = "Invalid token"
TOKEN_WRONG_TYPE = "Wrong token type"


WORKSPACE_NOT_FOUND = "Workspace not found"
PROJECT_NOT_FOUND = "Project not found"
MEMBER_NOT_FOUND = "Member not found"
ALREADY_MEMBER = "User is already a member of this workspace"
CANNOT_REMOVE_OWNER = "The workspace owner cannot be removed or demoted"


TASK_NOT_FOUND = "Task not found"
LABEL_NOT_FOUND = "Label not found"
COMMENT_NOT_FOUND = "Comment not found"
ASSIGNEE_NOT_MEMBER = "Assignee must be a member of the workspace"
PROJECT_ARCHIVED = "Project is archived"
LABEL_ALREADY_ATTACHED = "Label is already attached to this task"
LABEL_NOT_ATTACHED = "Label is not attached to this task"

CANNOT_DEMOTE_OWNER = "The workspace owner cannot be demoted"

LABEL_NAME_CONFLICT = "A label with this name already exists in the project"
RESOURCE_CHANGED = "The task or label changed concurrently; reload and retry"
FIELD_NOT_NULLABLE = "this field cannot be null"
DUE_DATE_IN_PAST = "due_date cannot be in the past"
ACCESS_LOG = "request_id=%s method=%s path=%s status=%s duration_ms=%.2f"
ASSIGNMENT_EMAIL_LOG = "Assignment email user_id=%s task_id=%s"
APP_ENV_MISMATCH = "APP_ENV in the selected file must match the explicit environment"
PRODUCTION_DATABASE_PASSWORD = (
    "DATABASE_URL password in prod must not be a sample password"
)
