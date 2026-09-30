// Блок: AuthContext — глобальное состояние «кто в системе».
//
// Идея без терминов: React умеет хранить данные ТОЛЬКО внутри одного компонента.
// Но «текущий пользователь» нужен и шапке, и страницам, и маршрутизатору.
// Context — это способ положить одни данные в общую коробку на всё дерево компонентов
// и доставать их оттуда хуком useAuth() в любом месте, не протаскивая через аргументы.
import { createContext, useContext, useEffect, useState } from 'react'
// createContext — сделать саму коробку; useContext — достать из неё;
// useState — переменная-состояние (меняешь -> экран перерисовывается);
// useEffect — «выполни код после появления компонента на экране».
import { fetchMe, getToken } from '../services/api' // наш HTTP-клиент: проверка сессии + чтение токена

// Создаём контекст со значением по умолчанию null («коробка ещё не открыта»).
const AuthContext = createContext(null)

// Провайдер — единственный компонент, который ДЕРЖИТ данные пользователя и раздаёт их детям.
// В main.jsx он обернёт вокруг всего приложения.
export function AuthProvider({ children }) {
  // children — это весь остальной интерфейс внутри <AuthProvider>...</AuthProvider>.

  // user: объект профиля ({username, role, display_name,...}) или null (не вошли).
  const [user, setUser] = useState(null)
  // checking: true, пока идёт первая проверка «жив ли вход». Нужен, чтобы не мигать
  // редиректом на /login у уже залогиненного пользователя до ответа бэка.
  const [checking, setChecking] = useState(true)

  // Эффект с пустым массивом зависимостей [] выполняется ОДИН раз при старте приложения.
  // Сценарий: пользователь перезагрузил страницу — токен остался в localStorage, но user=null.
  // Восстанавливаем профиль одним запросом GET /auth/me.
  useEffect(() => {
    if (!getToken()) {
      // Токена нет — проверять нечего, сразу «не авторизован», выходим из режима проверки.
      setChecking(false)
      return                                  // прекращаем выполнение эффекта (return без тела = ничего не делаем дальше)
    }
    fetchMe()                                 // спрашиваем бэк: «чей это токен?»
      .then((data) => setUser(data))         // 200 OK -> положили профиль в состояние -> все компоненты увидят пользователя
      .catch(() => setUser(null))            // 401 (токен протух/подделан) -> считаем что не авторизованы
      .finally(() => setChecking(false))     // в любом случае: проверка закончена, можно показывать страницы
  }, [])                                     // [] = запускать только один раз при монтировании

  // loginAction: вызывается со страницы входа ПОСЛЕ успешного логина.
  // Принимает готовый профиль — страница сама сходит на /auth/me и передаёт его сюда.
  const loginAction = (profile) => setUser(profile)

  // logoutAction: «выйти» = забыть пользователя. Сам токен удаляет страница (clearToken),
  // здесь мы лишь чистим состояние — интерфейсы тут же перерисуются в гостевой режим.
  const logoutAction = () => setUser(null)

  // Всё, что получат дети через useAuth(): данные + функции для их изменения.
  const value = { user, checking, loginAction, logoutAction }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  // Provider — та самая «раздача»: любой компонент внутри видит value.
}

// Хук-шпаргалка: как правильно достать контекст (и подсказка, если забыл обернуть в Provider).
export function useAuth() {
  const ctx = useContext(AuthContext)        // достаём value из ближайшего Provider
  if (ctx === null) {
    // Это значит: где-то вызвали useAuth(), но приложение НЕ обёрнуто в <AuthProvider>.
    throw new Error('useAuth должен вызываться внутри <AuthProvider>') // явная ошибка лучше тихого undefined
  }
  return ctx
}
