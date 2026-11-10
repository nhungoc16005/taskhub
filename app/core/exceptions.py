from app.core import messages


class AppError(Exception):
    status_code = 500
    message = "Internal server error"

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
