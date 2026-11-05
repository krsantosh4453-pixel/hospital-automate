import { expect, test } from "@playwright/test"
import { signInAs } from "./helpers.js"

// H4: billing staff take an advance, adjust it against a bill and refund
// what is left. The bill is raised through the API with the same session.
const PATIENT = "Demo Kiran (Ward A)"

test("advance is received, adjusted against a bill and the rest refunded", async ({ page }) => {
  await signInAs(page, "demo.billing")
  const api = page.request
  const csrf = (await (await api.get("/api/auth/csrf/")).json()).csrfToken
  const found = await (await api.get(`/api/patients/?search=${encodeURIComponent("Demo Kiran")}`)).json()
  const patient = (found.results || found).find((p) => p.name === PATIENT)
  const headers = { "X-CSRFToken": csrf, "X-Hospital-ID": String(patient.hospital) }

  await page.goto("/billing")
  await expect(page.getByRole("heading", { name: "Advance payments" })).toBeVisible()
  await page.getByRole("button", { name: "Receive advance" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByPlaceholder("Search by name, phone or UHID").fill("Demo Kiran")
  await dialog.getByRole("button", { name: new RegExp(PATIENT.replace(/[()]/g, "\\$&")) }).click()
  await dialog.getByLabel(/^Amount/).fill("1000")
  await dialog.getByRole("button", { name: "Save" }).click()
  await expect(dialog).toBeHidden()
  // The advance row (it expands to show the history), not the patient's bill rows.
  const row = page.getByRole("row", { name: new RegExp(PATIENT.replace(/[()]/g, "\\$&")) })
    .filter({ has: page.locator("button[aria-expanded]") })
  await expect(row).toContainText("₹1,000.00")

  const created = await api.post("/api/billing/invoices/", {
    headers,
    data: { hospital: patient.hospital, patient: patient.id, discount: 0,
            items_data: [{ description: "Room charge E2E", quantity: 1, unit_price: "400.00" }] },
  })
  expect(created.status()).toBe(201)
  const invoice = await created.json()

  await row.getByRole("button", { name: "Adjust against bill" }).click()
  await dialog.getByLabel(/^Bill/).selectOption(String(invoice.id))
  await dialog.getByLabel(/^Amount/).fill("400")
  await dialog.getByRole("button", { name: "Save" }).click()
  await expect(dialog).toBeHidden()
  await expect(row).toContainText("₹600.00")
  expect((await (await api.get(`/api/billing/invoices/${invoice.id}/`)).json()).status).toBe("Paid")

  await row.getByRole("button", { name: "Refund" }).click()
  await dialog.getByLabel(/^Amount/).fill("600")
  await dialog.getByLabel(/^Reason/).fill("Discharged, unused advance")
  await dialog.getByRole("button", { name: "Save" }).click()
  await expect(dialog).toBeHidden()
  await expect(row).toContainText("₹0.00")
})
