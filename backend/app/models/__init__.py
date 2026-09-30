"""Блок: реестр всех ORM-моделей.

ВАЖНО для Alembic: autogenerate видит таблицы ТОЛЬКО если модель импортирована здесь.
Новая модель => добавить строку импорта + имя в __all__.
"""
from app.database.base import Base
from app.models.user import User, UserRoleEnum

__all__ = ["Base", "User", "UserRoleEnum"]
