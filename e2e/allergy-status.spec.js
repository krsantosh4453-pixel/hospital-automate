import { expect, test } from "@playwright/test"
import { signIn, signInAs } from "./helpers.js"

// BUG-001 (E2E audit 2026-11-24): the consultation strip said "No known
// allergies" for a patient nobody had asked. Synthetic seed patients only.

const RAVI = /Demo Ravi \(Cardiology OPD\)/
const KIRAN = /Demo Kiran \(Ward A\)/
const ALLERGEN = "Synthetic penicillin"
const SHOTS = "reports/e2e-evidence"

test.describe.configure({ mode: "serial" })

/** The patient's stored allergy status, as the API reports it. */
async function statusOf(page, patientId) {
  return (await (await page.request.get(`/api/patients/${patientId}/`)).json()).allergy_status
}

/** Open a visit in Consultation; returns the patient id the strip loaded. */
async function openVisit(page, name) {
  const loaded = page.waitForResponse((r) => /\/api\/patients\/\d+\/$/.test(new URL(r.url()).pathname) && r.ok())
  await page.getByRole("listbox", { name: "Visits" }).getByRole("option", { name }).first().click()
  return (await (await loaded).json()).id
}

const strip = (page) => page.getByLabel("Patient summary")

test("a patient nobody has asked is shown as unknown, then the doctor records NKA and an allergy", async ({ page }) => {
  await signInAs(page, "demo.doctor1")
  await page.goto("/consultation")
  const raviId = await openVisit(page, RAVI)

  // Original BUG-001 scenario: no allergy information recorded.
  expect(await statusOf(page, raviId)).toBe("Unknown")
  await expect(strip(page)).toContainText("Allergy status unknown — ask the patient")
  await expect(strip(page)).not.toContainText("No known allergies")
  await page.screenshot({ path: `${SHOTS}/allergy-1-unknown.png` })

  // The doctor asks and records "no known allergies" (confirmed first).
  await strip(page).getByRole("button", { name: "Record no known allergies" }).click()
  await page.getByRole("button", { name: "Patient has no known allergies" }).click()
  await expect(strip(page)).toContainText("No known allergies")
  await expect(strip(page).getByRole("button", { name: "Record no known allergies" })).toHaveCount(0)
  expect(await statusOf(page, raviId)).toBe("No known allergies")
  await page.screenshot({ path: `${SHOTS}/allergy-2-nka.png` })

  // An allergy recorded later replaces "no known allergies".
  await strip(page).getByRole("button", { name: "Add allergy" }).click()
  const dialog = page.getByRole("dialog", { name: "Add allergy" })
  await dialog.getByLabel(/^Allergen/).fill(ALLERGEN)
  await dialog.getByLabel("Severity").selectOption("Severe")
  await dialog.getByRole("button", { name: "Record allergy" }).click()
  await expect(strip(page)).toContainText(`${ALLERGEN} (Severe)`)
  await expect(strip(page)).not.toContainText("No known allergies")
  expect(await statusOf(page, raviId)).toBe("Has allergies")

  // Saved on the server, not just on the page.
  await page.reload()
  await openVisit(page, RAVI)
  await expect(strip(page)).toContainText(`${ALLERGEN} (Severe)`)
  await page.screenshot({ path: `${SHOTS}/allergy-3-known.png` })
})

test("switching patients never carries the previous patient's allergies across", async ({ page }) => {
  await signInAs(page, "demo.doctor1")
  // A second OPD visit with this doctor, for the ward patient.
  const csrf = (await (await page.request.get("/api/auth/csrf/")).json()).csrfToken
  const visits = await (await page.request.get("/api/encounters/visits/")).json()
  const ravisVisit = (visits.results || visits).find((v) => RAVI.test(v.patient_name || ""))
  const found = await (await page.request.get(`/api/patients/?hospital=${ravisVisit.hospital}&search=Demo%20Kiran`)).json()
  const kiran = (found.results || found).find((p) => KIRAN.test(p.name))
  const created = await page.request.post("/api/encounters/visits/", {
    headers: { "X-CSRFToken": csrf, "X-Hospital-ID": String(ravisVisit.hospital) },
    data: { hospital: ravisVisit.hospital, patient: kiran.id, doctor: ravisVisit.doctor, visit_type: "OPD" },
  })
  expect(created.ok(), await created.text()).toBeTruthy()

  await page.goto("/consultation")
  await openVisit(page, RAVI)
  await expect(strip(page)).toContainText(ALLERGEN)

  await openVisit(page, KIRAN)
  await expect(strip(page)).not.toContainText(ALLERGEN)
  await expect(strip(page)).toContainText("Allergy status unknown — ask the patient")
  await page.screenshot({ path: `${SHOTS}/allergy-4-switched.png` })

  await openVisit(page, RAVI)
  await expect(strip(page)).toContainText(ALLERGEN)
})

test("a pharmacist cannot change allergy facts through the API", async ({ page }) => {
  await signIn(page, "demo.pharmacist")
  await expect(page).toHaveURL("/")
  const csrf = (await (await page.request.get("/api/auth/csrf/")).json()).csrfToken
  const headers = { "X-CSRFToken": csrf }
  // The role check runs before the record is looked up, so any id answers 403.
  const setStatus = await page.request.post("/api/patients/1/allergy-status/", {
    headers, data: { status: "No known allergies" },
  })
  expect(setStatus.status()).toBe(403)
  const addAllergy = await page.request.post("/api/clinical/allergies/", {
    headers, data: { patient: 1, name: "Synthetic latex" },
  })
  expect(addAllergy.status()).toBe(403)
})
