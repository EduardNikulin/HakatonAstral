"""Блок: криптография — хэширование паролей и генерация/проверка JWT-токенов.

Здесь НЕТ доступа к базе и HTTP — чистые функции. Используется сервисами (пароли)
и зависимостями deps.py (разбор токена).
"""
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Контекст хэширования. bcrypt — стандарт де-факто; параметр rounds задаёт стоимость.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Возвращает bcrypt-хэш пароля (никогда не храним пароль в открытом виде)."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Сверяет введённый пароль с сохранённым хэшем (сравнение внутри bcrypt)."""
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str | uuid.UUID, extra_claims: dict[str, Any] | None = None) -> str:
    """Генерирует JWT для пользователя.

    Args:
        subject: кого выдаём токен — обычно id пользователя (стандартный claim "sub").
        extra_claims: дополнительные поля в payload (например {"role": "admin"}),
            чтобы deps мог проверять роль без лишнего запроса к БД.

    Returns:
        Подписанная строка токена — её клиент кладёт в заголовок Authorization.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(subject),          # субъект токена (id пользователя)
        "exp": expire,                # срок годности — после него токен невалиден
    }
    if extra_claims:                  # добавляем role и пр., если передали
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Проверяет подпись и срок токена, возвращает его payload как dict.

    Raises:
        JWTError: токен повреждён, подпись не совпала (подделка) или истёк срок.
        Вызывающий код (deps.py) превращает это в HTTP 401.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
