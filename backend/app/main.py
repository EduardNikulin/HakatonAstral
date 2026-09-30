# Точка входа FastAPI. Здесь: настройка приложения, CORS, жизненный цикл (startup/shutdown).
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.database.session import async_session_maker
from app.repositories.user import UserRepository
from app.services.user import UserService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("realgame")


async def bootstrap_admin() -> None:
    """При старте гарантируем, что в БД есть администратор (ADMIN_USERNAME/ADMIN_PASSWORD из .env)."""
    async with async_session_maker() as session:
        service = UserService(UserRepository(session))
        created = await service.ensure_admin_exists(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
        await session.commit()
        if created:
            logger.info(f"Создан администратор по умолчанию: {settings.ADMIN_USERNAME}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код до startup — инициализация; после yield — shutdown.
    try:
        await bootstrap_admin()
    except Exception as e:  # не роняем старт, если БД ещё недоступна (например, до первой миграции)
        logger.warning(f"Не удалось создать администратора по умолчанию: {e}")
    yield


app = FastAPI(
    title="RealGame API",
    description="Бэкенд для игрового проекта RealGame",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def read_root():
    return {"status": "working", "message": "Welcome to RealGame API!"}
