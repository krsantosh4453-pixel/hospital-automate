/* global Buffer */
import { expect, test } from "./fixtures.js"
import { E2E_PASSWORD, pickPatient, signInAs } from "./helpers.js"

// Prompt 5 against the isolated e2e backend (config.settings.e2e, seed_demo):
// radiology role + images (MF-004/005), order-visit links (INT-002), billing of
// consultation, lab, X-ray and pharmacy (INT-004/MF-011), patient tracking
// (MF-008/009), patient cancel/reschedule (MF-003) and staff storage (SEC-001).
// Synthetic data only; prices are added through the real price-list API.

const SHOTS = "reports/e2e-evidence/prompt-5"
const PATIENT = "Demo Portal Patient"
const DOCTOR = "Dr Asha Mehta"
// 1x1 PNG
const PNG = Buffer.from("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da6364f8ffbf1e0005fe02fea3c2a1b20000000049454e44ae426082", "hex")
const PRICES = { consultation: "500.50", lab: "250.25", imaging: "350.75" }

test.describe.configure({ mode: "serial" })
const shared = {}

async function api(page, method, url, data) {
  const csrf = (await (await page.request.get("/api/auth/csrf/")).json()).csrfToken
  const response = await page.request[method](url, {
    headers: { "X-CSRFToken": csrf, "X-Hospital-ID": "1" }, ...(data === undefined ? {} : { data }),
  })
  return { status: response.status(), body: response.headers()["content-type"]?.includes("json") ? await response.json() : await response.text() }
}
const rows = (body) => (Array.isArray(body) ? body : body.results || [])

async function patientSignsIn(page) {
  await page.goto("/patient-login")
  await page.getByRole("tab", { name: "Email" }).click()
  await page.getByLabel("Email").first().fill("demo.patient@example.test")
  await page.getByLabel("Password").fill(E2E_PASSWORD)
  await page.getByRole("button", { name: "Sign In" }).click()
  await expect(page).toHaveURL(/\/patient$/)
}

test("setup: prices on the list, an open visit for the patient", async ({ page }) => {
  await signInAs(page, "demo.admin")
  for (const [category, code, applies_to, unit_price] of [
    ["consultation", "P5-CON", "", PRICES.consultation],
    ["laboratory", "P5-CBC", "CBC", PRICES.lab],
    ["imaging", "P5-XR-CHEST", "X-ray Chest PA", PRICES.imaging],
  ]) {
    const added = await api(page, "post", "/api/billing/price-list/", {
      hospital: 1, category, code, name: code, applies_to, unit_price, tax_rate: "0" })
    // A retry of this serial group runs setup again: the price from the first try stays.
    const alreadyPriced = added.status === 400 && /already has a price/.test(JSON.stringify(added.body))
    expect(alreadyPriced || added.status === 201, JSON.stringify(added.body)).toBe(true)
  }

  // The admin looks the patient up (a doctor lists only patients in their care).
  const found = rows((await api(page, "get", `/api/patients/?hospital=1&search=${encodeURIComponent(PATIENT)}`)).body)
  shared.patient = found.find((p) => p.name === PATIENT).id
  shared.doctor = rows((await api(page, "get", "/api/doctors/?hospital=1")).body).find((d) => d.name === DOCTOR).id

  await signInAs(page, "demo.doctor1")
  const visit = await api(page, "post", "/api/encounters/visits/", {
    hospital: 1, patient: shared.patient, doctor: shared.doctor, visit_type: "OPD", chief_complaint: "Cough" })
  expect(visit.status, JSON.stringify(visit.body)).toBe(201)
  shared.visit = visit.body.id
  expect((await api(page, "patch", `/api/encounters/visits/${shared.visit}/`, { status: "In Consultation" })).status).toBe(200)
  const diagnosis = await api(page, "post", "/api/clinical/diagnoses/", { visit: shared.visit, name: "Acute bronchitis", icd10_code: "J20.9" })
  expect(diagnosis.status, JSON.stringify(diagnosis.body)).toBe(201)
})

