"""Блок: подключение к БД и управление сессиями (async SQLAlchemy 2.0).

Здесь создаются engine (пул соединений) и sessionmaker. Ручки/сервисы получают
сессию через зависимость get_db() — сами никогда не открывают соединения.
Для тестов есть патч-точка: можно подменить get_db на SQLite-версию.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Engine: одно «ядро» на приложение. echo=False — не логируем каждый SQL (для дебага
# можно включить). pool_pre_ping проверит живость соединения перед выдачей.
engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

# Фабрика сессий: expire_on_commit=False — объекты остаются читаемыми после commit
# (иначе доступ к полям после коммита снова дёргал бы базу).
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-зависимость: выдаёт сессию на один запрос, гарантирует закрытие.

    yield отдаёт сессию внутрь ручки; блок finally выполнится уже ПОСЛЕ ответа —
    там мы коммитим/откатываем транзакцию и закрываем соединение.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session          # ручка работает внутри открытой транзакции
            await session.commit() # всё прошло — фиксируем изменения
        except Exception:
            await session.rollback()  # ошибка в середине запроса — откатываем
            raise                    # пробрасываем дальше, FastAPI отдаст 500/ошибку
