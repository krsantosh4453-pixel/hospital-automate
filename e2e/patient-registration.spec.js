import { expect, test } from "@playwright/test"
import { readFile } from "node:fs/promises"
import { signInAs, uniqueName, uniquePhone } from "./helpers.js"

// Prompt 3 (E2E audit 2026-11-24): a self-registered patient had no hospital,
// so no UHID and no booking; the front desk had no screen to enrol an existing
// patient. Synthetic patients only; codes come from the e2e console OTP log.

const HOSPITAL = "Demo City Hospital"
const SHOTS = "reports/e2e-evidence/prompt-3"
const UHID = /DCH-\d{4}-\d{6}/

test.describe.configure({ mode: "serial" })

const newcomer = { phone: uniquePhone(), name: uniqueName("Synthetic Signup"), dob: "1991-04-12" }
let newcomerUhid = ""
// The server allows one OTP per number per minute (OTP_RESEND_COOLDOWN);
// signing in again waits that out instead of working around it.
const OTP_COOLDOWN_MS = 61000
let lastOtpAt = 0

/** The latest code the e2e backend logged for `phone` (backend/e2e-otp.log), or null. */
async function latestOtp(phone) {
  const log = await readFile("backend/e2e-otp.log", "utf8").catch(() => "")
  const matches = [...log.matchAll(new RegExp(`OTP for \\+?9?1?${phone}\\b.*?: (\\d{6})`, "g"))]
  return matches.length ? matches[matches.length - 1][1] : null
}

async function patientSignsInWithOtp(page, phone) {
  await page.goto("/patient-login")
  await page.getByRole("tab", { name: "Mobile OTP" }).click()
  await page.locator("#pl-field-1").fill(phone)
  // A second sign-in must use the NEW code, not the one already in the log.
  const previous = await latestOtp(phone)
  await page.getByRole("button", { name: "Send OTP" }).click()
  lastOtpAt = Date.now()
  let code = null
  await expect.poll(async () => (code = await latestOtp(phone)) && code !== previous ? code : null).not.toBeNull()
  await page.locator("#pl-field-2").fill(code)
  await page.getByRole("button", { name: "Verify & Continue" }).click()
  await expect(page).toHaveURL(/\/patient$/)
}

/** A patient account with no hospital, made through the public sign-up API. */
async function accountWithoutHospital(page, person) {
  const csrf = (await (await page.request.get("/api/auth/csrf/")).json()).csrfToken
  const response = await page.request.post("/api/auth/register/", {
    headers: { "X-CSRFToken": csrf },
    data: {
      role: "Patient", full_name: person.name, phone: person.phone, email: `p${person.phone}@example.test`,
      password: "Synth-Pass-3001", confirm_password: "Synth-Pass-3001", date_of_birth: person.dob, gender: "Female",
    },
  })
  expect(response.status(), await response.text()).toBe(201)
  expect((await response.json()).patient.hospitals).toEqual([])
}

test("A: a new patient picks a hospital at sign-up and gets its UHID (TEST 1, 10)", async ({ page }) => {
  await page.goto("/register?role=Patient")
  await page.locator("#reg-field-1").fill(newcomer.name)
  await page.locator("#reg-field-phone").fill(newcomer.phone)
  await page.locator("#reg-field-2").fill(`p${newcomer.phone}@example.test`)
  await page.locator("#reg-field-3").fill(newcomer.dob)
  await page.locator("#reg-field-hospital").selectOption({ label: HOSPITAL })
  await page.locator("#reg-field-14").fill("Synth-Pass-3001")
  await page.locator("#reg-field-15").fill("Synth-Pass-3001")
  await page.getByRole("button", { name: "Create Account" }).click()

  const confirmation = page.getByText(`Registered at ${HOSPITAL}`)
  await expect(confirmation).toBeVisible()
  newcomerUhid = (await confirmation.locator("..").innerText()).match(UHID)[0]
  await page.screenshot({ path: `${SHOTS}/A1-registered-with-uhid.png` })

  await patientSignsInWithOtp(page, newcomer.phone)
  const card = page.getByRole("heading", { name: "Your hospitals" }).locator("xpath=ancestor::*[contains(@class,'rounded')][1]")
  await expect(card).toContainText(HOSPITAL)
  await expect(card).toContainText(newcomerUhid)
  const me = await (await page.request.get("/api/auth/patient/me/")).json()
  expect((me.hospitals || me.patient?.hospitals || []).map((h) => h.uhid)).toEqual([newcomerUhid])
  await page.screenshot({ path: `${SHOTS}/A2-dashboard-uhid.png` })

  await page.reload()
  await expect(page.getByText(newcomerUhid)).toBeVisible()
})