test("doctor orders an X-ray linked to the visit (INT-002)", async ({ page }) => {
  await signInAs(page, "demo.doctor1")
  await page.goto("/radiology")
  await page.getByRole("button", { name: "New imaging order" }).click()
  const dialog = page.getByRole("dialog", { name: "New imaging order" })
  await pickPatient(dialog, PATIENT)
  await expect(dialog.locator("#order-visit")).toHaveValue(String(shared.visit))
  await dialog.getByLabel(/Body part/).fill("Chest PA")
  await dialog.getByLabel(/Clinical question/).fill("Cough for three weeks")
  await page.screenshot({ path: `${SHOTS}/1-order-linked-to-visit.png` })
  await dialog.getByRole("button", { name: "Place order" }).click()
  await expect(dialog).toBeHidden()

  const studies = rows((await api(page, "get", `/api/laboratory/imaging/?patient=${shared.patient}`)).body)
  const study = studies.find((s) => s.body_part === "Chest PA" && s.status === "Ordered")
  expect(study.visit).toBe(shared.visit)
  shared.study = study
})

test("radiology staff see only imaging, perform the study and attach an image (MF-004, MF-005)", async ({ page }) => {
  await signInAs(page, "demo.radiology")
  const nav = page.getByRole("navigation", { name: "Main" })
  await expect(nav.getByRole("link", { name: "Radiology" })).toBeVisible()
  await expect(nav.getByRole("link", { name: "Laboratory" })).toHaveCount(0)
  await expect(nav.getByRole("link", { name: "Billing" })).toHaveCount(0)
  expect((await api(page, "get", "/api/laboratory/")).status).toBe(403)
  expect((await api(page, "get", "/api/billing/invoices/")).status).toBe(403)

  await page.goto("/radiology")
  const row = page.getByRole("row", { name: new RegExp(shared.study.accession_number) })
  await row.getByRole("button", { name: "Performed" }).click()
  await page.getByRole("dialog", { name: "Mark scan performed" }).getByRole("button", { name: "Mark performed" }).click()
  await page.getByRole("tab", { name: /Awaiting report/ }).click()
  await page.getByRole("row", { name: new RegExp(shared.study.accession_number) }).getByRole("button", { name: "Images" }).click()

  const images = page.getByRole("dialog", { name: "Study images" })
  await images.locator(`#study-image-${shared.study.id}`).setInputFiles({ name: "scan.exe", mimeType: "application/octet-stream", buffer: Buffer.from("MZ fake program") })
  await expect(images.getByRole("alert")).toContainText("PNG, JPEG, DICOM")
  await page.screenshot({ path: `${SHOTS}/2-unsafe-file-refused.png` })
  await images.locator(`#study-image-${shared.study.id}`).setInputFiles({ name: "chest-pa.png", mimeType: "image/png", buffer: PNG })
  // The listed file itself (its size line), not the dialog's own description.
  await expect(images.getByRole("listitem")).toHaveCount(1)
  await expect(images.getByRole("listitem")).toContainText("KB")
  await expect(images.getByText("No images attached")).toHaveCount(0)
  await page.screenshot({ path: `${SHOTS}/3-image-attached.png` })

  const listed = (await api(page, "get", `/api/laboratory/imaging/${shared.study.id}/images/`)).body
  expect(listed).toHaveLength(1)
  expect(listed[0].url).toBe(`/api/laboratory/imaging/${shared.study.id}/images/${listed[0].id}/`)
  shared.image = listed[0].id
  // Not reachable without signing in.
  const anonymous = await page.context().browser().newContext()
  expect((await anonymous.request.get(listed[0].url)).status()).toBe(401)
  await anonymous.close()
})

test("doctor signs the report; the X-ray is charged once (MF-011)", async ({ page }) => {
  await signInAs(page, "demo.doctor1")
  await page.goto("/radiology")
  await page.getByRole("tab", { name: /Awaiting report/ }).click()
  await page.getByRole("row", { name: new RegExp(shared.study.accession_number) }).getByRole("button", { name: "Report" }).click()
  const dialog = page.getByRole("dialog", { name: "Report and sign" })
  await dialog.getByLabel(/Findings/).fill("Clear lung fields. No consolidation.")
  await dialog.getByLabel(/Impression/).fill("Normal chest radiograph.")
  await dialog.getByRole("button", { name: "Sign report" }).click()
  await expect(dialog).toBeHidden()
  const again = await api(page, "post", `/api/laboratory/imaging/${shared.study.id}/report/`, { findings: "x", impression: "y" })
  expect(again.status).toBe(400)
})

