"""Блок: декларативная база SQLAlchemy — общий предок всех моделей.

Любая новая таблица наследуется от Base. Здесь же фиксируем naming convention,
чтобы Alembic генерировал предсказуемые имена индексов/констрейнтов (и миграции
корректно откатывались).
"""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Правила именования ограничений БД (%[...] раскрывает SQLAlchemy).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",        # индексы
    "uq": "uq_%(table_name)s_%(column_0_name)s",   # UNIQUE
    "ck": "ck_%(table_name)s_%(constraint_name)s", # CHECK
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # FOREIGN KEY
    "pk": "pk_%(table_name)s",            # PRIMARY KEY
}


class Base(DeclarativeBase):
    """Корневой класс всех ORM-моделей. Новые модели: `class Foo(Base): ...`."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
