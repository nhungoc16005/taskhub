class InvalidCredentialsError(Exception):
    """Sai email hoặc mật khẩu."""


class InactiveUserError(Exception):
    """Tài khoản đã bị vô hiệu hoá."""


class InvalidTokenError(Exception):
    """Refresh token sai, hết hạn hoặc đã bị thu hồi."""
