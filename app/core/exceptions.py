from typing import ClassVar

from app.core import messages


class AppError(Exception):
    status_code = 500
    message = messages.INTERNAL_SERVER_ERROR
    headers: ClassVar[dict[str, str] | None] = None

    def __init__(self, message: str | None = None):
        self.message = message or self.message
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404


class UserNotFoundError(NotFoundError):
    message = messages.USER_NOT_FOUND


class EmailAlreadyExistsError(AppError):
    status_code = 409
    message = messages.EMAIL_ALREADY_EXISTS


class UserInUseError(AppError):
    status_code = 409
    message = messages.USER_IN_USE


class UnauthorizedError(AppError):
    status_code = 401
    headers: ClassVar[dict[str, str] | None] = {"WWW-Authenticate": "Bearer"}


class InvalidCredentialsError(UnauthorizedError):
    message = messages.INVALID_CREDENTIALS


class InvalidTokenError(UnauthorizedError):
    message = messages.INVALID_REFRESH_TOKEN


class InactiveUserError(AppError):
    status_code = 403
    message = messages.INACTIVE_USER


class ForbiddenError(AppError):
    status_code = 403
    message = messages.PERMISSION_DENIED


class InvalidPasswordError(AppError):
    status_code = 400
    message = messages.CURRENT_PASSWORD_INCORRECT


class WorkspaceNotFoundError(NotFoundError):
    message = messages.WORKSPACE_NOT_FOUND


class ProjectNotFoundError(NotFoundError):
    message = messages.PROJECT_NOT_FOUND


class MemberNotFoundError(NotFoundError):
    message = messages.MEMBER_NOT_FOUND


class AlreadyMemberError(AppError):
    status_code = 409
    message = messages.ALREADY_MEMBER


class CannotRemoveOwnerError(AppError):
    status_code = 400
    message = messages.CANNOT_REMOVE_OWNER


class TaskNotFoundError(NotFoundError):
    message = messages.TASK_NOT_FOUND


class LabelNotFoundError(NotFoundError):
    message = messages.LABEL_NOT_FOUND


class CommentNotFoundError(NotFoundError):
    message = messages.COMMENT_NOT_FOUND


class AssigneeNotMemberError(AppError):
    status_code = 400
    message = messages.ASSIGNEE_NOT_MEMBER


class ProjectArchivedError(AppError):
    status_code = 409
    message = messages.PROJECT_ARCHIVED


class LabelAlreadyAttachedError(AppError):
    status_code = 409
    message = messages.LABEL_ALREADY_ATTACHED


class LabelNotAttachedError(NotFoundError):
    message = messages.LABEL_NOT_ATTACHED


class CannotDemoteOwnerError(AppError):
    status_code = 400
    message = messages.CANNOT_DEMOTE_OWNER


class LabelNameConflictError(AppError):
    status_code = 409
    message = messages.LABEL_NAME_CONFLICT


class ResourceChangedError(AppError):
    status_code = 409
    message = messages.RESOURCE_CHANGED
