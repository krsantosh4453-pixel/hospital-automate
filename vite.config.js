/* global process */
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

const BACKEND_TARGET = process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Google Sign-In only accepts the origins registered in Google Cloud
    // (http://localhost:5173). Never drift to another port: fail instead.
    host: 'localhost',
    port: 5173,
    strictPort: true,
    // The Python backend and virtualenvs live in this repo; do not watch them.
    watch: {
      ignored: ['**/backend/**', '**/backend_env/**', '**/dist/**'],
    },
    // One Django backend for every proxied path. Override to point the dev
    // server at another backend, e.g. a test instance (scripts/dev.sh sets it).
    // Vite answers 502 when nothing listens there: start it with scripts/dev.sh.
    proxy: {
      '/api': { target: BACKEND_TARGET, changeOrigin: true },
      // Django's /health/, /health/live/, /health/ready/: lets scripts and
      // developers check the backend through this dev server too.
      '/health': { target: BACKEND_TARGET, changeOrigin: true },
    },
  },
})
