# Pydantic-схемы пользователей. Слои схем:
#   UserBase      — общие поля (добавляй новые поля сюда)
#   UserCreate    — входные данные регистрации
#   UserUpdate    — входные данные редактирования профиля (все поля опциональны)
#   UserResponse  — то, что отдаём фронтенду (пароль никогда не возвращаем!)
#   UserPage      — пагинация списка пользователей для админки
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRoleEnum


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Уникальное имя пользователя")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="Пароль в открытом виде")


class UserLogin(BaseModel):
    """Вариант входа через JSON (альтернатива OAuth2 form-data)."""
    username: str = Field(..., description="Имя пользователя")
    password: str = Field(..., description="Пароль")


class UserUpdate(BaseModel):
    """Редактирование своего профиля. Только безопасные поля — роль здесь отсутствует."""
    username: str | None = Field(None, min_length=3, max_length=50)


class UserRoleUpdate(BaseModel):
    """Назначается ТОЛЬКО админом через PATCH /users/{id}/role."""
    role: UserRoleEnum = Field(..., description="Новая роль: admin / author / player")


class UserResponse(UserBase):
    id: uuid.UUID = Field(..., description="Уникальный ID пользователя")
    role: UserRoleEnum = Field(..., description="Роль пользователя в системе")
    created_at: datetime = Field(..., description="Дата регистрации")

    # Позволяет Pydantic v2 читать данные из SQLAlchemy-моделей напрямую.
    model_config = ConfigDict(from_attributes=True)


class UserPage(BaseModel):
    """Страница списка пользователей (для админки)."""
    items: list[UserResponse]
    total: int
    offset: int
    limit: int


class Token(BaseModel):
    access_token: str = Field(..., description="JWT-токен доступа")
    token_type: str = Field("bearer", description="Тип токена (всегда bearer)")
