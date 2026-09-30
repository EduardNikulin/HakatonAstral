"""Блок: точка входа приложения — сборка FastAPI, CORS, lifespan.

Запуск для разработки:  uvicorn app.main:app --reload  (из папки backend/)
Swagger с интерактивными ручками: http://localhost:8000/docs

Порядок «что происходит при старте»:
1) создаётся приложение (ниже, create_app) -> 2) lifespan открывает БД и
гарантирует наличие админа -> 3) запросы идут через middleware(CORS) -> api_router.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.repositories.user import UserRepository
from app.services.user import UserService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Код «до старта» и «после остановки» приложения.

    До старта: проверяем доступность БД и создаём админа по умолчанию из .env
    (идемпотентно — если админ уже есть, ничего не произойдёт).
    После остановки: сейчас чистить нечего (соединения закрывает engine сам),
    сюда добавляем освобождение будущих ресурсов (redis, mq и т.п.).
    """
    async with AsyncSessionLocal() as session:          # служебная сессия вне HTTP-запросов
        service = UserService(UserRepository(session))  # цепочку собираем вручную, без Depends
        await service.ensure_admin_exists()             # <- админ из ADMIN_USERNAME/ADMIN_PASSWORD
        await session.commit()                          # фиксируем вставку админа
    yield                                               # всё время работы приложения — «тут»


def create_app() -> FastAPI:
    """Фабрика приложения: здесь настраиваем метаданные, CORS и подключаем API.

    Вынесено в функцию, чтобы тесты могли создавать изолированные экземпляры app.
    """
    app = FastAPI(
        title="RealGame API",                  # имя в Swagger UI
        version="1.0.0",
        description=(
            "Backend шаблона для хакатона: авторизация (JWT), роли admin/author/player, "
            "CRUD пользователей. Точки расширения: services/ (логика), repositories/ (SQL), "
            "api/v1/api.py (новые роутеры)."
        ),
        lifespan=lifespan,
        docs_url="/docs",                      # Swagger UI
        redoc_url="/redoc",                    # альтернативная документация
    )

    # CORS: браузер блокирует запросы фронт(5173)->бек(8000) без этого разрешения.
    # origins берём из настроек (.env), методы — стандартные для REST.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,   # разрешить cookies/auth-заголовки
        allow_methods=["*"],      # GET/POST/PATCH/DELETE...
        allow_headers=["*"],      # Authorization и любые кастомные
    )

    # Единая префикс-точка версионирования: все ручки живут под /api/v1.
    app.include_router(api_router, prefix="/api/v1")

    # Служебный эндпоинт для мониторинга/проверки, что бэк вообще жив.
    @app.get("/healthcheck", tags=["Сервис"], summary="Жив ли бэкенд")
    async def healthcheck() -> dict[str, str]:
        """Возвращает {"status": "ok"} — удобно CI/деплою и быстрой проверке в браузере."""
        return {"status": "ok", "database": "configured"}

    return app


# Экземпляр для `uvicorn app.main:app` (имя `app` — соглашение uvicorn).
app = create_app()
