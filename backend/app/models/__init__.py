# Реестр всех моделей. Alembic видит таблицы только если модель импортирована здесь.
from app.database.base import Base
from app.models.user import User, UserRoleEnum

__all__ = ["Base", "User", "UserRoleEnum"]
