# RealGame Backend

FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL + Alembic + JWT.

## Архитектура (куда что добавлять)

```
app/
├── main.py            # точка входа: приложение, CORS, lifespan (создаёт админа по умолчанию)
├── core/              # каркас: настройки (.env), security (JWT/bcrypt), exceptions (ошибки API)
├── database/          # base.py (Base + naming convention), session.py (engine + get_db)
├── models/            # SQLAlchemy-модели = таблицы БД. Реестр в __init__.py (важно для Alembic!)
├── schemas/           # Pydantic-схемы: вход/выход API. Параллельно моделям, файл на сущность
├── repositories/      # слой запросов к БД (select/insert/update/delete). Больше SQL нигде не пишем
├── services/          # бизнес-логика без HTTP. Сюда добавляй правила хакатона
└── api/v1/
    ├── deps.py        # DI: get_db -> repo -> service; get_current_user; require_roles/require_admin
    ├── auth.py        # /auth/register, /auth/login, /auth/me
    ├── user.py        # CRUD пользователей + назначение ролей (admin)
    └── api.py         # сборка роутеров: include_router(new_feature.router) — одна строка
migrations/            # Alembic (async env.py читает DATABASE_URL из .env)
```

### Как добавить новую сущность (например, Game) — ничего не переписываем:
1. `models/game.py` — модель; зарегистрировать в `models/__init__.py`
2. `schemas/game.py` — GameCreate/GameResponse
3. `repositories/game.py` — GameRepository (запросы)
4. `services/game.py` — GameService (логика)
5. `api/v1/deps.py` — `get_game_repo`, `get_game_service`
6. `api/v1/game.py` — router с ручками
7. `api/v1/api.py` — `include_router(game.router)`
8. `alembic revision --autogenerate -m "games"` -> `alembic upgrade head`

## Права и роли
- Роли: `admin`, `author`, `player` (enum в БД). При регистрации всегда `player`.
- Назначение ролей — только от имени админа: `PATCH /api/v1/users/{id}/role` (`Depends(require_admin)`).
- Админ по умолчанию создаётся при старте: `ADMIN_USERNAME` / `ADMIN_PASSWORD` из `.env` (admin/admin123).

## Запуск
```bash
cd backend
cp .env.example .env                # затем поменять SECRET_KEY и пароли
pip install -r requirements.txt
alembic revision --autogenerate -m "users"   # первая миграция
alembic upgrade head
uvicorn app.main:app --reload       # http://localhost:8000/docs
```

## Smoke-тест (без PostgreSQL, на SQLite)
```bash
python smoke_test.py                # 17 проверок всех ручек и прав
```

## Ручки (v1)
| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| POST | /api/v1/auth/register | все | регистрация (роль player) |
| POST | /api/v1/auth/login | все | вход, выдаёт JWT (form-data: username/password) |
| GET | /api/v1/auth/me | авторизованные | текущий пользователь |
| GET | /api/v1/users | admin | список (пагинация offset/limit, фильтр ?role=) |
| GET | /api/v1/users/{id} | admin | карточка пользователя |
| PATCH | /api/v1/users/me | авторизованные | править свой профиль |
| DELETE | /api/v1/users/me | авторизованные | удалить свой аккаунт (не админ) |
| PATCH | /api/v1/users/{id}/role | admin | назначить роль admin/author/player |
| DELETE | /api/v1/users/{id} | admin | удалить пользователя |
