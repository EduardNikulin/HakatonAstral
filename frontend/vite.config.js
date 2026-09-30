// Блок: конфигурация сборщика Vite — что запускается, на каком порту, как обрабатывается JSX.
import { defineConfig } from 'vite'          // helper от Vite: даёт автодополнение и проверку настроек
import react from '@vitejs/plugin-react'     // плагин: умеет превращать JSX (HTML-внутри-JS) в обычный JS

// export default — Vite читает этот файл при запуске `npm run dev` / `npm run build`.
export default defineConfig({
  plugins: [react()],                        // подключаем обработку React-файлов (.jsx)
  server: {
    port: 5173,                              // фиксированный порт: должен совпадать со списком CORS на бэке
    strictPort: true,                        // если 5173 занят — упасть с ошибкой, а не молча взять 5174 (иначе CORS сломается)
  },
})
