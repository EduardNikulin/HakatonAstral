# Эндпоинты авторизации: регистрация, вход (JWT), текущий пользователь.
# Вся логика — в UserService; здесь только HTTP-обёртки.
from datetime import timedelta

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.v1.deps import get_current_user, get_user_service
from app.core.exceptions import InvalidCredentialsError
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse
from app.services.user import UserService

router = APIRouter(prefix="/auth", tags=["Auth"])

ACCESS_TOKEN_TTL_MINUTES = 60


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, service: UserService = Depends(get_user_service)):
    """Регистрация нового пользователя. Роль всегда player — админа назначает только админ."""
    return await service.register(user_in)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_user_service),
):
    """Вход (OAuth2 form-data: username + password). Возвращает JWT-токен."""
    user = await service.repo.get_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise InvalidCredentialsError()
    token = create_access_token(subject=str(user.id), expires_delta=timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Профиль текущего пользователя по JWT — для восстановления сессии на фронте."""
    return current_user
