// Блок: HTTP-клиент — ЕДИНСТВЕННОЕ место на фронте, где мы ходим на бэкенд.
// Правило: компоненты никогда не пишут axios.get('http://...') руками — только функции отсюда.
// Так адрес бэка и подстановка токена живут в одном месте и меняются в одном месте.
import axios from 'axios'

// Создаём настроенный экземпляр axios (а не пользуемся глобальным).
export const api = axios.create({
  // Базовый префикс всех ручек бэка. '/' в конце ВАЖЕН: дальше клеим 'auth/login' и т.п.
  // В продакшене этот адрес станет доменом сервера — менять будем одной строкой.
  baseURL: 'http://localhost:8000/api/v1/',
})

// Ключ, под которым токен лежит в localStorage браузера (переживает перезагрузку страницы).
const TOKEN_KEY = 'access_token'

// --- три маленькие функции-хранилища: чтобы больше нигде не писать localStorage напрямую ---

// saveToken: кладём JWT в браузерное хранилище после успешного входа.
export function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token)     // localStorage хранит только строки — JWT и есть строка
}

// getToken: читаем токен (или null, если пользователь не входил / вышел).
export function getToken() {
  return localStorage.getItem(TOKEN_KEY)     // getItem вернёт null, если ключа нет — это наш флаг «не авторизован»
}

// clearToken: удаляем токен — операция «выйти». Сам JWT с сервера не забирается, он просто перестаёт отправляться.
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

// --- перехватчик запросов: автоматическая подстановка токена ---

// Интерцептор — крючок axios: функция выполняется ПЕРЕД уходом каждого запроса.
// Благодаря ему ни один компонент не помнит про заголовок Authorization.
api.interceptors.request.use((config) => {
  const token = getToken()                   // достали токен из хранилища
  if (token) {                               // если пользователь залогинен —
    config.headers.Authorization = `Bearer ${token}` // лепим стандартный заголовок: Bearer <jwt>.
                                                   // Бэкенд (deps.py) умеет его читать и проверять подпись.
  }
  return config                              // отдаём доработанный конфиг; axios отправит запрос
})

// --- конкретные функции под наши ручки ---

// login: POST /auth/login. Формат form-data (username + password полями формы), а НЕ json —
// потому что бэкенд использует OAuth2PasswordRequestForm (см. backend/app/api/v1/auth.py).
export async function login(username, password) {
  const body = new URLSearchParams()         // объект, который axios сериализует как form-data
  body.append('username', username)          // первое поле формы — логин
  body.append('password', password)          // второе поле формы — пароль
  const { data } = await api.post('auth/login', body) // дождались ответа; data = тело ответа
  return data                                // ожидаем { access_token: "...", token_type: "bearer" }
}

// register: POST /auth/register — вот здесь JSON уместен (бэкенд ждёт UserCreate-схему).
// При успехе бэк вернёт профиль нового пользователя (без пароля), роль всегда player.
export async function register(username, password) {
  const { data } = await api.post('auth/register', { username, password }) // второй аргумент = JSON-тело
  return data                                // { id, username, role, created_at, display_name }
}

// fetchMe: GET /auth/me — «я кто?». Используется при загрузке страницы, чтобы понять,
// жива ли ещё сессия по сохранённому токену, и получить роль для ветвления меню.
export async function fetchMe() {
  const { data } = await api.get('auth/me')  // заголовок Authorization подставит интерцептор
  return data                                // профиль текущего пользователя
}

// updateMe: PATCH /users/me — частичное обновление профиля (например, отображаемого имени).
export async function updateMe({ displayName }) {
  const { data } = await api.patch('users/me', { display_name: displayName })
  return data                                // обновлённый профиль — положим его в состояние
}
