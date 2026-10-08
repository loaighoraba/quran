import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development the API runs separately (uv run fastapi dev); in production FastAPI serves
// the built files itself, so the app always calls the API on its own origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/stats': 'http://127.0.0.1:8000',
    },
  },
})
