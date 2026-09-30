# Сервисный слой — бизнес-логика пользователей без FastAPI и HTTP.
# Ручки тонкие: валидация через схемы -> вызов сервиса -> отдача ответа.
# Новая логика (например, «смена пароля», «бан пользователя») добавляется сюда.
import uuid

from app.core.exceptions import UsernameAlreadyExistsError, UserNotFoundError
from app.core.security import hash_password
from app.models.user import User, UserRoleEnum
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserRoleUpdate, UserUpdate


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    # ---------- Чтение ----------
    async def get_user(self, user_id: uuid.UUID) -> User:
        """Всегда бросает 404, если пользователя нет — ручкам не нужно это проверять."""
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        return user

    async def list_users(self, role: UserRoleEnum | None, offset: int, limit: int) -> tuple[list[User], int]:
        users = await self.repo.list_all(role=role, offset=offset, limit=limit)
        total = await self.repo.count(role=role)
        return list(users), total

    # ---------- Создание ----------
    async def register(self, data: UserCreate) -> User:
        """Регистрация нового пользователя. Роль всегда player (админа назначает только админ)."""
        existing = await self.repo.get_by_username(data.username)
        if existing is not None:
            raise UsernameAlreadyExistsError()
        return await self.repo.create(
            username=data.username,
            password_hash=hash_password(data.password),
            role=UserRoleEnum.PLAYER,
        )

    async def ensure_admin_exists(self, username: str, password: str) -> bool:
        """Создаёт администратора, если его ещё нет. Возвращает True, если создал."""
        existing = await self.repo.get_by_username(username)
        if existing is not None:
            return False
        await self.repo.create(
            username=username,
            password_hash=hash_password(password),
            role=UserRoleEnum.ADMIN,
        )
        return True

    # ---------- Обновление ----------
    async def update_profile(self, user: User, data: UserUpdate) -> User:
        """Редактирование своего профиля пользователем (роль менять нельзя)."""
        updates = data.model_dump(exclude_unset=True)
        if "username" in updates and updates["username"] != user.username:
            taken = await self.repo.get_by_username(updates["username"])
            if taken is not None:
                raise UsernameAlreadyExistsError()
        return await self.repo.update(user, **updates)

    async def change_role(self, target: User, data: UserRoleUpdate, actor: User) -> User:
        """Назначение роли. Вызывается только от имени админа (проверка прав — в deps/route)."""
        if target.id == actor.id and data.role != UserRoleEnum.ADMIN:
            # защита: админ не может сам себя понизить и потерять доступ к управлению
            raise ValueError("Админ не может снять с себя роль администратора")
        return await self.repo.update(target, role=data.role)

    # ---------- Удаление ----------
    async def delete_user(self, user: User) -> None:
        await self.repo.delete(user)
