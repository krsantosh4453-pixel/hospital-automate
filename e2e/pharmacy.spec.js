import { expect, test } from "@playwright/test"
import { signInAs } from "./helpers.js"

// The pharmacist stocks a medicine and keeps the pharmacy page open; a doctor
// then prescribes it, and the pharmacist finds and dispenses that prescription.
// The page is opened first on purpose: the lookup must ask the server.
const RUN = Date.now().toString(36).toUpperCase()
const MEDICINE = `Tab Cetirizine 10 E2E${RUN}`
const PAIR = [`Tab Levocetirizine 5 E2E${RUN}`, `Tab Pantoprazole 40 E2E${RUN}`]
const PATIENT = "Demo Ravi (Cardiology OPD) (9000003011)"

async function addMedicine(page, name = MEDICINE, salt = "cetirizine", stock = "50") {
  await page.getByRole("button", { name: "Add medicine" }).click()
  const form = page.getByRole("dialog", { name: "Add Medicine" })
  await form.getByLabel("Medicine Name").fill(name)
  await form.getByLabel("Salt (generic name)").fill(salt)
  await form.getByLabel("Category").selectOption("Tablet")
  await form.getByLabel("Batch Number").fill("B-E2E-1")
  await form.getByLabel("Stock Quantity").fill(stock)
  await form.getByLabel("Expiry (month)").fill("2028-12")
  await form.getByLabel("Price").fill("4")
  await form.getByRole("button", { name: "Add Medicine", exact: true }).click()
  await expect(form).toBeHidden()
}

function stockCell(page, name = MEDICINE) {
  return page.getByRole("row", { name: new RegExp(name) }).getByRole("cell").nth(3)
}

async function prescribe(doctor, lines) {
  await doctor.goto("/prescription")
  await doctor.getByLabel(/^Patient/).selectOption({ label: PATIENT })
  for (const [index, [name, qty]] of lines.entries()) {
    if (index > 0) await doctor.getByRole("button", { name: "Add medicine" }).click()
    await doctor.getByPlaceholder("Drug and strength").nth(index).fill(name)
    await doctor.getByLabel("Qty").nth(index).fill(qty)
  }
  await doctor.getByRole("button", { name: "Save prescription" }).click()
  const saved = doctor.getByText(/Prescription RX-\d+ created successfully/)
  await expect(saved).toBeVisible()
  return (await saved.textContent()).match(/RX-\d+/)[0]
}

test("pharmacist dispenses a prescription written after the page opened", async ({ browser }) => {
  const pharmacist = await (await browser.newContext()).newPage()
  await signInAs(pharmacist, "demo.pharmacist")
  await pharmacist.goto("/pharmacy")
  await addMedicine(pharmacist)
  await expect(stockCell(pharmacist)).toHaveText("50")

  const doctor = await (await browser.newContext()).newPage()
  await signInAs(doctor, "demo.doctor1")
  const rx = await prescribe(doctor, [[MEDICINE, "3"]])

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

test("a prescription with two medicines is dispensed in one step", async ({ browser }) => {
  test.setTimeout(60000)
  const [first, second] = PAIR
  const pharmacist = await (await browser.newContext()).newPage()
  await signInAs(pharmacist, "demo.pharmacist")
  await pharmacist.goto("/pharmacy")
  await addMedicine(pharmacist, first, "levocetirizine", "20")
  await addMedicine(pharmacist, second, "pantoprazole", "30")
  await expect(stockCell(pharmacist, second)).toHaveText("30")

  const doctor = await (await browser.newContext()).newPage()
  await signInAs(doctor, "demo.doctor1")
  const rx = await prescribe(doctor, [[first, "2"], [second, "5"]])

  await pharmacist.getByPlaceholder("RX-2026-001").fill(rx)
  await pharmacist.getByRole("button", { name: "Search Prescription" }).click()
  // Each medicine gets its own batch, chosen for it already.
  await expect(pharmacist.getByLabel(`Stock batch for ${first}`)).not.toHaveValue("")
  await expect(pharmacist.getByLabel(`Stock batch for ${second}`)).not.toHaveValue("")
  await pharmacist.getByRole("button", { name: "Dispense Prescription" }).click()

  await expect(pharmacist.getByText(`Prescription ${rx} dispensed successfully.`)).toBeVisible()
  await expect(stockCell(pharmacist, first)).toHaveText("18")
  await expect(stockCell(pharmacist, second)).toHaveText("25")
})

test("short stock: part now, a same-salt brand for the rest, then a return", async ({ browser }) => {
  test.setTimeout(90000)
  const brand = `Tab Crocin 500 E2E${RUN}`
  const generic = `Tab Dolo 500 E2E${RUN}`
  const pharmacist = await (await browser.newContext()).newPage()
  await signInAs(pharmacist, "demo.pharmacist")
  await pharmacist.goto("/pharmacy")
  await addMedicine(pharmacist, brand, "paracetamol", "2")
  await addMedicine(pharmacist, generic, "paracetamol", "50")
  await expect(stockCell(pharmacist, generic)).toHaveText("50")

  const doctor = await (await browser.newContext()).newPage()
  await signInAs(doctor, "demo.doctor1")
  const rx = await prescribe(doctor, [[brand, "5"]])

  await pharmacist.getByPlaceholder("RX-2026-001").fill(rx)
  await pharmacist.getByRole("button", { name: "Search Prescription" }).click()
  const batch = pharmacist.getByLabel(`Stock batch for ${brand}`)
  // Only 2 of the prescribed brand: give those now.
  await batch.selectOption(await batch.locator("option", { hasText: "2 in stock" }).getAttribute("value"))
  await pharmacist.getByLabel("Give now").fill("2")
  await pharmacist.getByRole("button", { name: "Dispense Prescription" }).click()
  await expect(pharmacist.getByText(`Part of prescription ${rx} dispensed; the rest can be given later.`)).toBeVisible()
  await expect(pharmacist.getByText("Already given: 2 · Still to give: 3")).toBeVisible()

  // The rest from the same-salt brand, with the pharmacist's reason.
  await batch.selectOption(await batch.locator("option", { hasText: generic }).getAttribute("value"))
  await pharmacist.getByLabel(`Why ${generic} instead of ${brand}?`).fill("Prescribed brand out of stock")
  await pharmacist.getByRole("button", { name: "Dispense Prescription" }).click()
  await expect(pharmacist.getByText(`Prescription ${rx} dispensed successfully.`)).toBeVisible()
  await expect(stockCell(pharmacist, generic)).toHaveText("47")

  // The patient brings one sealed strip back.
  await pharmacist.getByPlaceholder("Search patient, medicine or SALE-number").fill(generic)
  const sale = pharmacist.getByRole("row", { name: new RegExp(generic) }).filter({ hasText: `Instead of ${brand}` })
  await sale.getByRole("button", { name: "Return" }).click()
  const dialog = pharmacist.getByRole("dialog", { name: "Return medicine" })
  await dialog.getByLabel(/^Quantity returned/).fill("1")
  await dialog.getByLabel(/^Reason/).fill("Course stopped by doctor")
  await dialog.getByLabel("Sealed and fit to give again: put back in stock").check()
  await dialog.getByRole("button", { name: "Record return" }).click()
  await expect(dialog).toBeHidden()
  await expect(sale.getByRole("cell").nth(4)).toHaveText("1")
  await expect(stockCell(pharmacist, generic)).toHaveText("48")
})
