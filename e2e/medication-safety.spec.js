import { expect, test } from "@playwright/test"
import { pickPatient, signInAs } from "./helpers.js"

async function startPrescription(page, ...medicines) {
  await signInAs(page, "demo.doctor1")
  await page.goto("/prescription")
  await pickPatient(page, "Demo Ravi (Cardiology OPD)")
  for (const [index, medicine] of medicines.entries()) {
    if (index > 0) await page.getByRole("button", { name: "Add medicine" }).click()
    await page.getByPlaceholder("Drug and strength").nth(index).fill(medicine)
  }
  await page.getByRole("button", { name: "Save prescription" }).click()
}

test("a prescription with no alerts is saved straight away", async ({ page }) => {
  await startPrescription(page, "Tab Paracetamol 500")

  await expect(page.getByText(/Prescription RX-\d+ created successfully/)).toBeVisible()
  await expect(page.getByRole("dialog")).toHaveCount(0)
})

test("a high-risk interaction needs a written reason before it can be prescribed", async ({ page }) => {
  await startPrescription(page, "Tab Warfarin 5 mg", "Tab Ibuprofen 400")

  const dialog = page.getByRole("dialog")
  await expect(dialog.getByText("High-risk medication alert")).toBeVisible()
  await expect(dialog.getByText(/Raised bleeding risk/)).toBeVisible()
  const prescribe = dialog.getByRole("button", { name: "Prescribe anyway" })
  await expect(prescribe).toBeDisabled()

  await dialog.getByLabel(/^Reason to prescribe anyway/).fill("Two-day course; INR checked today")
  await prescribe.click()

  await expect(page.getByText(/Prescription RX-\d+ created successfully/)).toBeVisible()
})

test("going back keeps the prescription unsaved for changes", async ({ page }) => {
  await startPrescription(page, "Tab Sildenafil 50", "Tab Isosorbide Mononitrate 20")

  await page.getByRole("dialog").getByRole("button", { name: "Go back and change" }).click()

  await expect(page.getByRole("dialog")).toHaveCount(0)
  await expect(page.getByPlaceholder("Drug and strength").first()).toHaveValue("Tab Sildenafil 50")
})
