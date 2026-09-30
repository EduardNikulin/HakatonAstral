# Централизованная обработка ошибок приложения.
# Новые бизнес-ошибки добавляем сюда — ручки остаются чистыми.
from fastapi import HTTPException, status


class UserNotFoundError(HTTPException):
    def __init__(self, user_id: str = ""):
        detail = "Пользователь не найден"
        if user_id:
            detail += f": {user_id}"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UsernameAlreadyExistsError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким именем уже существует",
        )


class InvalidCredentialsError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )


class NotAuthenticatedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedError(HTTPException):
    def __init__(self, detail: str = "Недостаточно прав для этого действия"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
