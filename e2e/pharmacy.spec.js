import { expect, test } from "@playwright/test"
import { signInAs } from "./helpers.js"

// The pharmacist stocks a medicine and keeps the pharmacy page open; a doctor
// then prescribes it, and the pharmacist finds and dispenses that prescription.
// The page is opened first on purpose: the lookup must ask the server.
const MEDICINE = `Tab Cetirizine 10 E2E${Date.now().toString(36).toUpperCase()}`
const PATIENT = "Demo Ravi (Cardiology OPD) (9000003011)"

async function addMedicine(page) {
  await page.getByRole("button", { name: "Add medicine" }).click()
  const form = page.locator("main")
  await form.getByRole("textbox", { name: "Medicine Name" }).fill(MEDICINE)
  await form.getByRole("textbox", { name: "Salt (generic name)" }).fill("cetirizine")
  await form.locator("select").filter({ hasText: "Select Category" }).selectOption("Tablet")
  await form.getByRole("textbox", { name: "Batch Number" }).fill("B-E2E-1")
  await form.getByRole("spinbutton", { name: "Stock Quantity" }).fill("50")
  await form.locator("input[type=month]").fill("2028-12")
  await form.getByRole("spinbutton", { name: "Price" }).fill("4")
  await form.getByRole("button", { name: "Add Medicine", exact: true }).click()
}

function stockCell(page) {
  return page.getByRole("row", { name: new RegExp(MEDICINE) }).getByRole("cell").nth(3)
}

test("pharmacist dispenses a prescription written after the page opened", async ({ browser }) => {
  const pharmacist = await (await browser.newContext()).newPage()
  await signInAs(pharmacist, "demo.pharmacist")
  await pharmacist.goto("/pharmacy")
  await addMedicine(pharmacist)
  await expect(stockCell(pharmacist)).toHaveText("50")

  const doctor = await (await browser.newContext()).newPage()
  await signInAs(doctor, "demo.doctor1")
  await doctor.goto("/prescription")
  await doctor.getByLabel(/^Patient/).selectOption({ label: PATIENT })
  await doctor.getByPlaceholder("Drug and strength").first().fill(MEDICINE)
  await doctor.getByLabel("Qty").first().fill("3")
  await doctor.getByRole("button", { name: "Save prescription" }).click()
  const saved = doctor.getByText(/Prescription RX-\d+ created successfully/)
  await expect(saved).toBeVisible()
  const rx = (await saved.textContent()).match(/RX-\d+/)[0]

  await pharmacist.getByPlaceholder("RX-2026-001").fill(rx)
  await pharmacist.getByRole("button", { name: "Search Prescription" }).click()
  await expect(pharmacist.getByText("Required: 3")).toBeVisible()
  await pharmacist.getByRole("button", { name: "Dispense Prescription" }).click()

  await expect(pharmacist.getByText(`Prescription ${rx} dispensed successfully.`)).toBeVisible()
  await expect(stockCell(pharmacist)).toHaveText("47")

  // Looked up again later, it shows as dispensed and cannot be dispensed twice.
  await pharmacist.reload()
  await pharmacist.getByPlaceholder("RX-2026-001").fill(rx)
  await pharmacist.getByRole("button", { name: "Search Prescription" }).click()
  await expect(pharmacist.getByText("Dispensed", { exact: true })).toBeVisible()
  await expect(pharmacist.getByRole("button", { name: "Dispense Prescription" })).toHaveCount(0)
})

test("an unknown prescription number is reported, not dispensed", async ({ page }) => {
  await signInAs(page, "demo.pharmacist")
  await page.goto("/pharmacy")
  await page.getByPlaceholder("RX-2026-001").fill("RX-999999")
  await page.getByRole("button", { name: "Search Prescription" }).click()
  await expect(page.getByText("Prescription not found for this hospital.")).toBeVisible()
  await expect(page.getByRole("button", { name: "Dispense Prescription" })).toHaveCount(0)
})