test("C: the same patient signs in again and books at that hospital (TEST 9, 10)", async ({ page }) => {
  test.setTimeout(120000)
  await page.waitForTimeout(Math.max(0, OTP_COOLDOWN_MS - (Date.now() - lastOtpAt)))
  await patientSignsInWithOtp(page, newcomer.phone)
  await expect(page.getByText(newcomerUhid)).toBeVisible()

  await page.goto("/patient/appointments?book=1")
  const dialog = page.getByRole("dialog", { name: "Book an appointment" })
  await dialog.getByLabel(/^Hospital/).selectOption({ label: HOSPITAL })
  const doctor = dialog.getByLabel(/^Doctor/)
  await expect(doctor.locator("option")).not.toHaveCount(1)
  await doctor.selectOption({ index: 1 })
  const time = dialog.getByLabel(/^Time/)
  await expect(time.locator("option")).not.toHaveCount(1)
  await time.selectOption({ index: 1 })
  await dialog.getByRole("button", { name: "Confirm booking" }).click()
  await expect(page.getByText(/Booked with/)).toBeVisible()

  const mine = await (await page.request.get("/api/appointments/")).json()
  const booked = (mine.results || mine).find((a) => a.status === "Scheduled")
  expect(booked.hospital_name).toBe(HOSPITAL)
  expect(booked.patient_name).toBe(newcomer.name)
  await page.screenshot({ path: `${SHOTS}/C-booked.png` })
})

test("B: the front desk enrols an existing patient by mobile and date of birth (TEST 5, 6)", async ({ page }) => {
  const person = { phone: uniquePhone(), name: uniqueName("Synthetic Existing"), dob: "1988-08-08" }
  await accountWithoutHospital(page, person)

  await signInAs(page, "demo.desk.main")
  await page.goto("/patients")
  const enrol = async () => {
    await page.getByRole("button", { name: "Enrol existing patient" }).click()
    const dialog = page.getByRole("dialog", { name: "Enrol existing patient" })
    await dialog.getByLabel(/^Mobile number/).fill(person.phone)
    await dialog.getByLabel(/^Date of birth/).fill(person.dob)
    await dialog.getByRole("button", { name: "Find and enrol" }).click()
    return dialog
  }

  let dialog = await enrol()
  await expect(dialog).toContainText(`${person.name} is now registered at ${HOSPITAL}`)
  const uhid = (await dialog.innerText()).match(UHID)[0]
  await page.screenshot({ path: `${SHOTS}/B1-enrolled.png` })
  await dialog.getByRole("button", { name: "Close", exact: true }).click()

  dialog = await enrol()
  await expect(dialog).toContainText(`${person.name} is already registered at ${HOSPITAL}`)
  await expect(dialog).toContainText(uhid)
  await page.screenshot({ path: `${SHOTS}/B2-already-registered.png` })
  await dialog.getByRole("button", { name: "Close", exact: true }).click()

  // One patient record with that number, now registered here with that UHID.
  const hospitalId = await page.evaluate(() => JSON.parse(localStorage.getItem("selectedHospital")).id)
  const found = await (await page.request.get(`/api/patients/?hospital=${hospitalId}&search=${person.phone}`)).json()
  const rows = (found.results || found).filter((p) => p.phone?.endsWith(person.phone))
  expect(rows.map((p) => p.uhid)).toEqual([uhid])

  // A wrong date of birth finds nobody and enrols nothing.
  await page.getByRole("button", { name: "Enrol existing patient" }).click()
  dialog = page.getByRole("dialog", { name: "Enrol existing patient" })
  await dialog.getByLabel(/^Mobile number/).fill(uniquePhone())
  await dialog.getByLabel(/^Date of birth/).fill(person.dob)
  await dialog.getByRole("button", { name: "Find and enrol" }).click()
  await expect(dialog).toContainText("No patient has this mobile number and date of birth")
})

test("D: a patient with no hospital registers at one from the booking form, then can book", async ({ page }) => {
  const person = { phone: uniquePhone(), name: uniqueName("Synthetic Joiner"), dob: "1993-03-03" }
  await accountWithoutHospital(page, person)
  await patientSignsInWithOtp(page, person.phone)

  await page.goto("/patient/appointments?book=1")
  const dialog = page.getByRole("dialog", { name: "Book an appointment" })
  await expect(dialog).toContainText("You are not registered at any hospital yet")
  await dialog.locator("#join-hospital").selectOption({ label: HOSPITAL })
  await dialog.getByRole("button", { name: "Register at this hospital" }).click()
  await expect(dialog.getByLabel(/^Hospital/).first().locator("option", { hasText: HOSPITAL })).toHaveCount(1)
  await page.screenshot({ path: `${SHOTS}/D-joined-from-booking.png` })

  const me = await (await page.request.get("/api/auth/patient/me/")).json()
  expect((me.hospitals || me.patient?.hospitals || [])[0].uhid).toMatch(UHID)
})
