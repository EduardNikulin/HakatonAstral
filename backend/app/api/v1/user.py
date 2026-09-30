# CRUD пользователей.
#   GET    /users            — список (только админ)
#   GET    /users/{id}       — карточка пользователя (только админ)
#   PATCH  /users/me         — редактирование своего профиля (любой авторизованный)
#   DELETE /users/me         — удаление своего аккаунта (любой авторизованный)
#   PATCH  /users/{id}/role  — НАЗНАЧЕНИЕ РОЛИ (только админ)
#   DELETE /users/{id}       — удаление пользователя (только админ)
import uuid

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.v1.deps import get_current_user, get_user_service, require_admin
from app.core.exceptions import PermissionDeniedError
from app.models.user import User, UserRoleEnum
from app.schemas.user import UserPage, UserRoleUpdate, UserResponse, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserPage)
async def list_users(
    role: UserRoleEnum | None = Query(None, description="Фильтр по роли"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: UserService = Depends(get_user_service),
    _admin: User = Depends(require_admin),
):
    """Список всех пользователей с пагинацией и фильтром по роли. Доступ: admin."""
    users, total = await service.list_users(role=role, offset=offset, limit=limit)
    return {"items": users, "total": total, "offset": offset, "limit": limit}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
    _admin: User = Depends(require_admin),
):
    """Карточка пользователя по ID. Доступ: admin."""
    return await service.get_user(user_id)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
):
    """Изменить свой профиль (сменить имя). Роль через эту ручку менять нельзя."""
    return await service.update_profile(current_user, data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
):
    """Удалить свой аккаунт. Админ не может удалить сам себя (защита от потери доступа)."""
    if current_user.role == UserRoleEnum.ADMIN:
        raise PermissionDeniedError("Админ не может удалить собственный аккаунт")
    await service.delete_user(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{user_id}/role", response_model=UserResponse)
async def change_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    service: UserService = Depends(get_user_service),
    admin: User = Depends(require_admin),
):
    """Назначение роли пользователю (admin/author/player). Доступ: только admin."""
    target = await service.get_user(user_id)
    try:
        return await service.change_role(target=target, data=data, actor=admin)
    except ValueError as e:
        raise PermissionDeniedError(str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
    admin: User = Depends(require_admin),
):
    """Удаление любого пользователя. Доступ: только admin."""
    target = await service.get_user(user_id)
    if target.id == admin.id:
        raise PermissionDeniedError("Нельзя удалить самого себя")
    await service.delete_user(target)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
