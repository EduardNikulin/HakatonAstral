// Блок: шапка страницы — правый верхний угол с кнопками входа/регистрации,
// а после входа показывает имя пользователя и кнопку «Выйти».
import { Link, useNavigate } from 'react-router-dom' // Link = переход без перезагрузки; useNavigate = программный переход
import { useAuth } from '../context/AuthContext'     // достаём текущего пользователя из общей коробки
import { clearToken } from '../services/api'         // удаление токена из localStorage

export default function Header() {
  const { user, logoutAction } = useAuth()   // user = профиль или null; logoutAction чистит состояние
  const navigate = useNavigate()             // функция-переход: navigate('/login') = открыть страницу /login

  // handleLogout: полный выход = удалить токен + забыть пользователя + уехать на главную.
  function handleLogout() {
    clearToken()                             // токен больше не будет подставляться в запросы
    logoutAction()                           // setUser(null) в контексте -> шапка перерисует кнопки
    navigate('/')                            // редирект на пустой лист
  }

  return (
    // header: горизонтальная полоса сверху; flex (в styles.css) раздвинет части по краям
    <header className="header">
      {/* brand: логотип-ссылка на главную (Link = переход без перезагрузки страницы) */}
      <Link to="/" className="brand">HakatonAstral</Link>

      {/* Правая часть шапки: содержимое зависит от того, залогинены мы или нет. */}
      <div className="header-right">
        {/* Если пользователя НЕТ (!user) — показываем две кнопки-ссылки.
            <>...</> — «фрагмент»: склеивает два элемента в один без лишнего div. */}
        {!user ? (
          <>
            <Link to="/login" className="btn btn-outline">Войти</Link>                 {/* уедет на /login */}
            <Link to="/register" className="btn btn-solid">Зарегистрироваться</Link>   {/* уедет на /register */}
          </>
        ) : (
          /* Пользователь есть — показываем имя и кнопку выхода */
          <>
            {/* display_name может быть null (заполняется позже в профиле),
                поэтому запасной вариант — username. Оператор || читается «или». */}
            <span className="username">Привет, {user.display_name || user.username}</span>
            {/* button, а не Link: тут действие (выход), а не переход по адресу */}
            <button type="button" onClick={handleLogout} className="btn btn-outline">Выйти</button>
          </>
        )}
      </div>
    </header>
  )
}
