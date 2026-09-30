"""Блок: ручки авторизации — /api/v1/auth/*.

Тонкий слой: разобрать запрос -> вызвать сервис -> отдать ответ. Никакой логики и SQL.
Эти ручки публичные (кроме /me), их видит Swagger на http://localhost:8000/docs.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm  # ждёт form-data: username + password

from app.api.v1.deps import CurrentUser, UserServiceDep
from app.schemas.user import Token, UserCreate, UserResponse

# Префикс и тег задаём здесь; api.py подключит роутер под /api/v1 одним include_router.
router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    "/register",
    response_model=UserResponse,               # наружу уйдёт только безопасный профиль
    status_code=status.HTTP_201_CREATED,       # 201 — корректный код «создан ресурс»
    summary="Регистрация нового игрока",
)
async def register(data: UserCreate, service: UserServiceDep) -> UserResponse:
    """Создаёт пользователя (роль всегда player) и возвращает его профиль.

    Дубликат логина -> 409 (правило живёт в UserService, не здесь).
    """
    user, _token = await service.register(data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Вход: выдаёт JWT",
)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: UserServiceDep,
) -> Token:
    """Проверяет учётные данные и отдаёт access_token.

    Фронт кладёт его в заголовок: Authorization: Bearer <access_token>.
    Неверные данные -> 401. Форма (а не JSON) — стандарт OAuth2, совместимый
    с кнопкой Authorize в Swagger UI.
    """
    return await service.authenticate(form.username, form.password)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Текущий пользователь по токену",
)
async def me(current: CurrentUser) -> UserResponse:
    """Возвращает профиль владельца токена.

    Нужна фронту для двух вещей: проверка живости сессии при загрузке страницы
    и получение роли (role в ответе) — по ней ветвим UI админки/игрока.
    Без токена или с битым токеном зависимость get_current_user сама отдаст 401.
    """
    return UserResponse.model_validate(current)
