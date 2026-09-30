# RealGame Backend — шаблон для хакатона

Стек: **FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL + Alembic + JWT**.
Готовый каркас с авторизацией, ролями и CRUD пользователей. Дальше — только бизнес-логика.

---

## 1. Запуск с нуля (Windows / PowerShell)

```powershell
cd backend
python -m venv venv                # если venv скопирован из другого проекта — пересоздать обязательно!
venv\Scripts\Activate.ps1          # политика: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
python -m pip install -r requirements.txt   # всегда `python -m pip`, а не `pip` (см. docs/SMOKE_TESTS.md §5)

copy .env.example .env             # Linux/Mac: cp
# отредактируйте .env: DATABASE_URL, SECRET_KEY, ADMIN_USERNAME/PASSWORD

python smoke_test.py               # быстрая проверка без БД: должно быть "0 провалено"

alembic revision --autogenerate -m "init"   # если миграций ещё нет в вашем клоне
alembic upgrade head                        # применить схему к PostgreSQL

uvicorn app.main:app --reload      # сервер на http://localhost:8000
```

- Swagger UI (тыкать ручки руками): **http://localhost:8000/docs** → кнопка *Authorize* → логин через `/auth/login`.
- Админ по умолчанию создаётся сам при старте: `ADMIN_USERNAME`/`ADMIN_PASSWORD` из `.env` (по умолчанию admin/admin123).

## 2. Архитектура: за что отвечает каждая папка

Запрос идёт строго сверху вниз, каждый слой умеет ровно одно дело:

```
HTTP → [api/v1 ручки] → [services логика] → [repositories SQL] → [models таблицы] → БД
              ↑ deps.py склеивает слои и проверяет токен/роль
```

| Путь | Ответственность | Меняем, когда... |
|---|---|---|
| `app/main.py` | Точка входа: FastAPI, CORS, lifespan (создание админа), `/healthcheck` | добавляем middleware/глобальные обработчики |
| `app/core/config.py` | Все настройки из `.env` (`settings.XXX`) | появилась новая переменная окружения |
| `app/core/security.py` | bcrypt-хэши паролей, генерация/проверка JWT | меняем алгоритмы аутентификации |
| `app/core/exceptions.py` | Типизированные ошибки API (404/409/403/401) | нужен новый тип ошибки |
| `app/database/base.py` | `Base` — общий предок моделей + naming convention | почти никогда |
| `app/database/session.py` | engine, фабрика сессий, `get_db()` | настройки пула соединений |
| `app/models/` | SQLAlchemy-модели = таблицы БД | добавили колонку/таблицу |
| `app/schemas/` | Pydantic-контракты вход/выход API | ручка принимает/отдаёт новые поля |
| `app/repositories/` | **Единственное место с SQL** (select/insert/...) | новый способ запроса данных |
| `app/services/` | Бизнес-правила без HTTP | **любые правила фич хакатона — сюда** |
| `app/api/v1/deps.py` | DI-цепочки, `get_current_user`, `require_roles/require_admin` | новая зависимость/охрана ручки |
| `app/api/v1/auth.py` | `/auth/register`, `/auth/login`, `/auth/me` | методы входа |
| `app/api/v1/user.py` | CRUD юзеров + назначение ролей (admin) | ручки пользователей |
| `app/api/v1/api.py` | Сборка роутеров: `include_router(...)` | **новая фича = 1 строка сюда** |
| `migrations/` | Alembic (async env.py читает `.env`) | после правки моделей |
| `docs/SMOKE_TESTS.md` | Инструкция по тестам и расширению | — |
| `smoke_test.py` | 26 сквозных проверок API на SQLite | после каждой новой ручки |

### Матрица доступа текущих ручек

| Метод | Путь | Кто может |
|---|---|---|
| POST | `/api/v1/auth/register` | все |
| POST | `/api/v1/auth/login` | все (form-data) |
| GET | `/api/v1/auth/me` | авторизованные |
| GET | `/api/v1/users?page=&per_page=&role=` | admin |
| GET | `/api/v1/users/{id}` | admin |
| PATCH | `/api/v1/users/me` | авторизованные |
| DELETE | `/api/v1/users/me` | авторизованные (кроме admin) |
| **PATCH** | **`/api/v1/users/{id}/role`** | **admin** (назначение ролей) |
| DELETE | `/api/v1/users/{id}` | admin (не админов) |

Роли: `admin` / `author` / `player` (enum в БД). Регистрация всегда выдаёт `player`;
повышает роли только админ. Защита от потери админки: админ не может понизить/удалить себя.

## 3. Как добавить новую сущность (пример: Game) — чек-лист

Ничего не переписываем, только добавляем файлы и по одной строке в реестры:

1. **Модель** — `app/models/game.py`:
   ```python
   class Game(Base):                     # таблица users уже есть как образец
       __tablename__ = "games"
       id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
       title: Mapped[str] = mapped_column(String(120), nullable=False)
       owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
   ```
   ➕ зарегистрировать в `app/models/__init__.py` (**без этого Alembic/тесты её не увидят!**).
2. **Схемы** — `app/schemas/game.py`: `GameCreate`, `GameResponse` (образец: `schemas/user.py`).
3. **Репозиторий** — `app/repositories/game.py`: класс `GameRepository(session)` с методами
   `create/get_by_id/list_by_owner/...` (копирайт структуры `repositories/user.py`).
4. **Сервис** — `app/services/game.py`: правила («нельзя дубликат названия», «удаляет только владелец»)
   + вызовы репозитория. Ошибки — из `core/exceptions.py`.
5. **DI** — `app/api/v1/deps.py`: `get_game_repo`, `get_game_service`, алиас `GameServiceDep`.
6. **Роутер** — `app/api/v1/game.py`: `router = APIRouter(prefix="/games", tags=["Игры"])`,
   ручки с `CurrentUser`/`RequireAdmin`/`require_roles(UserRoleEnum.AUTHOR)`.
7. **Регистрация** — `app/api/v1/api.py`: `api_router.include_router(game.router)`.
8. **Миграция**: `alembic revision --autogenerate -m "games"` → `alembic upgrade head`.
9. **Тесты**: блок в `smoke_test.py` по инструкции `docs/SMOKE_TESTS.md` → `python smoke_test.py`.

Типичные связки: FK на пользователя (`owner_id`), many-to-many через промежуточную таблицу,
пагинация — как в `GET /users`.

## 4. Правила стиля кода (чтобы шаблоны совпадали)

- В каждом файле докстринг начинается со слова **«Блок:»** — что это за кирпич и куда его трогать.
- У каждой функции/класса docstring: первая строка «что делает», далее Args/Returns/Raises.
- Комментарии над блоками кода, а не вперемешку внутри; поясняем *зачем*, а не *что*.
- Ручки тонкие (вызов сервиса), сервисы не знают про HTTP, репозитории — единственные с SQL.
- Новые ошибки — только через классы `core/exceptions.py`, не `raise HTTPException` в ручках.

## 5. Документация

- Расширение и тесты: **[docs/SMOKE_TESTS.md](docs/SMOKE_TESTS.md)**
- Переменные окружения: см. `.env.example` (комментарии у каждой).
