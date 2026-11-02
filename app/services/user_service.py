from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def create_user(self, data: UserCreate) -> dict:
        if self.repo.get_by_email(data.email):
            raise ValueError("Email already exists")
        user_data = data.model_dump(exclude={"password"})
        user_data["hashed_password"] = data.password
        return self.repo.create(user_data)

    def get_user(self, user_id: int) -> dict | None:
        return self.repo.get(user_id)

    def list_users(self, skip: int = 0, limit: int = 10) -> list[dict]:
        return self.repo.get_all(skip=skip, limit=limit)

    def update_user(self, user_id: int, data: UserUpdate) -> dict | None:
        changes = data.model_dump(exclude_unset=True)
        return self.repo.update(user_id, changes)

    def delete_user(self, user_id: int) -> bool:
        return self.repo.delete(user_id)
