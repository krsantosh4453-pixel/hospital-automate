import { expect, test } from "@playwright/test"
import { signInAs } from "./helpers.js"

// A doctor prescribes for an admitted patient; the ward nurse gives the due
// dose from the MAR and it leaves the due list. No screen creates MAR orders
// yet, so that one step (order + dose schedule) goes through the API with the
// doctor's session, exactly as a future order screen would.
const MEDICINE = `Inj Ceftriaxone 1 g E2E${Date.now().toString(36).toUpperCase()}`
const PATIENT = "Demo Kiran (Ward A)"

async function prescribe(page) {
  await page.goto("/prescription")
  const patient = page.getByLabel(/^Patient/)
  const option = patient.locator("option", { hasText: PATIENT })
  await option.waitFor({ state: "attached" })
  await patient.selectOption(await option.getAttribute("value"))
  await page.getByPlaceholder("Drug and strength").first().fill(MEDICINE)
  await page.getByLabel("Dosage").first().fill("1 g")
  await page.getByLabel("Frequency").first().fill("BID")
  await page.getByRole("button", { name: "Save prescription" }).click()
  const saved = page.getByText(/Prescription RX-\d+ created successfully/)
  await expect(saved).toBeVisible()
  return Number((await saved.textContent()).match(/RX-0*(\d+)/)[1])
}

async function createMarOrder(page, prescriptionId) {
  const api = page.request
  const csrf = (await (await api.get("/api/auth/csrf/")).json()).csrfToken
  const rx = await (await api.get(`/api/clinical/prescriptions/${prescriptionId}/`)).json()
  const headers = { "X-CSRFToken": csrf, "X-Hospital-ID": String(rx.hospital) }
  const admissions = await (await api.get(`/api/ipd/admissions/?hospital=${rx.hospital}&patient=${rx.patient}`)).json()
  const admission = (admissions.results || admissions).find((a) => a.patient === rx.patient && a.status === "Admitted")

  const created = await api.post("/api/nurses/mar/", {
    headers,
    data: {
      patient: rx.patient, admission: admission.id, hospital: rx.hospital, prescription: rx.id,
      prescription_item: rx.items[0].id, medicine_name: MEDICINE, dose: "1 g", route: "IV",
      frequency: "BID", start_date: new Date().toISOString().slice(0, 10),
    },
  })
  expect(created.status()).toBe(201)
  // First dose ten minutes ago, so it is due now.
  const firstDose = new Date(Date.now() - 10 * 60 * 1000).toISOString()
  const schedule = await api.post(`/api/nurses/mar/${(await created.json()).id}/generate_schedule/`, {
    headers, data: { start_date: firstDose },
  })
  expect(schedule.status()).toBe(200)
}

test("ward nurse gives a due dose from the MAR", async ({ browser }) => {
  const doctor = await (await browser.newContext()).newPage()
  await signInAs(doctor, "demo.doctor1")
  await createMarOrder(doctor, await prescribe(doctor))

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
