# Как запустить (Windows PowerShell)

Нужны два терминала: один для бэкенда, второй для фронтенда. Оба должны работать одновременно.

## 0. Один раз: PostgreSQL
Установи PostgreSQL (https://www.postgresql.org/download/windows/), запомни пароль пользователя `postgres`.
Файл `backend/.env` уже содержит строки DATABASE_URL и ADMIN_* — проверь, что пароль в DATABASE_URL совпадает с твоим.

## 1. Терминал 1 — бэкенд (порт 8000)
```powershell
cd C:\edProject\Hakaton27\backend
python -m venv venv          # если venv ещё нет на этом месте
venv\Scripts\Activate.ps1    # активировать окружение
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m alembic upgrade head   # создать таблицы в БД (внимание: ВСЕГДА `python -m alembic`, не `alembic`)
python smoke_test.py             # проверка, что код живой: должно быть «ИТОГ: 26 пройдено, 0 провалено»
uvicorn app.main:app --reload    # сам сервер; остановка Ctrl+C
```
Открой http://localhost:8000/docs — Swagger. Админ по умолчанию: `admin` / `admin123` (создаётся при старте).

## 2. Терминал 2 — фронтенд (порт 5173)
```powershell
cd C:\edProject\Hakaton27\frontend
npm install        # ставит зависимости из package.json (один раз)
npm run dev        # dev-сервер Vite; остановка Ctrl+C
```
Открой http://localhost:5173 — увидишь пустой лист с кнопками «Войти»/«Зарегистрироваться» справа сверху.

## 3. Что проверить руками
1. «Зарегистрироваться»: придумай логин/пароль -> после успеха справа сверху появится «Привет, <логин>».
2. F5 (перезагрузка страницы) — вход должен сохраниться (токен лежит в localStorage браузера).
3. «Выйти» — кнопки вернулись.
4. Войди как `admin` -> в Swagger можно потыкать ручки /users (нужен токен: Authorize -> вставить access_token).

## Частые проблемы
| Симптом | Причина | Лечение |
|---|---|---|
| `Fatal error in launcher: Unable to create process` | папка venv скопирована из другого проекта | удали venv, создай заново, ставь через `python -m pip` |
| Консоль браузера: `blocked by CORS policy` | порт фронта не в списке разрешённых | backend/app/core/config.py, CORS_ORIGINS (там :5173 и :3000) |
| Фронт: «Сервер недоступен» | бэкенд не запущен | Терминал 1 должен держать uvicorn |
| uvicorn падает на старте с ошибкой БД | PostgreSQL не запущен / неверный пароль в .env | запусти службу Postgres, поправь DATABASE_URL |
| `Table users does not exist` | миграции не применены | `python -m alembic upgrade head` |
| Ошибка про display_name при запросе | новая колонка не долетела в твою базу | `python -m alembic upgrade head` (миграция add_display_name) |
