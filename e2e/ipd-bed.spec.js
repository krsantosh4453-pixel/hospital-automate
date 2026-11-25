import { expect, test } from "./fixtures.js"
import { pickPatient, signInAs } from "./helpers.js"

// seed_demo fills every bed, so the admin adds one; a doctor admits an OPD
// patient (only a doctor of the hospital, admitting as themself, may) and the
// admin gives them that bed.
const PATIENT = "Demo Ravi (Cardiology OPD)"
const BED = `E2E-${Date.now().toString(36).toUpperCase()}`

async function pickOption(select, text) {
  const value = await select.locator("option", { hasText: text }).first().getAttribute("value")
  await select.selectOption(value)
}

test("admin adds a bed, a doctor admits a patient and the admin allocates the bed", async ({ browser }) => {
  // Two sign-ins (admin and doctor), like the laboratory test.
  test.setTimeout(60000)
  const page = await (await browser.newContext()).newPage()
  await signInAs(page, "demo.admin")
  await page.goto("/ipd")

  await page.getByRole("button", { name: "Add bed" }).first().click()
  const addBed = page.getByRole("dialog", { name: "Add bed" })
  await addBed.getByPlaceholder("B-1").fill(BED)
  await addBed.getByRole("button", { name: "Add bed" }).click()
  await expect(page.getByText(`Bed ${BED} added`)).toBeVisible()

  const doctor = await (await browser.newContext()).newPage()
  await signInAs(doctor, "demo.doctor1")
  await doctor.goto("/ipd")
  await doctor.getByRole("button", { name: "New admission" }).first().click()
  const admit = doctor.getByRole("dialog", { name: "New admission" })
  await pickPatient(admit, PATIENT)
  await pickOption(admit.locator("select").first(), "Dr Asha Mehta")
  await admit.locator("textarea").fill("Chest pain, observation")
  await admit.getByRole("button", { name: "Admit patient" }).click()
  await expect(admit).toBeHidden()

  await page.reload()
  // Adding a bed leaves the page on "All beds"; admissions have their own tab.
  await page.getByRole("tab", { name: /Admissions/ }).click()
  const row = page.getByRole("row", { name: new RegExp(PATIENT.replace(/[()]/g, "\\$&")) })
  await expect(row.getByText("No bed")).toBeVisible()
  await row.getByRole("button", { name: "Allocate bed" }).click()

  const allocate = page.getByRole("dialog", { name: "Allocate bed" })
  await pickOption(allocate.locator("select"), `Bed ${BED}`)
  await allocate.getByRole("button", { name: "Allocate" }).click()
  await expect(allocate).toBeHidden()
  await expect(page.getByText("Bed allocated")).toBeVisible()

  // The list reloads in the background after the dialog closes; slower when the whole suite runs.
  await expect(row.getByText(BED)).toBeVisible({ timeout: 15000 })
  await expect(row.getByRole("button", { name: "Release bed" })).toBeVisible()
})
