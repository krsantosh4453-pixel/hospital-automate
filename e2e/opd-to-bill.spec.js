import { expect, test } from "@playwright/test"
import { hospitalToday, signInAs, uniqueName } from "./helpers.js"

// One OPD patient through the browser, each step by its own role:
// front desk books and issues the token, the doctor sees the patient,
// billing raises the bill and takes full payment.
test.describe.configure({ mode: "serial" })

const patient = uniqueName("E2E Patient")
const DOCTOR = "Dr Asha Mehta"

test("front desk books an appointment", async ({ page }) => {
  await signInAs(page, "demo.desk.main")
  await page.goto("/appointments")

  await page.getByRole("button", { name: "New appointment" }).first().click()
  const form = page.getByRole("dialog")
  await form.getByLabel("Patient name").fill(patient)
  await form.getByLabel("Mobile number").fill("9000004" + String(Date.now()).slice(-3))
  await form.getByLabel("Village / locality").fill("Test Nagar")
  await form.locator("select").selectOption({ label: DOCTOR })
  await form.getByLabel("Date").fill(hospitalToday())
  await form.getByLabel("Time").fill("11:30")
  await form.getByLabel("Reason for visit").fill("Fever")
  await form.getByRole("button", { name: "Book appointment" }).click()

  await expect(form).toBeHidden()
  const row = page.getByRole("row", { name: new RegExp(patient) })
  await expect(row).toBeVisible()
  await expect(row.getByText("Scheduled")).toBeVisible()
})

test("front desk issues the queue token", async ({ page }) => {
  await signInAs(page, "demo.desk.main")
  await page.goto("/queue")

  // Issue token serves booked appointments in order; seed data may be ahead of ours.
  const row = page.getByRole("row", { name: new RegExp(patient) })
  const issue = page.getByRole("button", { name: /^Issue token/ })
  for (let attempt = 0; attempt < 5 && !(await row.isVisible()); attempt += 1) {
    await issue.click()
    await expect(page.getByText(/Token #\d+ generated/)).toBeVisible()
  }
  await expect(row).toBeVisible()
  await expect(row.getByText("Waiting")).toBeVisible()
})

test("doctor calls, sees and completes the patient", async ({ page }) => {
  await signInAs(page, "demo.doctor1")
  await page.goto("/queue")

  const row = page.getByRole("row", { name: new RegExp(patient) })
  await row.getByRole("button", { name: "Call" }).click()
  await row.getByRole("button", { name: "Start consultation" }).click()
  await expect(row.getByText("In Consultation")).toBeVisible()
  await row.getByRole("button", { name: "Complete" }).click()
  await expect(row.getByText("Completed")).toBeVisible()
})

async function billAndPayInFull(page, username) {
  await signInAs(page, username)
  await page.goto("/billing")

  await page.getByRole("button", { name: "Create invoice" }).click()
  await page.getByPlaceholder("Rahul Kumar").fill(patient)
  await page.getByPlaceholder("P001").fill("P000")
  await page.getByPlaceholder("Doctor Consultation ₹").fill("300")
  await page.getByPlaceholder("Pharmacy / Medicines ₹").fill("25")
  await page.locator("input[name=paid]").fill("325")
  await page.locator("select[name=payment]").selectOption("Cash")
  await page.getByRole("button", { name: "Generate Bill" }).click()

  const row = page.getByRole("row", { name: new RegExp(patient) })
  await expect(row).toBeVisible()
  await expect(row.getByText("Paid", { exact: true })).toBeVisible()
}

test("billing staff raise the bill and take full payment", async ({ page }) => {
  await billAndPayInFull(page, "demo.billing")
})
