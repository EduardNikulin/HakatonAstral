"""Блок: единый формат ошибок API.

Сервисы и репозитории НЕ умеют работать с HTTP — они бросают исключения из этого
файла, а обработчики в main.py превращают их в JSON-ответы с правильным кодом.
Благодаря этому тексты/коды ошибок одинаковые во всём приложении, и новым фичам
не нужно городить свои ошибки.
"""
from fastapi import HTTPException, status


class ApiError(HTTPException):
    """Базовая ошибка API. Наследуемся от HTTPException — FastAPI сама отдаст JSON."""

    def __init__(self, status_code: int, detail: str):
        """Args:
            status_code: HTTP-код (400/403/404/...).
            detail: человекочитаемое сообщение — попадёт в ответ клиенту.
        """
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(ApiError):
    """Сущность не найдена в БД → 404. Бросаем из сервисов/репо по id."""

    def __init__(self, entity: str = "Объект", ident: object = ""):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{entity} не найден(а): {ident}")


class AlreadyExistsError(ApiError):
    """Дубликат уникального поля (логин/email уже занят) → 409 Conflict."""

    def __init__(self, field: str, value: str):
        super().__init__(status.HTTP_409_CONFLICT, f"«{field}» уже занят: {value}")


class PermissionDeniedError(ApiError):
    """Пользователь авторизован, но его роли недостаточно → 403 Forbidden."""

    def __init__(self, message: str = "Недостаточно прав"):
        super().__init__(status.HTTP_403_FORBIDDEN, message)


class InvalidCredentialsError(ApiError):
    """Логин/пароль не совпали или токен невалиден → 401 Unauthorized."""

    def __init__(self, message: str = "Неверные учётные данные"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, message)
