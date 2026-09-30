"""Блок: сборка всех версионных роутеров в один api_router.

Единственная точка, где «регистрируются» фичи API. Версия v1 вынесена в префикс
main.py (/api/v1), чтобы при нужде добавить /api/v2, не трогая существующие ручки.

НОВАЯ ФИЧА = одна строка include_router сюда (+ её router в отдельном файле).
"""
from fastapi import APIRouter

from app.api.v1 import auth, user

api_router = APIRouter()

# Порядок подключения не важен; теги берём из самих роутеров (см. auth.py / user.py).
api_router.include_router(auth.router)   # /auth/register, /auth/login, /auth/me
api_router.include_router(user.router)   # /users ...
