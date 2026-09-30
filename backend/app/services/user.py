"""Блок: UserService — бизнес-правила работы с пользователями.

Здесь живут ВСЕ правила («нельзя дубликат логина», «админ не может удалить себя»...).
Слой не знает про HTTP: вместо ошибок FastAPI бросает исключения из core/exceptions.py,
а к БД обращается ТОЛЬКО через репозиторий. Ручки становятся тонкими перешлюшками.
Новые фичи хакатона (правила рейтинга, модерация и т.п.) добавляем в этот слой.
"""
import uuid

from app.core.exceptions import AlreadyExistsError, InvalidCredentialsError, NotFoundError, PermissionDeniedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRoleEnum
from app.repositories.user import UserRepository
from app.schemas.user import Token, UserCreate, UserPage, UserResponse, UserUpdate


class UserService:
    """Сервис пользователей. Зависимости (репозиторий) внедряет deps.py."""

    def __init__(self, repo: UserRepository):
        self.repo = repo

    # ---------- Регистрация / вход -------------------------------------------

    async def register(self, data: UserCreate) -> tuple[User, Token]:
        """Создаёт пользователя с ролью player и сразу выдаёт JWT.

        Raises:
            AlreadyExistsError (409): логин уже занят.
        """
        if await self.repo.get_by_username(data.username):   # проверяем уникальность ДО вставки
            raise AlreadyExistsError("Логин", data.username)
        user = User(
            username=data.username,
            password_hash=hash_password(data.password),      # открытый пароль не сохраняется
            role=UserRoleEnum.PLAYER,                        # новая регистрация — всегда игрок;
                                                             # повышение роли возможно только админом
        )
        user = await self.repo.create(user)
        return user, self._make_token(user)

    async def authenticate(self, username: str, password: str) -> Token:
        """Проверяет логин/пароль и возвращает токен для /auth/login.

        Raises:
            InvalidCredentialsError (401): юзера нет ИЛИ пароль не совпал
            (сообщение одинаковое — чтобы нельзя было «сканировать» существующие логины).
        """
        user = await self.repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        return self._make_token(user)

    @staticmethod
    def _make_token(user: User) -> Token:
        """Собирает JWT: sub=id пользователя, плюс роль — для быстрых проверок на клиенте."""
        access = create_access_token(user.id, {"role": user.role.value})
        return Token(access_token=access)

    # ---------- Чтение ----------------------------------------------------------

    async def get_or_404(self, user_id: uuid.UUID) -> User:
        """Универсальная «взять или упасть с 404» — используется остальными методами."""
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Пользователь", user_id)
        return user

    async def list_users(self, page: int, per_page: int, role: UserRoleEnum | None) -> UserPage:
        """Страница пользователей для админки: page=1..N, фильтр по роли опционален."""
        users, total = await self.repo.list_users(offset=(page - 1) * per_page, limit=per_page, role=role)
        return UserPage(items=[UserResponse.model_validate(u) for u in users], total=total)

    # ---------- Изменение -------------------------------------------------------

    async def update_self(self, current: User, data: UserUpdate) -> User:
        """PATCH /users/me: пользователь меняет СВОИ username/пароль.

        Raises:
            AlreadyExistsError: новый логин занят кем-то другим.
        """
        if data.username and data.username != current.username:
            if await self.repo.get_by_username(data.username):
                raise AlreadyExistsError("Логин", data.username)
            current.username = data.username
        # display_name: обновляем только если поле реально пришло в PATCH-запросе.
        # "model_fields_set" — набор полей, которые клиент явно прислал (в отличие
        # от просто None по умолчанию). Позволяет отличить «не трогать» от «очистить».
        if "display_name" in data.model_fields_set:
            current.display_name = data.display_name
        if data.password:                     # пароль меняем только если прислали новый
            current.password_hash = hash_password(data.password)
        return await self.repo.update(current)

    async def change_role(self, actor: User, target_id: uuid.UUID, new_role: UserRoleEnum) -> User:
        """Назначение роли (ручка доступна только админу — проверка в deps).

        Правило безопасности: админ не может сам себя понизить — иначе можно
        случайно остаться без единого администратора системы.
        """
        if actor.id == target_id and new_role != UserRoleEnum.ADMIN:
            raise PermissionDeniedError("Админ не может снять роль с самого себя")
        target = await self.get_or_404(target_id)
        target.role = new_role
        return await self.repo.update(target)

    # ---------- Удаление --------------------------------------------------------

    async def delete_user(self, actor: User, target_id: uuid.UUID) -> None:
        """Удаление пользователя админом (или игроком себя через /users/me).

        Args:
            actor: кто инициирует удаление (текущий юзер из токена).
            target_id: кого удаляем.

        Raises:
            PermissionDeniedError: админа нельзя удалить совсем (нужен живой админ);
                                   самоснятие доступно через другой путь — см. change_role.
            NotFoundError: target_id не существует.
        """
        if actor.id == target_id and actor.role == UserRoleEnum.ADMIN:
            raise PermissionDeniedError("Админ не может удалить сам себя")
        target = await self.get_or_404(target_id)
        if target.role == UserRoleEnum.ADMIN:
            raise PermissionDeniedError("Нельзя удалить администратора")
        await self.repo.delete(target)

    async def ensure_admin_exists(self) -> None:
        """Вызывается lifespan-ом при старте: создаёт админа из .env, если его ещё нет.

        Идемпотентна: повторные запуски ничего не ломают.
        """
        from app.core.config import settings  # локальный импорт, чтобы не тянуть настройки в модуль

        if not await self.repo.get_by_username(settings.ADMIN_USERNAME):
            await self.repo.create(
                User(
                    username=settings.ADMIN_USERNAME,
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    role=UserRoleEnum.ADMIN,
                )
            )
