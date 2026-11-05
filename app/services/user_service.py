from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User
from app.core.security import hash_password


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def create_user(self, data: UserCreate) -> User:
        email = data.email.lower()
        if await self.repo.get_by_email(email):
            raise ValueError("Email already exists")

        user_data = data.model_dump(exclude={"password"})
        user_data["email"] = email
        user_data["hashed_password"] = hash_password(data.password)
        return await self.repo.create(user_data)

    async def get_user(self, user_id: int) -> User | None:
        return await self.repo.get(user_id)

    async def list_users(self, skip: int = 0, limit: int = 10):
        return await self.repo.get_all(skip=skip, limit=limit)

    async def update_user(self, user_id: int, data: UserUpdate) -> User | None:
        user = await self.repo.get(user_id)
        if not user:
            return None
        return await self.repo.update(user, data.model_dump(exclude_unset=True))

    async def delete_user(self, user_id: int) -> bool:
        user = await self.repo.get(user_id)
        if not user:
            return False
        await self.repo.delete(user)
        return True
