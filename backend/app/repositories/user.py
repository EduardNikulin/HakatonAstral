# Слой доступа к данным (Repository).
# Здесь живут ВСЕ запросы к таблице users. Ручки и сервисы не пишут select-запросы сами —
# они вызывают методы репозитория. Так при смене БД или добавлении полей меняется только этот файл.
import uuid
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRoleEnum


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Чтение ----------
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return await self.db.get(User, user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_all(
        self, role: Optional[UserRoleEnum] = None, offset: int = 0, limit: int = 50
    ) -> Sequence[User]:
        query = select(User)
        if role is not None:
            query = query.where(User.role == role)
        query = query.order_by(User.created_at).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count(self, role: Optional[UserRoleEnum] = None) -> int:
        query = select(func.count(User.id))
        if role is not None:
            query = query.where(User.role == role)
        result = await self.db.execute(query)
        return int(result.scalar_one())

    # ---------- Запись ----------
    async def create(self, username: str, password_hash: str, role: UserRoleEnum) -> User:
        user = User(username=username, password_hash=password_hash, role=role)
        self.db.add(user)
        await self.db.flush()  # генерирует id/created_at, не закрывая транзакцию
        return user

    async def update(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        await self.db.flush()
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()
