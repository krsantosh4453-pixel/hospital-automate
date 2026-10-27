/* global process */
import { expect } from "@playwright/test"

// Every seed_demo login shares this password (see playwright.config.js).
export const E2E_PASSWORD = process.env.E2E_PASSWORD || "e2e-demo-password"

/** Sign in through the real staff form. */
export async function signIn(page, username, password = E2E_PASSWORD) {
  await page.goto("/staff-login")
  await page.getByLabel("Username or email").fill(username)
  await page.locator("input[type=password]").fill(password)
  await page.locator("input[type=password]").press("Enter")
}

/** Sign in and wait until the staff home page has loaded. */
export async function signInAs(page, username) {
  await signIn(page, username)
  await expect(page).toHaveURL("/")
}

/** A name no earlier run has used, so each test works on its own records. */
export function uniqueName(prefix) {
  return `${prefix} ${Date.now().toString(36).toUpperCase()}`
}

/** Today as YYYY-MM-DD in the hospital's time zone (India). */
export function hospitalToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date())
}
