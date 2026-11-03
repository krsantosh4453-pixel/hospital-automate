import { expect, test } from "@playwright/test"
import { signInAs } from "./helpers.js"

// seed_demo fills every bed, so the admin adds one, admits an OPD patient
// and gives them that bed.
const PATIENT = "Demo Ravi (Cardiology OPD)"
const BED = `E2E-${Date.now().toString(36).toUpperCase()}`

async function pickOption(select, text) {
  const value = await select.locator("option", { hasText: text }).first().getAttribute("value")
  await select.selectOption(value)
}

test("admin adds a bed, admits a patient and allocates the bed", async ({ page }) => {
  await signInAs(page, "demo.admin")
  await page.goto("/ipd")

  await page.getByRole("button", { name: "Add bed" }).first().click()
  const addBed = page.getByRole("dialog", { name: "Add bed" })
  await addBed.getByPlaceholder("B-1").fill(BED)
  await addBed.getByRole("button", { name: "Add bed" }).click()
  await expect(page.getByText(`Bed ${BED} added`)).toBeVisible()

  await page.getByRole("button", { name: "New admission" }).first().click()
  const admit = page.getByRole("dialog", { name: "New admission" })
  const [patientSelect, doctorSelect] = [admit.locator("select").nth(0), admit.locator("select").nth(1)]
  await pickOption(patientSelect, PATIENT)
  await pickOption(doctorSelect, "Dr Asha Mehta")
  await admit.locator("textarea").fill("Chest pain, observation")
  await admit.getByRole("button", { name: "Admit patient" }).click()
  await expect(admit).toBeHidden()

  // Adding a bed leaves the page on "All beds"; admissions have their own tab.
  await page.getByRole("tab", { name: /Admissions/ }).click()
  const row = page.getByRole("row", { name: new RegExp(PATIENT.replace(/[()]/g, "\\$&")) })
  await expect(row.getByText("No bed")).toBeVisible()
  await row.getByRole("button", { name: "Allocate bed" }).click()

  const allocate = page.getByRole("dialog", { name: "Allocate bed" })
  await pickOption(allocate.locator("select"), `Bed ${BED}`)
  await allocate.getByRole("button", { name: "Allocate" }).click()
  await expect(allocate).toBeHidden()

  await expect(row.getByText(BED)).toBeVisible()
  await expect(row.getByRole("button", { name: "Release bed" })).toBeVisible()
})
