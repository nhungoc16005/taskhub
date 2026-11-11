from app.core import messages


class AppError(Exception):
    status_code = 500
    message = "Internal server error"
    headers: dict[str, str] | None = None

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
    headers = {"WWW-Authenticate": "Bearer"}


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