test("lab test on the same visit is charged once when verified", async ({ page, browser }) => {
  await signInAs(page, "demo.doctor1")
  const ordered = await api(page, "post", "/api/laboratory/", {
    hospital: 1, patient: shared.patient, doctor: shared.doctor, visit: shared.visit, name: "CBC" })
  expect(ordered.status, JSON.stringify(ordered.body)).toBe(201)
  const id = ordered.body.id

  const lab = await (await browser.newContext()).newPage()
  await signInAs(lab, "demo.lab")
  for (const [step, body] of [["collect_sample", {}], ["dispatch_sample", {}], ["receive_sample", {}],
    ["start_processing", {}], ["enter_result", { result_text: "Hb 13.2 g/dL, WBC 7.1" }]]) {
    const done = await api(lab, "post", `/api/laboratory/${id}/${step}/`, body)
    expect(done.status, `${step}: ${JSON.stringify(done.body)}`).toBeLessThan(300)
  }
  // The second check: a different authorised user (SEC-002 policy pending for Admin).
  const admin = await (await browser.newContext()).newPage()
  await signInAs(admin, "demo.admin")
  expect((await api(admin, "post", `/api/laboratory/${id}/verify_result/`, {})).status).toBe(200)
  expect((await api(lab, "post", `/api/laboratory/${id}/release_result/`, {})).status).toBe(200)
})

test("consultation completes; pharmacy dispenses; every charge reconciles (INT-004)", async ({ page, browser }) => {
  await signInAs(page, "demo.doctor1")
  expect((await api(page, "patch", `/api/encounters/visits/${shared.visit}/`, { status: "Completed" })).status).toBe(200)

  // Pharmacy: the doctor prescribes from stock, the pharmacist dispenses.
  await page.goto("/prescription")
  await pickPatient(page, PATIENT)
  await page.getByPlaceholder("Drug and strength").first().fill("Paracetamol 500mg")
  await page.getByLabel("Qty").first().fill("2")
  await page.getByRole("button", { name: "Save prescription" }).click()
  const saved = page.getByText(/Prescription RX-\d+ created successfully/)
  await expect(saved).toBeVisible()
  const rx = (await saved.textContent()).match(/RX-\d+/)[0]
  const pharmacist = await (await browser.newContext()).newPage()
  await signInAs(pharmacist, "demo.pharmacist")
  await pharmacist.goto("/pharmacy")
  await pharmacist.getByPlaceholder("RX-0001").fill(rx)
  await pharmacist.getByRole("button", { name: "Search Prescription" }).click()
  await pharmacist.getByRole("button", { name: "Dispense Prescription" }).click()
  await expect(pharmacist.getByText(`Prescription ${rx} dispensed successfully.`)).toBeVisible()

  const billing = await (await browser.newContext()).newPage()
  await signInAs(billing, "demo.billing")
  const invoices = rows((await api(billing, "get", `/api/billing/invoices/?hospital=1&patient=${shared.patient}`)).body)
  const visitBill = invoices.find((i) => i.visit === shared.visit)
  const detail = (await api(billing, "get", `/api/billing/invoices/${visitBill.id}/`)).body
  const lines = detail.items.map((i) => [i.category, i.unit_price, i.quantity])
  expect(lines.sort()).toEqual([["consultation", PRICES.consultation, 1], ["imaging", PRICES.imaging, 1], ["laboratory", PRICES.lab, 1]])
  expect(detail.total_amount).toBe("1101.50")
  const sum = detail.items.reduce((total, item) => total + Math.round(Number(item.subtotal) * 100) + Math.round(Number(item.tax_amount || 0) * 100), 0)
  expect(sum).toBe(110150)
  const pharmacyBill = invoices.find((i) => i.prescription)
  expect(pharmacyBill.total_amount).toBe("4.48") // 2 × ₹2.00 + 12% GST
  shared.visitBill = visitBill
  shared.reconciliation = { visitBill: visitBill.invoice_number, lines, total: detail.total_amount, pharmacy: pharmacyBill.total_amount }

  // A partial payment in paise leaves the exact balance.
  await billing.goto("/billing")
  const row = billing.getByRole("row", { name: new RegExp(visitBill.invoice_number) })
  await row.getByRole("button", { name: "Payment" }).click()
  await billing.locator("input[name=paid]").fill("101.25")
  await billing.locator("select[name=payment]").selectOption("Cash")
  await billing.getByRole("button", { name: "Save Changes" }).click()
  await expect(row).toContainText("Partially Paid")
  await expect(row).toContainText("₹1,000.25")
  await billing.screenshot({ path: `${SHOTS}/4-visit-bill-partially-paid.png` })
  const after = (await api(billing, "get", `/api/billing/invoices/${visitBill.id}/`)).body
  expect([after.status, after.total_paid, after.balance_due]).toEqual(["Partially Paid", "101.25", "1000.25"])
})

