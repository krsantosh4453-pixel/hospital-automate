/* global process */
import { defineConfig, devices } from "@playwright/test"
import { E2E_PASSWORD } from "./e2e/helpers.js"

// Browser tests against a throwaway backend (config/settings/e2e.py) seeded
// with the synthetic Demo City Hospital. E2E_PYTHON picks the interpreter
// (default backend/venv). Run: npx playwright install chromium (once), then
// npm run test:e2e. Both servers start fresh; stop anything on 8020/5185.
const PYTHON = process.env.E2E_PYTHON || "venv/bin/python"
const DB_PATH = process.env.E2E_DB_PATH || "e2e.sqlite3"
const BACKEND_PORT = 8020
const FRONTEND_PORT = 5185

export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: [
        `rm -f ${DB_PATH}`,
        `${PYTHON} manage.py migrate -v0`,
        `${PYTHON} manage.py seed_demo --password ${E2E_PASSWORD}`,
        `${PYTHON} manage.py runserver 127.0.0.1:${BACKEND_PORT} --noreload`,
      ].join(" && "),
      cwd: "backend",
      env: { DJANGO_SETTINGS_MODULE: "config.settings.e2e", E2E_DB_PATH: DB_PATH },
      url: `http://127.0.0.1:${BACKEND_PORT}/health/live/`,
      timeout: 180000,
      reuseExistingServer: false,
    },
    {
      command: `npx vite --port ${FRONTEND_PORT} --strictPort`,
      env: {
        VITE_PROXY_TARGET: `http://127.0.0.1:${BACKEND_PORT}`,
        VITE_DEV_AUTH_BYPASS: "false",
        VITE_AUTH_REQUIRED: "true",
      },
      url: `http://localhost:${FRONTEND_PORT}`,
      timeout: 60000,
      reuseExistingServer: false,
    },
  ],
})
