// Блок: точка входа всего фронтенда. Браузер стартует именно отсюда (см. index.html).
// Здесь мы «вкручиваем» React-приложение в пустой <div id="root"> на странице.
import React from 'react'                       // сам React нужен для работы хуков и классических сборок
import ReactDOM from 'react-dom/client'         // мост между React и реальной HTML-страницей браузера
import { BrowserRouter } from 'react-router-dom' // читает адресную строку и решает, какой экран показать
import App from './App'                         // наше приложение: список маршрутов и общая разметка
import { AuthProvider } from './context/AuthContext' // коробка с текущим пользователем для всего дерева
import './styles.css'                           // глобальные стили: шапка, карточка, кнопки

ReactDOM.createRoot(document.getElementById('root')).render(
  // createRoot: находим div#root из index.html и говорим React — «твой дом вот здесь».
  <React.StrictMode>           {/* StrictMode: в dev-режиме дважды вызывает эффекты, чтобы ловить баги; на prod не мешает */}
    <BrowserRouter>            {/* включаем работу с URL: /login, /register... без перезагрузки страницы */}
      <AuthProvider>           {/* кладём пользователя в общую коробку ДО того, как дети начнут его читать */}
        <App />                {/* само приложение: роуты + шапка */}
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
