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

/**
 * Choose a patient in a PatientPicker (RL-03): search the "Patient" field by
 * name and click the matching result. ``scope`` is the page or a dialog.
 */
export async function pickPatient(scope, name) {
  await scope.getByLabel(/^Patient/).fill(name)
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  await scope.getByRole("button", { name: new RegExp(escaped) }).first().click()
}

/** A name no earlier run has used, so each test works on its own records. */
export function uniqueName(prefix) {
  return `${prefix} ${Date.now().toString(36).toUpperCase()}`
}

/** Today as YYYY-MM-DD in the hospital's time zone (India). */
export function hospitalToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date())
}

/**
 * The latest console-mode OTP the e2e backend logged for a 10-digit number
 * (config/settings/e2e.py writes those log lines to backend/e2e-otp.log).
 */
export async function readOtp(phone) {
  const { readFile } = await import("node:fs/promises")
  let code = null
  await expect
    .poll(async () => {
      const log = await readFile("backend/e2e-otp.log", "utf8").catch(() => "")
      const matches = [...log.matchAll(new RegExp(`OTP for \\+?9?1?${phone}\\b.*?: (\\d{6})`, "g"))]
      code = matches.length ? matches[matches.length - 1][1] : null
      return code
    })
    .not.toBeNull()
  return code
}

/** A 10-digit mobile number no earlier run has used. */
export function uniquePhone() {
  return `8${Date.now().toString().slice(-9)}`
}
