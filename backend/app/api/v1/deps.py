# Зависимости FastAPI (dependencies): БД, репозитории, сервисы, текущий пользователь, права.
# Новый слой для новой сущности = одна функция-зависимость здесь + роутер в api.py.
import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import InvalidCredentialsError, NotAuthenticatedError, PermissionDeniedError, UserNotFoundError
from app.database.session import get_db
from app.models.user import User, UserRoleEnum
from app.repositories.user import UserRepository
from app.services.user import UserService

# "auto_error=False" — чтобы ошибку 401 формировать сами (с русским detail из exceptions.py)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ---------- Инъекция слоёв (DI) ----------
def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_user_service(repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(repo)


# ---------- Аутентификация (кто ты?) ----------
async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    service: UserService = Depends(get_user_service),
) -> User:
    """Достаёт пользователя из БД по JWT-токену. Бросает 401 при проблемах с токеном."""
    if not token:
        raise NotAuthenticatedError()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise InvalidCredentialsError()
    except JWTError:
        raise InvalidCredentialsError()
    try:
        return await service.get_user(uuid.UUID(user_id))
    except ValueError:  # sub не является UUID
        raise InvalidCredentialsError()


# ---------- Авторизация (что тебе разрешено?) ----------
def require_roles(*roles: UserRoleEnum):
    """Фабрика зависимостей: пустить только пользователей с указанными ролями.

    Примеры использования в ручках:
       Depends(require_roles(UserRoleEnum.ADMIN))                 # только админ
        current_user=Depends(require_roles(UserRoleEnum.ADMIN, UserRoleEnum.AUTHOR))
    """
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise PermissionDeniedError(
                f"Требуется роль: {', '.join(r.value for r in roles)}"
            )
        return current_user
    return dependency


require_admin = require_roles(UserRoleEnum.ADMIN)  # готовая шпаргалка: Depends(require_admin)
