import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The Python backend and virtualenvs live in this repo; do not watch them.
    watch: {
      ignored: ['**/backend/**', '**/backend_env/**', '**/dist/**'],
    },
    proxy: {
      '/api': {
        // Override to point the dev server at another backend, e.g. a test instance.
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
