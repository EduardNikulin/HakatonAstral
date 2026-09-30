"""Блок: смоук-тесты всего API без PostgreSQL и без запуска сервера.

Что это: 17 сквозных проверок (регистрация -> вход -> CRUD -> роли -> запреты),
которые гоняют приложение «в-process» через httpx ASGI-транспорт на in-memory
SQLite. Ни uvicorn, ни Docker не нужны.

Запуск из папки backend/:  python smoke_test.py
Код возврата: 0 — всё зелёное, 1 — есть проваленные проверки (удобно для CI).

Как добавить тест под новую ручку: см. docs/SMOKE_TESTS.md (раздел «Расширение»).
"""
import asyncio
import sys

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ВАЖНО: подмену конфигурации делаем ДО импорта app.main — иначе engine уже
# создастся с реальным DATABASE_URL из .env.
from app.core.config import settings

settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"  # тестовая база в памяти

from app.database.base import Base                         # noqa: E402
from app.database.session import get_db                    # noqa: E402
from app.main import app                                   # noqa: E402
from app.repositories.user import UserRepository           # noqa: E402

PASSED: list[str] = []   # список успешных проверок
FAILED: list[str] = []   # список провалов — из-за него выходим с кодом 1


def check(name: str, condition: bool, hint: str = "") -> None:
    """Фиксирует результат одной проверки; hint печатается только при провале."""
    (PASSED if condition else FAILED).append(name)
    mark = "OK  " if condition else "FAIL"
    print(f"[{mark}] {name}" + (f"  <- {hint}" if not condition and hint else ""))


async def make_client() -> httpx.AsyncClient:
    """Создаёт «HTTP-клиент поверх приложения» с изолированной SQLite-базой.

    Механика: httpx умеет отправлять запросы прямо в ASGI-приложение (transport=
    ASGITransport(app=...)) — сеть не используется. lifespan при этом НЕ выполняется,
    поэтому таблицы создаём руками, а админа заводим явным вызовом сервиса.
    """
    engine = create_async_engine(settings.DATABASE_URL)
    tables = Base.metadata              # все модели уже импортированы через app.main
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # Пересоздаём таблицы на каждой сессии клиента — тесты полностью независимы.
    async def override_get_db():
        async with Session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Создаём схему БД и админа до первого запроса (эмуляция lifespan).
    async with engine.begin() as conn:
        await conn.run_sync(tables.create_all)
    async with Session() as admin_session:
        service_repo = UserRepository(admin_session)
        from app.services.user import UserService
        await UserService(service_repo).ensure_admin_exists()
        await admin_session.commit()

    app.dependency_overrides[get_db] = override_get_db
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


V1 = "/api/v1"  # короткий алиас — меньше копипасты префикса в тестах


