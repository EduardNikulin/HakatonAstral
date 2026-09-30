"""Блок: зависимости FastAPI (DI) — склейка HTTP-слоя с сервисами и защитой.

Здесь собираются цепочки db -> repository -> service, а также проверки авторизации
и ролей. Ручки описывают требования через Depends(...) и получают уже готовые
объекты — им не нужно знать, откуда что берётся.

Новая сущность = добавить пару get_xxx_repo/get_xxx_service по образцу ниже.
"""
import uuid
from typing import Annotated, Callable, Coroutine

from fastapi import Depends, Header
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentialsError, PermissionDeniedError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User, UserRoleEnum
from app.repositories.user import UserRepository
from app.services.user import UserService

# --- Цепочка сборки пользователей ------------------------------------------------


def get_user_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    """Создаёт репозиторий поверх текущей сессии БД."""
    return UserRepository(session)


def get_user_service(repo: Annotated[UserRepository, Depends(get_user_repo)]) -> UserService:
    """Создаёт сервис поверх репозитория — именно его просят ручки."""
    return UserService(repo)


# Типы-алиасы: в сигнатурах ручек пишем коротко, а разворачивается полная цепочка.
UserServiceDep = Annotated[UserService, Depends(get_user_service)]

# --- Авторизация по JWT -----------------------------------------------------------


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    service: UserServiceDep = None,  # реальное значение подставит FastAPI через Depends
) -> User:
    """Достаёт пользователя из заголовка `Authorization: Bearer <token>`.

    ГЛАВНАЯ зависимость для защищённых ручек: если вернула User — запрос
    аутентифицирован; иначе бросит 401 и тело ручки вообще не выполнится.

    Raises:
        InvalidCredentialsError (401): заголовка нет / он кривой / токен истёк или
        подделан / пользователь с таким id удалён из БД.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise InvalidCredentialsError("Ожидается заголовок Authorization: Bearer <token>")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)          # проверка подписи и срока годности
    except JWTError as exc:
        raise InvalidCredentialsError("Токен недействителен или истёк") from exc

    user_id = payload.get("sub")                      # sub = id юзера, который зашил токен
    try:
        user = await service.get_or_404(uuid.UUID(user_id))  # + проверка, что юзер ещё жив в БД
    except Exception as exc:
        # сюда попадают NotFoundError (юзер удалён) и ValueError (sub — не UUID)
        raise InvalidCredentialsError("Пользователь не найден") from exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]  # алиас для сигнатур ручек

# --- Проверка ролей ----------------------------------------------------------------


def require_roles(*roles: UserRoleEnum) -> Callable[..., Coroutine[None, None, User]]:
    """Фабрика зависимостей: разрешает доступ только перечисленным ролям.

    Использование в ручке:
        @router.get(..., dependencies=[Depends(require_roles(UserRoleEnum.ADMIN))])
    Возвращает готовую функцию-зависимость — комбинации ролей настраиваются
    на месте, без правок этого файла.
    """

    async def checker(user: CurrentUser) -> User:
        """Сверяет роль текущего юзера со списком допущенных."""
        if user.role not in roles:
            raise PermissionDeniedError(f"Требуется роль: {', '.join(r.value for r in roles)}")
        return user

    return checker


# Готовая частая проверка: RequireAdmin = Annotated[User, Depends(require_admin)].
require_admin = require_roles(UserRoleEnum.ADMIN)
RequireAdmin = Annotated[User, Depends(require_admin)]
