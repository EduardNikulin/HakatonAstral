# Единая точка сборки всех роутеров API v1.
# Новая сущность: создаёшь файл в app/api/v1/, импортируешь router и добавляешь одну строку ниже.
from fastapi import APIRouter

from app.api.v1 import auth, user

api_router = APIRouter()

api_router.include_router(auth.router)   # /auth/*    — регистрация, вход, профиль
api_router.include_router(user.router)   # /users/*   — CRUD пользователей (админ + self-service)

# Пример подключения новой фичи на следующем шаге:
# from app.api.v1 import game
# api_router.include_router(game.router)
