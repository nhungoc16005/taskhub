from app.core.exceptions import EmailAlreadyExistsError, UserNotFoundError
from app.core.security import hash_password

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def create_user(self, data: UserCreate) -> dict:
        email = data.email.lower()
        if self.repo.get_by_email(email):
            raise EmailAlreadyExistsError()
        user_data = data.model_dump(exclude={"password"})
        user_data["email"] = email
        user_data["hashed_password"] = hash_password(data.password)
        return self.repo.create(user_data)

    def get_user(self, user_id: int) -> dict:
        user = self.repo.get(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    def list_users(self, skip: int, limit: int) -> dict:
        return {
            "items": self.repo.get_all(skip=skip, limit=limit),
            "total": self.repo.count(),
            "skip": skip,
            "limit": limit,
        }

    def update_user(self, user_id: int, data: UserUpdate) -> dict:
        self.get_user(user_id)  # raise 404 nếu không có
        return self.repo.update(user_id, data.model_dump(exclude_unset=True))

    def delete_user(self, user_id: int) -> None:
        self.get_user(user_id)
        self.repo.delete(user_id)
