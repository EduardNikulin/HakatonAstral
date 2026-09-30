"""Блок: ORM-модель пользователя (таблица `users`).

Новые поля пользователя добавляем СЮДА (+ продублировать в UserBase/UserResponse
в schemas/user.py, затем alembic revision --autogenerate).
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserRoleEnum(str, enum.Enum):
    """Роли пользователей. Наследуемся от str — значения удобно сравнивать со строками из JWT."""

    ADMIN = "admin"     # полный доступ: управление ролями и пользователями
    AUTHOR = "author"   # создатель контента/игр
    PLAYER = "player"   # обычный пользователь (роль по умолчанию при регистрации)


class User(Base):
    """Пользователь системы: логин, хэш пароля, роль, дата создания."""

    __tablename__ = "users"

    # UUID первичный ключ — генерируется на стороне Python до вставки в БД.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    # Уникальный логин для входа; index=True ускоряет поиск при авторизации.
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    # Только bcrypt-хэш! Открытый пароль нигде не храним и никому не отдаём.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Роль как enum в БД: мусорное значение невозможно записать ни из API, ни руками.
    role: Mapped[UserRoleEnum] = mapped_column(
        Enum(UserRoleEnum, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UserRoleEnum.PLAYER,
    )
    # Время создания в UTC с таймзоной (timezone=True — чтобы Postgres хранил timestamptz).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Красивое отображение в логах/отладке вместо <User object at 0x...>."""
        return f"<User {self.username} ({self.role.value})>"