async def login(client: httpx.AsyncClient, username: str, password: str) -> str:
    """Хелпер: логин по form-data и извлечение токена. Падает с assert, если вход не удался."""
    r = await client.post(f"{V1}/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, f"login {username}: {r.status_code} {r.text}"
    return r.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    """Заголовок Authorization из токена — для всех защищённых запросов."""
    return {"Authorization": f"Bearer {token}"}


async def run() -> None:
    """Все проверки по порядку. Сценарий: админ заводит игрока и крутит его права."""
    client = await make_client()

    # ---------- 1. healthcheck / публичные ручки --------------------------------
    r = await client.get("/healthcheck")
    check("GET /healthcheck -> 200", r.status_code == 200, r.text)

    r = await client.post(f"{V1}/auth/register", json={"username": "player1", "password": "secret123"})
    check("POST /auth/register -> 201", r.status_code == 201, r.text)
    check("register отдаёт роль player", r.json().get("role") == "player", str(r.json()))
    check("register не течёт пароль", "password" not in r.text and "hash" not in r.text.lower())

    r = await client.post(f"{V1}/auth/register", json={"username": "player1", "password": "secret123"})
    check("дубликат логина -> 409", r.status_code == 409, r.text)

    r = await client.post(f"{V1}/auth/register", json={"username": "ab", "password": "123"})
    check("кривые поля регистрации -> 422 (валидация Pydantic)", r.status_code == 422, r.text)

    # ---------- 2. вход ----------------------------------------------------------
    r = await client.post(f"{V1}/auth/login", data={"username": "player1", "password": "WRONG"})
    check("неверный пароль -> 401", r.status_code == 401, r.text)

    token = await login(client, "player1", "secret123")
    check("POST /auth/login -> JWT", isinstance(token, str) and len(token) > 20)

    r = await client.get(f"{V1}/auth/me", headers=auth(token))
    check("GET /auth/me -> профиль владельца токена",
          r.status_code == 200 and r.json()["username"] == "player1", r.text)
    player_id = r.json()["id"]

    r = await client.get(f"{V1}/auth/me")
    check("GET /auth/me без токена -> 401", r.status_code == 401, r.text)

    r = await client.get(f"{V1}/auth/me", headers=auth("garbage.token.here"))
    check("битый токен -> 401", r.status_code == 401, r.text)

    # ---------- 3. админ: вход и управление -------------------------------------
    admin_token = await login(client, settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
    check("логин админа из .env работает", bool(admin_token))

    r = await client.get(f"{V1}/users", headers=auth(admin_token))
    check("GET /users как admin -> 200", r.status_code == 200, r.text)
    check("список содержит админа и игрока", r.json()["total"] >= 2, str(r.json()))

    r = await client.get(f"{V1}/users", params={"role": "admin"}, headers=auth(admin_token))
    check("фильтр ?role=admin возвращает только админов",
          all(u["role"] == "admin" for u in r.json()["items"]))

    r = await client.patch(f"{V1}/users/{player_id}/role", json={"role": "author"}, headers=auth(admin_token))
    check("PATCH /users/{id}/role как admin -> 200, роль сменилась",
          r.status_code == 200 and r.json()["role"] == "author", r.text)

    r = await client.patch(f"{V1}/users/{player_id}/role", json={"role": "wizard"}, headers=auth(admin_token))
    check("несуществующая роль -> 422 (enum)", r.status_code == 422, r.text)

    # Повышаем ИГРОКА до admin — это обычный рабочий кейс (админ даёт права юзеру).
    newbie_reg = await client.post(f"{V1}/auth/register", json={"username": "newbie", "password": "secret123"})
    newbie_id = newbie_reg.json()["id"]
    r = await client.patch(f"{V1}/users/{newbie_id}/role", json={"role": "admin"}, headers=auth(admin_token))
    check("повышение игрока до admin -> 200", r.status_code == 200 and r.json()["role"] == "admin", r.text)

    # Понизить ЧУЖОГО админа можно... но только если это не ты сам. Проверяем обратное:
    # текущий админ пытается снять роль с самого себя -> 403 (защита от «остаться без админа»).
    admin_me = await client.get(f"{V1}/auth/me", headers=auth(admin_token))
    my_admin_id = admin_me.json()["id"]
    r = await client.patch(f"{V1}/users/{my_admin_id}/role", json={"role": "player"}, headers=auth(admin_token))
    check("понизить себя админу -> 403 (защита от потери админки)", r.status_code == 403, r.text)

    # Итого в базе два админа: дефолтный и newbie (повышен выше). Удалять админов нельзя:
    r = await client.delete(f"{V1}/users/{newbie_id}", headers=auth(admin_token))
    check("DELETE другого админа -> 403 (админы не удаляются)", r.status_code == 403, r.text)

    # ---------- 4. игрок против админских ручек -----------------------------------
    # Отдельный «чистый» игрок: register всегда выдаёт роль player.
    await client.post(f"{V1}/auth/register", json={"username": "pure_player", "password": "secret123"})
    player_token = await login(client, "pure_player", "secret123")

    r = await client.get(f"{V1}/users", headers=auth(player_token))
    check("GET /users как не-admin -> 403", r.status_code == 403, r.text)

    r = await client.delete(f"{V1}/users/{player_id}", headers=auth(player_token))
    check("DELETE чужого как не-admin -> 403", r.status_code == 403, r.text)

    # ---------- 5. самообслуживание пользователя -----------------------------------
    r = await client.patch(f"{V1}/users/me", json={"username": "player_renamed"}, headers=auth(player_token))
    check("PATCH /users/me меняет свой логин", r.status_code == 200 and r.json()["username"] == "player_renamed", r.text)

    r = await client.delete(f"{V1}/users/me", headers=auth(player_token))
    check("DELETE /users/me как игрок -> 204 (аккаунт удалён)", r.status_code == 204, r.text)

    r = await client.get(f"{V1}/auth/me", headers=auth(player_token))
    check("токен удалённого юзера мёртв -> 401", r.status_code == 401, r.text)

    r = await client.get(f"{V1}/users/00000000-0000-0000-0000-000000000000", headers=auth(admin_token))
    check("несуществующий id -> 404", r.status_code == 404, r.text)

    # ---------- Итог ----------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"ИТОГ: {len(PASSED)} пройдено, {len(FAILED)} провалено")
    if FAILED:
        print("Проваленные проверки:")
        for name in FAILED:
            print(f"  - {name}")
    await client.aclose()
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    asyncio.run(run())
