class UserRepository:
    def __init__(self):
        self._db: dict[int, dict] = {}
        self._next_id = 1

    def create(self, data: dict) -> dict:
        user = {"id": self._next_id, **data}
        self._db[self._next_id] = user
        self._next_id += 1
        return user

    def get(self, user_id: int) -> dict | None:
        return self._db.get(user_id)

    def get_by_email(self, email: str) -> dict | None:
        for user in self._db.values():
            if user["email"] == email:
                return user
        return None

    def get_all(self, skip: int = 0, limit: int = 10) -> list[dict]:
        users = list(self._db.values())
        return users[skip : skip + limit]

    def update(self, user_id: int, data: dict) -> dict | None:
        user = self._db.get(user_id)
        if user is None:
            return None
        user.update(data)
        return user

    def delete(self, user_id: int) -> bool:
        if user_id in self._db:
            del self._db[user_id]
            return True
        return False
