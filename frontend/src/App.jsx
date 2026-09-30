// Блок: маршрутизация — соответствие «адрес в браузере -> какой экран показать».
// Плюс общая рамка страницы: сверху всегда Header, ниже — текущая страница.
import { Routes, Route, Navigate } from 'react-router-dom' // Routes = список правил, Route = одно правило, Navigate = переезд
import { useAuth } from './context/AuthContext'            // состояние «кто вошёл» и идёт ли проверка сессии
import Header from './components/Header'                   // правый верхний угол: войти/зарегистрироваться или имя
import LoginPage from './pages/LoginPage'                  // форма входа
import RegisterPage from './pages/RegisterPage'            // форма регистрации
import HomePage from './pages/HomePage'                    // тот самый пустой лист

export default function App() {
  // checking = true первые доли секунды после открытия страницы: GET /auth/me ещё в пути.
  // Без этой паузы залогиненный пользователь увидел бы мигание «сначала login, потом home».
  const { checking } = useAuth()
  if (checking) {
    return (                                   // пока проверка не закончилась — показываем заглушку
      <div className="page"><p>Загрузка...</p></div> // и НИКАКИХ редиректов: маршрут ещё не решён
    )
  }

  return (
    <>                                          {/* фрагмент: склеиваем шапку и контент без лишнего div */}
      <Header />                                {/* живёт над всеми страницами — кнопки видны всегда */}
      <Routes>                                  {/* дальше: один из четырёх маршрутов совпадёт с адресом */}
        <Route path="/" element={<HomePage />} />              {/* главная — открыта всем */}
        <Route path="/login" element={<LoginPage />} />        {/* вход — открыт всем */}
        <Route path="/register" element={<RegisterPage />} />  {/* регистрация — открыта всем */}
        <Route path="*" element={<Navigate to="/" replace />} /> {/* звёздочка = «ничего не совпало»: уезжаем на главную */}
      </Routes>                                 {/* replace = не оставлять битый адрес в истории «назад» */}
    </>
  )
}
