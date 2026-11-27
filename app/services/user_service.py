from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    EmailAlreadyExistsError,
    UserInUseError,
    UserNotFoundError,
)
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page, Pagination
from app.schemas.user import UserCreate, UserUpdate
from app.services.updates import update_from_schema


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def create_user(self, data: UserCreate) -> User:
        email = data.email.lower()
        if await self.repo.get_by_email(email):
            raise EmailAlreadyExistsError()

        user_data = data.model_dump(exclude={"password"})
        user_data["email"] = email
        user_data["hashed_password"] = hash_password(data.password)
        try:
            return await self.repo.create(user_data)
        except IntegrityError:
            # 2 request đăng ký cùng lúc: request sau vi phạm UNIQUE(email)
            raise EmailAlreadyExistsError() from None

    async def get_user(self, user_id: int) -> User:
        user = await self.repo.get(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    async def list_users(self, pagination: Pagination) -> Page[User]:
        return pagination.page(
            items=await self.repo.get_all(skip=pagination.skip, limit=pagination.limit),
            total=await self.repo.count(),
        )

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        user = await self.get_user(user_id)
        return await update_from_schema(self.repo, user, data)

    async def delete_user(self, user_id: int) -> None:
        user = await self.get_user(user_id)
        try:
            await self.repo.delete(user)
        except IntegrityError:
            # user còn workspace/task tham chiếu tới -> vi phạm FK
            raise UserInUseError() from None
