import { expect, test } from "@playwright/test"
import { E2E_PASSWORD, readOtp, uniqueName, uniquePhone } from "./helpers.js"

const PATIENT_EMAIL = "demo.patient@example.test"
const PATIENT_NAME = "Demo Portal Patient"

async function patientSignsIn(page) {
  await page.goto("/patient-login")
  await page.getByRole("tab", { name: "Email" }).click()
  await page.getByLabel("Email").first().fill(PATIENT_EMAIL)
  await page.getByLabel("Password").fill(E2E_PASSWORD)
  await page.getByRole("button", { name: "Sign In" }).click()
  await expect(page).toHaveURL(/\/patient$/)
}

async function familyMemberSignsIn(page, phone) {
  await page.goto("/patient-login")
  await page.getByRole("tab", { name: "Family" }).click()
  await page.getByLabel("Your mobile number").fill(phone)
  await page.getByRole("button", { name: "Send OTP" }).click()
  await page.getByLabel("6-Digit OTP Code").fill(await readOtp(phone))
  await page.getByRole("button", { name: "Verify & Continue" }).click()
}

test("patient gives a family member view-only access and can take it back", async ({ browser }) => {
  const relative = uniqueName("Family Member")
  const phone = uniquePhone()

  // The patient adds the family member.
  const patientPage = await (await browser.newContext()).newPage()
  await patientSignsIn(patientPage)
  await patientPage.goto("/patient/consent")
  await patientPage.getByLabel("Name").fill(relative)
  await patientPage.getByLabel("Relationship").fill("Son")
  await patientPage.getByLabel("Their mobile number").fill(phone)
  await patientPage.getByRole("button", { name: "Give access" }).click()
  const row = patientPage.getByRole("listitem").filter({ hasText: relative })
  await expect(row).toBeVisible()

  // The family member signs in with their own number and sees the patient's records, read-only.
  const familyContext = await browser.newContext()
  const familyPage = await familyContext.newPage()
  await familyMemberSignsIn(familyPage, phone)
  await expect(familyPage).toHaveURL(/\/patient$/)
  await expect(familyPage.getByText(/View only: you cannot sign, upload, share or change anything/)).toBeVisible()
  await expect(familyPage.getByText(PATIENT_NAME).first()).toBeVisible()

  // A family member cannot manage access themselves.
  await familyPage.goto("/patient/consent")
  await expect(familyPage.getByRole("button", { name: "Give access" })).toHaveCount(0)

  const readProfile = () =>
    familyPage.evaluate(async () => (await fetch("/api/auth/patient/me/", { credentials: "include" })).status)
  expect(await readProfile()).toBe(200)

  // The patient removes access; the family member's session stops working at once.
  await row.getByRole("button", { name: "Remove access" }).click()
  await patientPage.getByRole("dialog").getByRole("button", { name: "Remove access" }).click()
  await expect(patientPage.getByText(`${relative} no longer has access.`)).toBeVisible()

  expect([401, 403]).toContain(await readProfile())
})

test("an unknown number gets the same answer and cannot sign in", async ({ page }) => {
  const phone = uniquePhone()

  await page.goto("/patient-login")
  await page.getByRole("tab", { name: "Family" }).click()
  await page.getByLabel("Your mobile number").fill(phone)
  await page.getByRole("button", { name: "Send OTP" }).click()
  await page.getByLabel("6-Digit OTP Code").fill("123456")
  await page.getByRole("button", { name: "Verify & Continue" }).click()

  await expect(page.getByText(/invalid/i).first()).toBeVisible()
  await expect(page).not.toHaveURL(/\/patient$/)
})
