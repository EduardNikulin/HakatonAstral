# Модель пользователя. Роли — enum, чтобы БД и API не принимали мусорные значения.
# Новые поля пользователя добавляем сюда + в UserBase/UserResponse в schemas/user.py.
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserRoleEnum(str, enum.Enum):
    """Роли пользователей. Наследуемся от str — удобно сравнивать с строками из JWT."""
    ADMIN = "admin"      # полный доступ, управление ролями и пользователями
    AUTHOR = "author"    # создатель контента/игр
    PLAYER = "player"    # обычный пользователь (роль по умолчанию при регистрации)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRoleEnum] = mapped_column(
        Enum(UserRoleEnum, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UserRoleEnum.PLAYER,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:  # удобно для логов и отладки
        return f"<User {self.username} ({self.role.value})>"
