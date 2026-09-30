from fastapi import APIRouter
from app.api.v1 import auth, user

api_router = APIRouter()

api_router.include_router(auth.router)        # Авторизация и сессии
api_router.include_router(user.router)        # Профиль
