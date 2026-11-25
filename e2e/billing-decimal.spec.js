import { expect, test } from "@playwright/test"
import { E2E_PASSWORD, pickPatient, signInAs } from "./helpers.js"

// BUG-002 (E2E audit 2026-11-24): a bill with paise (₹33.60) could not be
// paid in full because the payment field took whole rupees only.
// Bills are raised through the API, paid through the real billing page.

const PATIENT = "Demo Portal Patient"
const PATIENT_EMAIL = "demo.patient@example.test"
const SHOTS = "reports/e2e-evidence"

test.describe.configure({ mode: "serial" })

const escape = (text) => text.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&")

async function session(page) {
  const csrf = (await (await page.request.get("/api/auth/csrf/")).json()).csrfToken
  // The header picks the hospital once its list has loaded, a moment after sign-in.
  await page.waitForFunction(() => localStorage.getItem("selectedHospital"))
  const hospital = await page.evaluate(() => JSON.parse(localStorage.getItem("selectedHospital")).id)
  const found = await (await page.request.get(`/api/patients/?hospital=${hospital}&search=${encodeURIComponent(PATIENT)}`)).json()
  const patient = (found.results || found).find((p) => p.name === PATIENT)
  return { csrf, hospital, patient: patient.id }
}

/** A bill of one synthetic line, priced by the server (GST included). */
async function raiseBill(page, s, unitPrice, taxRate = "0.00") {
  const response = await page.request.post(`/api/billing/invoices/?hospital=${s.hospital}`, {
    headers: { "X-CSRFToken": s.csrf, "X-Hospital-ID": String(s.hospital) },
    data: { patient: s.patient, items_data: [{ description: "Synthetic decimal service", quantity: 1, unit_price: unitPrice, tax_rate: taxRate }] },
  })
  expect(response.status(), await response.text()).toBe(201)
  return response.json()
}

async function stateOf(page, id) {
  const data = await (await page.request.get(`/api/billing/invoices/${id}/`)).json()
  return { status: data.status, total: data.total_amount, paid: data.total_paid, due: data.balance_due }
}

const rowOf = (page, invoice) => page.getByRole("row", { name: new RegExp(escape(invoice.invoice_number)) })

/** The cashier sets the bill's total amount paid on the Payment form. */
async function enterPaid(page, invoice, amount) {
  await rowOf(page, invoice).getByRole("button", { name: "Payment" }).click()
  await page.locator("input[name=paid]").fill(amount)
  await page.locator("select[name=payment]").selectOption("Cash")
  await page.getByRole("button", { name: "Save Changes" }).click()
}

test("a ₹33.60 bill is paid in full with exactly ₹33.60 (TEST 1)", async ({ page }) => {
  await signInAs(page, "demo.billing")
  const s = await session(page)
  const bill = await raiseBill(page, s, "30.00", "12.00")
  expect((await stateOf(page, bill.id)).total).toBe("33.60")

  await page.goto("/billing")
  await enterPaid(page, bill, "33.60")

  await expect(page.getByText("Payment recorded.")).toBeVisible()
  await expect(rowOf(page, bill)).toContainText("₹0.00")
  await expect(rowOf(page, bill)).not.toContainText("Partially")
  expect(await stateOf(page, bill.id)).toEqual({ status: "Paid", total: "33.60", paid: "33.60", due: "0.00" })

  await page.reload()
  await expect(rowOf(page, bill)).toContainText("₹33.60")
  await expect(rowOf(page, bill)).toContainText("₹0.00")
  await page.screenshot({ path: `${SHOTS}/billing-1-paid-33.60.png` })
})

