"""Блок: конфигурация приложения.

Все настройки читаются из переменных окружения (файл .env в корне backend/).
Значения по умолчанию подходят для локальной разработки; в бою переопределяем
через ENV-переменные. Доступ к настройкам из кода: `from app.core.config import settings`.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Имя поля = имя переменной окружения (без учёта регистра)."""

    # --- База данных -----------------------------------------------------------
    # Asyncpg-строка подключения к PostgreSQL.
    # Формат: postgresql+asyncpg://user:pass@host:port/dbname
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/realgame"

    # --- JWT -------------------------------------------------------------------
    # Секрет для подписи токенов. В бою ОБЯЗАТЕЛЬНО заменить на длинную случайную строку!
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"                    # алгоритм подписи JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # токен живёт сутки

    # --- Админ по умолчанию ----------------------------------------------------
    # Создаётся автоматически при старте приложения, если логина с таким именем нет.
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # --- CORS ------------------------------------------------------------------
    # Список источников фронта, которым браузеру разрешено обращаться к API.
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Читаем .env рядом с backend/; лишние переменные в .env игнорируем, а не падаем.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Единственный экземпляр настроек на всё приложение (импортируем везде как `settings`).
settings = Settings()
