// Блок: страница регистрации. Заполняем логин+пароль -> POST /auth/register -> сразу входим.
import { useState } from 'react'                    // состояния полей формы, ошибки и режима загрузки
import { Link, useNavigate } from 'react-router-dom' // ссылка «уже есть аккаунт» + редирект после успеха
import { register, login, fetchMe, saveToken } from '../services/api' // наши функции-запросы к бэку
import { useAuth } from '../context/AuthContext'    // чтобы записать пользователя в общую коробку

export default function RegisterPage() {
  const [username, setUsername] = useState('')       // текст в поле логина
  const [password, setPassword] = useState('')       // текст в поле пароля
  const [repeat, setRepeat] = useState('')           // повтор пароля — проверяем ТОЛЬКО на фронте для удобства
  const [error, setError] = useState('')             // сообщение об ошибке ('' = всё хорошо)
  const [loading, setLoading] = useState(false)      // кнопка неактивна, пока запрос в пути

  const { loginAction } = useAuth()                  // функция «пользователь вошёл» из контекста
  const navigate = useNavigate()                     // программный переход на главную

  async function handleSubmit(event) {
    event.preventDefault()                           // отменяем перезагрузку страницы браузером
    setError('')                                     // убираем старую ошибку
    if (password !== repeat) {                       // проверка совпадения двух паролей — до всякого запроса:
      setError('Пароли не совпадают')                // незачем дёргать сервер очевидной ерундой
      return                                         // прерываем отправку
    }
    setLoading(true)                                 // включаем спиннер/блокировку кнопки
    try {
      await register(username, password)             // 1) создаём аккаунт; бэк вернёт профиль (роль всегда player)
      const { access_token } = await login(username, password) // 2) тут же логинимся тем же логином/паролем,
      saveToken(access_token)                        //    чтобы не заставлять юзера вводить пароль второй раз
      const profile = await fetchMe()                // 3) GET /auth/me — получаем полный профиль с ролью
      loginAction(profile)                           // 4) кладём в контекст -> шапка мгновенно покажет имя
      navigate('/')                                  // 5) уезжаем на пустой лист
    } catch (err) {
      // 409 -> «Логин уже занят», 422 -> «Пароль слишком короткий» и т.п.: берём detail от FastAPI.
      setError(err?.response?.data?.detail || 'Сервер недоступен, попробуйте позже')
    } finally {
      setLoading(false)                              // гасим загрузку при любом исходе
    }
  }

  return (
    <main className="page">                          {/* та же центрирующая колонка, что и на входе */}
      <section className="card">                     {/* белая карточка */}
        <h1>Регистрация</h1>                         {/* заголовок */}
        <form onSubmit={handleSubmit}>               {/* привязка отправки к нашей функции */}
          <label htmlFor="reg-username">Логин</label>
          <input
            id="reg-username"                        // уникальный id (не конфликтует с LoginPage)
            value={username}                         // управляемое поле: значение из state
            onChange={(e) => setUsername(e.target.value)} // каждое нажатие клавиши обновляет state
            placeholder="придумайте логин"           // подсказка внутри пустого поля
            autoComplete="username"                  // автозаполнение браузера
            required                                 // браузер не отправит пустое поле
          />

          <label htmlFor="reg-password">Пароль</label>
          <input
            id="reg-password"
            type="password"                          // точки вместо символов
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"              // менеджер паролей предложит СОЗДАТЬ новый, а не подставить старый
            required
          />

          <label htmlFor="reg-repeat">Повторите пароль</label>
          <input
            id="reg-repeat"
            type="password"
            value={repeat}
            onChange={(e) => setRepeat(e.target.value)}
            autoComplete="new-password"
            required
          />

          {error && <p className="error">{error}</p>} {/* рисуем ошибку только если она есть */}

          <button type="submit" disabled={loading}>   {/* disabled блокирует двойные отправки */}
            {loading ? 'Создаём...' : 'Зарегистрироваться'} // текст зависит от состояния запроса
          </button>
        </form>

        <p className="hint">
          Уже есть аккаунт? <Link to="/login">Войти</Link> {/* переход без перезагрузки */}
        </p>
      </section>
    </main>
  )
}
