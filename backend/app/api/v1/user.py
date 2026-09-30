"""Блок: CRUD-ручки пользователей — /api/v1/users/*.

Матрица доступа (одна таблица — удобно и фронту, и при ревью прав):
    GET    /users            список+пагинация      только admin
    GET    /users/{id}       карточка юзера        только admin
    PATCH  /users/me         своё имя/пароль       любой авторизованный
    DELETE /users/me         удалить себя          авторизованный (кроме admin)
    PATCH  /users/{id}/role  назначение роли       только admin  <-- ключевая фича
    DELETE /users/{id}       удаление юзера        только admin

Все правила («что можно и почему») живут в UserService; здесь только Depends-охрана.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.v1.deps import CurrentUser, RequireAdmin, UserServiceDep
from app.models.user import UserRoleEnum
from app.schemas.user import UserRoleUpdate, UserPage, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get(
    "",
    response_model=UserPage,
    summary="Список пользователей (админ)",
)
async def list_users(
    service: UserServiceDep,
    _admin: RequireAdmin,               # префикс _ — зависимостью пользуемся, значение не нужно
    page: Annotated[int, Query(ge=1, description="Страница, начиная с 1")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Размер страницы")] = 20,
    role: Annotated[UserRoleEnum | None, Query(description="Фильтр по роли")] = None,
) -> UserPage:
    """Отдаёт страницу юзеров + total. Query-валидация (ge/le) не даст прислать page=-5."""
    return await service.list_users(page=page, per_page=per_page, role=role)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Карточка пользователя по id (админ)",
)
async def get_user(
    user_id: uuid.UUID,                 # FastAPI сам проверит валидность UUID (иначе 422)
    service: UserServiceDep,
    _admin: RequireAdmin,
) -> UserResponse:
    """Только чтение: несуществующий id -> 404 (бросает сервис)."""
    user = await service.get_or_404(user_id)
    return UserResponse.model_validate(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Изменить свои логин/пароль",
)
async def update_me(data: UserUpdate, current: CurrentUser, service: UserServiceDep) -> UserResponse:
    """PATCH с частичным обновлением: пришлите только username ИЛИ только password.

    Работает через «свой» объект из токена — чужого юзера так не изменить.
    """
    user = await service.update_self(current, data)
    return UserResponse.model_validate(user)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить свой аккаунт",
)
async def delete_me(current: CurrentUser, service: UserServiceDep) -> None:
    """Самоудаление игрока/автора. Админ удалять себя НЕ может (защита от потери админки)."""
    await service.delete_user(actor=current, target_id=current.id)


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Назначить роль (только админ)",
)
async def change_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    admin: RequireAdmin,                # вся ручка под охраной роли admin
    service: UserServiceDep,
) -> UserResponse:
    """Ключевой админский эндпоинт: player <-> author <-> admin.

    Тело запроса: {"role": "author"}. Несуществующий юзер -> 404; попытка снять
    роль с самого себя -> 403 (правило в UserService.change_role).
    """
    user = await service.change_role(actor=admin, target_id=user_id, new_role=data.role)
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя (админ)",
)
async def delete_user(user_id: uuid.UUID, admin: RequireAdmin, service: UserServiceDep) -> None:
    """Админ удаляет любого НЕ-админа; другого админа удалить нельзя (403)."""
    await service.delete_user(actor=admin, target_id=user_id)
