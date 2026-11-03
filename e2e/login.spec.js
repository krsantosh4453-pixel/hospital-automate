import { expect, test } from "@playwright/test"
import { signIn, signInAs } from "./helpers.js"

test("receptionist signs in and lands on the home page of their hospital", async ({ page }) => {
  await signInAs(page, "demo.desk.main")

  await expect(page.getByText("Demo City Hospital").first()).toBeVisible()
})

test("wrong password keeps the user on the sign-in page", async ({ page }) => {
  await signIn(page, "demo.desk.main", "not-the-password")

  await expect(page).toHaveURL(/\/staff-login$/)
  await expect(page.getByText(/invalid|incorrect|failed/i).first()).toBeVisible()
})

test("signed-out visitor is sent away from a staff page", async ({ page }) => {
  await page.goto("/billing")

  await expect(page).not.toHaveURL(/\/billing$/)
})
