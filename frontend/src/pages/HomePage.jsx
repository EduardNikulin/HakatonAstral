// Блок: главная страница — тот самый «пустой лист». Контента пока нет, но она уже знает,
// кто перед ней: шапка (Header) рисует либо кнопки войти/зарегистрироваться, либо имя.
import { useAuth } from '../context/AuthContext' // текущий пользователь или null

export default function HomePage() {
  const { user } = useAuth()                 // достаём профиль из общей коробки
  return (
    <main className="page page-home">        // та же центрирующая колонка (+класс для главной)
      {user ? (                              // залогинен: встречаем по имени
        <p className="welcome">
          Это HakatonAstral. Добро пожаловать, {user.display_name || user.username}!
          {/* display_name заполняется в профиле; пока null — показываем username (оператор || = «или») */}
        </p>
      ) : (                                  // гость: минимальная заглушка на пустом листе
        <p className="welcome welcome-guest">
          Здесь будет игра. <br />
          Войдите или зарегистрируйтесь, чтобы начать.
          {/* две кнопки уже висят в правом верхнем углу (Header) — здесь их дублировать не нужно */}
        </p>
      )}
    </main>
  )
}