test("a partial ₹10.25 payment leaves ₹90.25, then the rest pays it off (TEST 2, 3)", async ({ page }) => {
  await signInAs(page, "demo.billing")
  const s = await session(page)
  const bill = await raiseBill(page, s, "100.50")

  await page.goto("/billing")
  await enterPaid(page, bill, "10.25")
  await expect(rowOf(page, bill)).toContainText("Partially Paid")
  await expect(rowOf(page, bill)).toContainText("₹90.25")
  expect(await stateOf(page, bill.id)).toEqual({ status: "Partially Paid", total: "100.50", paid: "10.25", due: "90.25" })

  await page.reload()
  await expect(rowOf(page, bill)).toContainText("Partially Paid")
  await expect(rowOf(page, bill)).toContainText("₹90.25")
  await page.screenshot({ path: `${SHOTS}/billing-2-partial-10.25.png` })

  // The status filter uses the server's names ("Partial" used to match nothing).
  const statusFilter = page.locator("select").filter({ has: page.locator("option[value='Partially Paid']") })
  await statusFilter.selectOption("Partially Paid")
  await expect(rowOf(page, bill)).toBeVisible()
  await statusFilter.selectOption("Paid")
  await expect(rowOf(page, bill)).toHaveCount(0)
  await statusFilter.selectOption("All Status")

  // The form holds the running total paid: ₹100.50 records the other ₹90.25.
  await enterPaid(page, bill, "100.50")
  await expect(rowOf(page, bill)).toContainText("₹0.00")
  expect(await stateOf(page, bill.id)).toEqual({ status: "Paid", total: "100.50", paid: "100.50", due: "0.00" })
})

test("₹10.999 and ₹33.61 on a ₹33.60 bill are refused and nothing is recorded (TEST 4, 7)", async ({ page }) => {
  await signInAs(page, "demo.billing")
  const s = await session(page)
  const bill = await raiseBill(page, s, "30.00", "12.00")
  await page.goto("/billing")

  for (const amount of ["10.999", "33.61"]) {
    await enterPaid(page, bill, amount)
    // Refused in the browser (field validity) or by the page before sending.
    const field = page.locator("input[name=paid]")
    const browserRefused = await field.evaluate((el) => el.isConnected && !el.checkValidity()).catch(() => false)
    if (!browserRefused) await expect(page.getByText(/at most 2 decimal places|more than the bill|cannot be greater/)).toBeVisible()
    await page.keyboard.press("Escape")
    await page.goto("/billing")
  }
  expect(await stateOf(page, bill.id)).toEqual({ status: "Unpaid", total: "33.60", paid: "0.00", due: "33.60" })
  const payments = await (await page.request.get(`/api/billing/payments/?hospital=${s.hospital}&invoice=${bill.id}`)).json()
  expect((payments.results || payments).length).toBe(0)
})

test("a bill with paise can be raised on the billing page", async ({ page }) => {
  await signInAs(page, "demo.billing")
  await page.goto("/billing")
  await page.getByRole("button", { name: "Create invoice" }).click()
  await pickPatient(page, PATIENT)
  await page.getByPlaceholder("Other Charges ₹").fill("250.75")
  await page.getByRole("button", { name: "Generate Bill" }).click()
  await expect(page.getByRole("row", { name: /Demo Portal Patient.*₹250\.75/ }).first()).toBeVisible()
})

test("the patient sees a partly paid bill as owing, on the dashboard and the Bills page (TEST 12)", async ({ page, browser }) => {
  await signInAs(page, "demo.billing")
  const s = await session(page)
  const bill = await raiseBill(page, s, "30.00", "12.00")
  const paid = await page.request.post(`/api/billing/payments/?hospital=${s.hospital}`, {
    headers: { "X-CSRFToken": s.csrf, "X-Hospital-ID": String(s.hospital) },
    data: { invoice: bill.id, amount: "10.25", payment_method: "Cash" },
  })
  expect(paid.status()).toBe(201)

  const patientPage = await (await browser.newContext()).newPage()
  await patientPage.goto("/patient-login")
  await patientPage.getByRole("tab", { name: "Email" }).click()
  await patientPage.getByLabel("Email").first().fill(PATIENT_EMAIL)
  await patientPage.getByLabel("Password").fill(E2E_PASSWORD)
  await patientPage.getByRole("button", { name: "Sign In" }).click()
  await expect(patientPage).toHaveURL(/\/patient$/)

  const mine = await (await patientPage.request.get("/api/billing/invoices/")).json()
  const owing = (mine.results || mine).filter((i) => ["Unpaid", "Partially Paid"].includes(i.status) && Number(i.balance_due) > 0)
  expect(owing.some((i) => i.id === bill.id)).toBe(true)
  await expect(patientPage.locator("main")).toContainText(new RegExp(`Bills with balance due\\s*${owing.length}(?!\\d)`))
  await patientPage.screenshot({ path: `${SHOTS}/billing-3-patient-dashboard.png` })

  await patientPage.goto("/patient/bills")
  await patientPage.getByRole("radio", { name: "Balance due" }).click()
  await expect(patientPage.locator("main")).toContainText(bill.invoice_number)
  await expect(patientPage.locator("main")).toContainText("₹23.35")
})
