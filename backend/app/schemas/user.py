"""Блок: Pydantic-схемы пользователя — контракты «вход/выход» API.

Модели SQLAlchemy описывают, КАК данные лежат в БД; схемы здесь описывают,
КАКИЕ поля принимает и отдаёт HTTP-API. Разделение позволяет, например,
принять пароль (UserCreate) и никогда его не отдать (UserResponse).
Новые поля сущности = добавить в модель + сюда (+ Alembic-миграция).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRoleEnum


class UserBase(BaseModel):
    """Общие поля всех пользовательских схем (наследуемся от неё ниже)."""

    # min_length/max_length и pattern — валидация на лету: кривой логин не дойдёт до БД.
    username: str = Field(
        min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$",
        description="Логин: буквы, цифры, _ . -",
    )


class UserCreate(UserBase):
    """Тело запроса регистрации: логин + пароль (пароль принимаем, но не отдаём)."""

    password: str = Field(min_length=6, max_length=128, description="Минимум 6 символов")


class UserUpdate(UserBase):
    """Тело PATCH /users/me: всё опционально — обновляем только присланные поля."""

    # Переопределяем username из UserBase как optional (PATCH = частичное обновление).
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    # Отображаемое имя (необязательное) — то, что фронт показывает в шапке после входа.
    display_name: str | None = Field(default=None, max_length=100)


class UserRoleUpdate(BaseModel):
    """Админский PATCH /users/{id}/role: одна роль из enum. Валидируется автоматически."""

    role: UserRoleEnum


class UserResponse(UserBase):
    """Что фронт видит про пользователя. Поля password_hash тут НЕТ намеренно."""

    # from_attributes=True: можно делать UserResponse.model_validate(user_orm_obj).
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRoleEnum
    created_at: datetime
    # Отображаемое имя (может быть null — фронт тогда показывает username).
    display_name: str | None = None


class Token(BaseModel):
    """Ответ логина/регистрации: JWT + тип заголовка для клиента (Bearer <token>)."""

    access_token: str
    token_type: str = "bearer"


class UserPage(BaseModel):
    """Страница списка пользователей для админки (пагинация)."""

    items: list[UserResponse]   # юзеры текущей страницы
    total: int                  # всего записей без учёта фильтра/страницы
