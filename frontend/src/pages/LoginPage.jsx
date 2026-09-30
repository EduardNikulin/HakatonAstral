// Блок: страница входа в аккаунт. Форма -> запрос на бэк -> токен -> профиль -> редирект.
import { useState } from 'react'                 // локальные переменные-состояния (значения полей формы, ошибки)
import { Link, useNavigate } from 'react-router-dom' // переходы: ссылка «регистрация» и программный редирект
import { login, fetchMe, saveToken, clearToken } from '../services/api' // наш HTTP-клиент + хранилище токена
import { useAuth } from '../context/AuthContext' // чтобы после входа записать пользователя в общую коробку

export default function LoginPage() {
  // Четыре независимых куска состояния страницы. Каждое изменение -> перерисовка.
  const [username, setUsername] = useState('')   // что набрано в поле логина
  const [password, setPassword] = useState('')   // что набрано в поле пароля
  const [error, setError] = useState('')         // текст ошибки для показа под формой ('' = ошибок нет)
  const [loading, setLoading] = useState(false)  // true, пока запрос в пути — блокируем кнопку от двойного клика

  const { loginAction } = useAuth()              // функция записи профиля в контекст
  const navigate = useNavigate()                 // программный переход после успеха

  // handleSubmit: вызывается браузером при отправке формы (Enter по полю или клик по кнопке).
  async function handleSubmit(event) {
    event.preventDefault()                       // ОТМЕНЯЕМ поведение браузера по умолчанию (перезагрузка страницы с GET-запросом)
    setError('')                                 // чистим старую ошибку, если была
    setLoading(true)                             // включаем режим «идёт работа»
    try {                                        // весь сетевой путь оборачиваем: любая 4xx/5xx прыгнет в catch
      const { access_token } = await login(username, password) // POST /auth/login (form-data); дождались JWT
      saveToken(access_token)                    // кладём токен в localStorage — дальше интерцептор сам его подставит
      const profile = await fetchMe()            // GET /auth/me с этим токеном -> узнали id, роль, имя
      loginAction(profile)                       // положили профиль в контекст -> шапка мгновенно перерисуется
      navigate('/')                              // и ушли на главную
    } catch (err) {
      // axios кладёт ответ сервера в err.response; FastAPI отдаёт текст ошибки в поле detail.
      // 401 -> "Неверный логин или пароль", 5xx/офлайн -> общий текст. Никаких падений страницы.
      const detail = err?.response?.data?.detail
      setError(detail || 'Сервер недоступен, попробуйте позже')
      clearToken()                               // если логин не прошёл — никакого мусорного токена держать не будем
    } finally {
      setLoading(false)                          // всегда гасим спиннер: и при успехе, и при провале
    }
  }

  return (
    <main className="page">                      {/* центрирующая колонка контента */}
      <section className="card">                 {/* белая карточка авторизации */}
        <h1>Вход</h1>                            {/* заголовок карточки */}

        {/* form: onSubmit привязан к нашей функции; поля управляемые — value берётся из state */}
        <form onSubmit={handleSubmit}>
          {/* label: подпись поля; htmlFor связывает её с input по id (клик по тексту фокусирует поле) */}
          <label htmlFor="username">Логин</label>
          {/* input: цель для label и якорь автозаполнения браузера */}
          <input
            id="username"
            value={username}                                            // значение поля = наша переменная (управляемый input)
            onChange={(e) => setUsername(e.target.value)}               // каждое нажатие клавиши пишем ввод в state
            placeholder="admin"                                         // подсказка-пример внутри пустого поля
            autoComplete="username"                                     // браузер предложит сохранённый логин
            required                                                    // пустое поле браузер не даст отправить вообще
          />

          <label htmlFor="password">Пароль</label>
          <input
            id="password"
            type="password"                                             // скрывает вводимые символы точками
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"                             // стандартное имя для менеджеров паролей
            required
          />

          {/* Условный рендер ошибки: JSX-выражение {условие && <элемент>} рисует элемент только если условие истинно */}
          {error && <p className="error">{error}</p>}

          <button type="submit" disabled={loading}>
            {/* Текст кнопки меняется в зависимости от состояния запроса */}
            {loading ? 'Проверяем...' : 'Войти'}
          </button>
        </form>

        {/* Ссылка-переход на регистрацию без перезагрузки страницы */}
        <p className="hint">
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </section>
    </main>
  )
}