test("the patient sees diagnosis, results, image and the bill due (MF-008, MF-009)", async ({ page }) => {
  await patientSignsIn(page)
  await expect(page.getByText("My health record")).toBeVisible()
  await expect(page.getByText(/Acute bronchitis/)).toBeVisible()
  await expect(page.getByText("Normal chest radiograph.")).toBeVisible()
  await expect(page.getByText(/Hb 13.2/)).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/5-patient-health-record.png`, fullPage: true })
  const imageUrl = `/api/laboratory/imaging/${shared.study.id}/images/${shared.image}/`
  expect((await page.request.get(imageUrl)).status()).toBe(200)

  await page.goto("/patient/bills")
  await expect(page.getByText(shared.visitBill.invoice_number)).toBeVisible()
  await expect(page.getByText("₹1,000.25").first()).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/6-patient-bill-due.png`, fullPage: true })
})

test("the patient moves and then cancels their own booking (MF-003)", async ({ page }) => {
  await patientSignsIn(page)
  const day = (weekday) => {
    const d = new Date()
    d.setUTCHours(12, 0, 0, 0)
    do d.setUTCDate(d.getUTCDate() + 1)
    while (d.getUTCDay() !== weekday)
    return d.toISOString().slice(0, 10)
  }
  const booked = await api(page, "post", "/api/appointments/book/", { doctor: shared.doctor, appointment_date: day(1), appointment_time: "15:00" })
  expect(booked.status, JSON.stringify(booked.body)).toBe(201)

  await page.goto("/patient/appointments")
  const item = page.getByRole("listitem").filter({ hasText: "15:00" })
  await item.getByRole("button", { name: "Reschedule" }).click()
  const move = page.getByRole("dialog", { name: "Reschedule appointment" })
  await move.locator("#move-date").fill(day(0))
  await expect(move).toContainText("does not see patients on Sundays")
  await move.locator("#move-date").fill(day(2))
  await move.locator("#move-time").selectOption("15:30")
  await page.screenshot({ path: `${SHOTS}/7-reschedule.png` })
  await move.getByRole("button", { name: "Move appointment" }).click()
  await expect(page.getByText(/Moved to/)).toBeVisible()

  const moved = page.getByRole("listitem").filter({ hasText: "15:30" })
  await moved.getByRole("button", { name: "Cancel" }).click()
  const cancel = page.getByRole("dialog", { name: "Cancel appointment" })
  await cancel.locator("#cancel-reason").fill("Synthetic: feeling better")
  await cancel.getByRole("button", { name: "Cancel appointment" }).click()
  await expect(page.getByText(/was cancelled/)).toBeVisible()
  await expect(moved).toContainText("Cancelled")
  await expect(moved.getByRole("button", { name: "Reschedule" })).toHaveCount(0)
  await page.screenshot({ path: `${SHOTS}/8-cancelled.png` })
  const record = (await api(page, "get", `/api/appointments/${booked.body.id}/`)).body
  expect([record.status, record.appointment_date, record.appointment_time.slice(0, 5)]).toEqual(["Cancelled", day(2), "15:30"])
})

test("no staff profile stays in browser storage; logout leaves nothing behind (SEC-001)", async ({ page }) => {
  await signInAs(page, "demo.desk.main")
  const stored = await page.evaluate(() => Object.fromEntries(Object.keys(localStorage).map((k) => [k, localStorage.getItem(k)])))
  expect(stored.user).toBeUndefined()
  expect(stored.roles).toBeUndefined()
  expect(stored.hospitals).toBeUndefined()
  expect(JSON.stringify(stored)).not.toContain("@example")
  shared.storageAfterLogin = Object.keys(stored).sort()

  await page.getByRole("button", { name: /^Profile menu for/ }).click()
  await page.getByRole("menuitem", { name: /Sign out|Log out|Logout/i }).click()
  await expect(page).toHaveURL(/login|\/$/)
  // Logout finishes after the server call returns; wait for it, then check twice
  // (a page that re-saved the hospital afterwards would show up the second time).
  const keys = () => page.evaluate(() => Object.keys(localStorage))
  for (const key of ["user", "roles", "hospitals", "selectedHospital", "hms_session"]) {
    await expect.poll(keys, { timeout: 5000 }).not.toContain(key)
  }
  await page.waitForTimeout(1500)
  const left = await keys()
  for (const key of ["user", "roles", "hospitals", "selectedHospital", "hms_session"]) expect(left).not.toContain(key)
  shared.storageAfterLogout = left.sort()
})

test.afterAll(async () => {
  const fs = await import("node:fs")
  fs.writeFileSync(`${SHOTS}/run-facts.json`, JSON.stringify({ ...shared, generated: new Date().toISOString() }, null, 2))
})
