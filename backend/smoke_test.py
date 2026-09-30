# Интеграционный smoke-тест всего API на SQLite (не нужен PostgreSQL для проверки).
import asyncio, os, sys

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./smoke.db"
os.environ["SECRET_KEY"] = "test_secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin123"

# SQLite не умеет native enum -> патчим тип колонки ДО импорта приложения
import sqlalchemy as sa
from app.models.user import User, UserRoleEnum
User.__table__.c.role.type = sa.Enum(UserRoleEnum, name="user_role",
    values_callable=lambda e: [m.value for m in e], native_enum=False)

from httpx import AsyncClient, ASGITransport
from app.database.base import Base
from app.database.session import async_engine, async_session_maker
from app.main import app

PASS, FAIL = 0, 0
def check(name, cond, extra=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  [OK]   {name}")
    else: FAIL += 1; print(f"  [FAIL] {name} {extra}")

async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # lifespan вручную (bootstrap админа)
        from app.main import bootstrap_admin
        await bootstrap_admin()

        # 1. Админ логинится
        r = await c.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
        check("POST /auth/login (admin)", r.status_code == 200, r.text)
        admin_token = r.json()["access_token"]
        ah = {"Authorization": f"Bearer {admin_token}"}

        # 2. Регистрация нового пользователя
        r = await c.post("/api/v1/auth/register", json={"username": "player_one", "password": "secret123"})
        check("POST /auth/register", r.status_code == 201, r.text)
        player = r.json()
        check("registered role == player", player["role"] == "player", str(player))

        # 3. Дубликат имени -> 409
        r = await c.post("/api/v1/auth/register", json={"username": "player_one", "password": "secret123"})
        check("duplicate register -> 409", r.status_code == 409, r.text)

        # 4. Неверный пароль -> 401
        r = await c.post("/api/v1/auth/login", data={"username": "player_one", "password": "wrong_pass"})
        check("bad login -> 401", r.status_code == 401, r.text)

        # 5. Логин игрока + /auth/me
        r = await c.post("/api/v1/auth/login", data={"username": "player_one", "password": "secret123"})
        player_token = r.json()["access_token"]
        ph = {"Authorization": f"Bearer {player_token}"}
        r = await c.get("/api/v1/auth/me", headers=ph)
        check("GET /auth/me (player)", r.status_code == 200 and r.json()["username"] == "player_one", r.text)

        # 6. Без токена -> 401
        r = await c.get("/api/v1/users")
        check("GET /users without token -> 401", r.status_code == 401, r.text)

        # 7. Игрок не может смотреть список пользователей -> 403
        r = await c.get("/api/v1/users", headers=ph)
        check("GET /users as player -> 403", r.status_code == 403, r.text)

        # 8. Игрок не может менять роли -> 403
        r = await c.patch(f"/api/v1/users/{player['id']}/role", json={"role": "admin"}, headers=ph)
        check("PATCH role as player -> 403", r.status_code == 403, r.text)

        # 9. Админ назначает роль author -> 200
        r = await c.patch(f"/api/v1/users/{player['id']}/role", json={"role": "author"}, headers=ah)
        check("PATCH /users/{id}/role as admin", r.status_code == 200 and r.json()["role"] == "author", r.text)

        # 10. Невалидная роль -> 422
        r = await c.patch(f"/api/v1/users/{player['id']}/role", json={"role": "superman"}, headers=ah)
        check("invalid role -> 422", r.status_code == 422, r.text)

        # 11. Админ получает список и карточку
        r = await c.get("/api/v1/users", headers=ah)
        check("GET /users as admin", r.status_code == 200 and r.json()["total"] >= 2, r.text)
        r = await c.get(f"/api/v1/users/{player['id']}", headers=ah)
        check("GET /users/{id} as admin", r.status_code == 200, r.text)
        r = await c.get("/api/v1/users/00000000-0000-0000-0000-000000000000", headers=ah)
        check("GET missing user -> 404", r.status_code == 404, r.text)

        # 12. Пользователь обновляет свой профиль
        r = await c.patch("/api/v1/users/me", json={"username": "renamed_player"}, headers=ph)
        check("PATCH /users/me", r.status_code == 200 and r.json()["username"] == "renamed_player", r.text)

        # 13. Админ удаляет пользователя; сам себя — нельзя
        r = await c.delete(f"/api/v1/users/{player['id']}", headers=ah)
        check("DELETE /users/{id} as admin", r.status_code == 204, r.text)
        me = (await c.get("/api/v1/auth/me", headers=ah)).json()
        r = await c.delete(f"/api/v1/users/{me['id']}", headers=ah)
        check("admin self-delete -> 403", r.status_code == 403, r.text)

    print(f"\nRESULT: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)

asyncio.run(main())
