import { expect, test } from "@playwright/test"
import { pickPatient, signInAs } from "./helpers.js"

// A doctor prescribes for an admitted patient and orders the medicine from
// the IPD screen (only a doctor may); the ward nurse gives the due dose from
// the MAR and it leaves the due list.
const MEDICINE = `Inj Ceftriaxone 1 g E2E${Date.now().toString(36).toUpperCase()}`
const PATIENT = "Demo Kiran (Ward A)"

async function prescribe(page) {
  await page.goto("/prescription")
  await pickPatient(page, PATIENT)
  await page.getByPlaceholder("Drug and strength").first().fill(MEDICINE)
  await page.getByLabel("Dosage").first().fill("1 g")
  await page.getByLabel("Frequency").first().fill("BID")
  await page.getByRole("button", { name: "Save prescription" }).click()
  const saved = page.getByText(/Prescription RX-\d+ created successfully/)
  await expect(saved).toBeVisible()
  return Number((await saved.textContent()).match(/RX-0*(\d+)/)[1])
}

async function orderFromIpd(page) {
  await page.goto("/ipd")
  const admission = page.getByRole("row", { name: new RegExp(PATIENT.replace(/[()]/g, "\\$&")) }).filter({ hasText: "Admitted" }).first()
  await admission.getByRole("button", { name: "Medicines" }).click()
  const dialog = page.getByRole("dialog")
  const medicine = dialog.getByLabel(/^Medicine/)
  const option = medicine.locator("option", { hasText: MEDICINE })
  await option.waitFor({ state: "attached" })
  await medicine.selectOption(await option.getAttribute("value"))
  await dialog.getByLabel(/^Route/).selectOption("IV")
  await dialog.getByRole("button", { name: "Order medicine" }).click()
  // The order lists who ordered it; its first dose is due now.
  await expect(dialog.getByRole("row", { name: new RegExp(MEDICINE) })).toContainText("Active")
}

test("ward nurse gives a due dose from the MAR", async ({ browser }) => {
  const doctor = await (await browser.newContext()).newPage()
  await signInAs(doctor, "demo.doctor1")
  await prescribe(doctor)
  await orderFromIpd(doctor)

  const nurse = await (await browser.newContext()).newPage()
  await signInAs(nurse, "demo.nurse")
  await nurse.goto("/nurses")
  await nurse.getByRole("tablist", { name: "Nursing sections" }).getByRole("tab", { name: "MAR" }).click()

  const row = nurse.getByRole("row", { name: new RegExp(MEDICINE) })
  await expect(row).toContainText(PATIENT)
  await expect(row).toContainText("Due")
  await row.getByRole("button", { name: "Give Medicine" }).click()

  const confirm = nurse.getByRole("dialog", { name: "Please confirm" })
  await expect(confirm).toContainText(`Record ${MEDICINE}`)
  await confirm.getByRole("button", { name: "Confirm" }).click()
  await expect(row).toHaveCount(0)

  // Still gone after a reload: the dose was recorded on the server.
  await nurse.reload()
  await nurse.getByRole("tablist", { name: "Nursing sections" }).getByRole("tab", { name: "MAR" }).click()
  await expect(nurse.getByRole("columnheader", { name: "Medicine" })).toBeVisible()
  await expect(nurse.getByRole("row", { name: new RegExp(MEDICINE) })).toHaveCount(0)
})
