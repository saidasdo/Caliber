import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Backend runs separately (`npm run api`, port 8000); proxied here so the browser
      // only ever talks to the Vite origin, avoiding CORS and hardcoded hosts.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
