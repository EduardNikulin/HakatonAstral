"""Блок: UserRepository — ЕДИНСТВЕННОЕ место, где пишутся SQL-запросы к таблице users.

Правило архитектуры: сервисы и ручки НЕ трогают select()/insert() — только методы
репозитория. Это позволяет менять схему запросов, не трогая бизнес-логику, и легко
подменять хранилище (например, на фейковое в тестах).
"""
import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRoleEnum


class UserRepository:
    """Обёртка над сессией БД со всеми операциями чтения/записи пользователей."""

    def __init__(self, session: AsyncSession):
        """Сессию передаёт слой deps.py (зависимость get_db) — на каждый запрос своя."""
        self.session = session

    async def create(self, user: User) -> User:
        """Вставляет объект-модель и возвращает его же (со значениями по умолчанию БД).

        commit делает get_db после успешного ответа ручки; при исключении — rollback.
        """
        self.session.add(user)
        await self.session.flush()  # отправляет INSERT, чтобы проставились defaults
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Ищет по первичному ключу. Возвращает None, если пользователя нет."""
        return await self.session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        """Поиск по уникальному логину — используется при регистрации и входе."""
        stmt = select(User).where(User.username == username)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_users(
        self,
        offset: int = 0,
        limit: int = 20,
        role: UserRoleEnum | None = None,
    ) -> tuple[Sequence[User], int]:
        """Страница юзеров + общее количество (для пагинации в админке).

        Args:
            offset/limit: окно выборки (смещение и размер страницы).
            role: необязательный фильтр по роли.

        Returns:
            (кортеж юзеров страницы, total — сколько всего подходит под фильтр).
        """
        stmt = select(User).order_by(User.created_at.desc())
        count_stmt = select(func.count()).select_from(User)
        if role is not None:  # добавляем WHERE к обоим запросам только если фильтр задан
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)

        users = (await self.session.execute(stmt.offset(offset).limit(limit))).scalars().all()
        total = (await self.session.execute(count_stmt)).scalar_one()
        return users, total

    async def update(self, user: User) -> User:
        """Явная запись изменений объекта в БД (flush без ожидания коммита)."""
        await self.session.flush()
        return user

    async def delete(self, user: User) -> None:
        """Удаляет строку пользователя (коммит произойдёт в get_db)."""
        await self.session.delete(user)
        await self.session.flush()
