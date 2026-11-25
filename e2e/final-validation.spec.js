/* global process, Buffer */
import { expect, test } from "@playwright/test"
import { copyFile, readFile, writeFile, mkdir } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { E2E_PASSWORD, signIn } from "./helpers.js"

// Prompt 6: a fresh synthetic hospital, run through the whole journey in the
// real browser against the isolated e2e backend. Validation only. Every step
// records what it saw in state.json, so a failing step does not hide the rest.
// Passwords are generated per run and never written to the evidence.

const DIR = "reports/e2e-evidence/final-validation"
// Kept outside the project while running: the dev server watches the project
// tree (Tailwind rescans files), so writing here would reload the page under test.
const STATE = join(tmpdir(), "hms-final-validation-state.json")
const SESSION = join(tmpdir(), "hms-final-validation-patient.json")
const RUN = process.env.FINAL_RUN_ID || `FV${Date.now().toString(36).toUpperCase()}`
const PASS = `Synth-${RUN}-pw1`
const ADMIN_CODE = process.env.ADMIN_INVITE_CODE || ""

test.describe.configure({ mode: "default" })

async function load() {
  try { return JSON.parse(await readFile(STATE, "utf8")) } catch { return { run: RUN, steps: {}, facts: {} } }
}
async function save(state) {
  await writeFile(STATE, JSON.stringify(state, null, 2))
}
async function note(step, result, detail) {
  const state = await load()
  state.steps[step] = { result, detail, at: new Date().toISOString() }
  await save(state)
}
async function fact(key, value) {
  const state = await load()
  state.facts[key] = value
  await save(state)
}
const facts = async () => (await load()).facts
// Web fonts come from an external CDN; when it is slow, screenshots wait on it.
// Blocked in the test browser only (the page falls back to system fonts).
async function blockFonts(page) {
  await page.context().route(/fonts\.(googleapis|gstatic)\.com/, (route) => route.abort()).catch(() => {})
}
async function shot(page, name) {
  await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: true, timeout: 15000 }).catch(() => {})
}
test.beforeEach(async ({ page }) => blockFonts(page))

async function call(page, method, url, data, hospital) {
  const csrf = (await (await page.request.get("/api/auth/csrf/")).json()).csrfToken
  const headers = { "X-CSRFToken": csrf }
  if (hospital) headers["X-Hospital-ID"] = String(hospital)
  const response = await page.request[method](url, { headers, ...(data === undefined ? {} : { data }) })
  const type = response.headers()["content-type"] || ""
  return { status: response.status(), body: type.includes("json") ? await response.json() : await response.text() }
}
const rows = (body) => (Array.isArray(body) ? body : body?.results || [])

async function staffSignIn(page, username) {
  await blockFonts(page)
  await signIn(page, username, PASS)
  await expect(page).not.toHaveURL(/staff-login/, { timeout: 15000 })
}

// ---------------------------------------------------------------- phase 0/1

test("00 reset run state", async () => {
  await save({ run: RUN, started: new Date().toISOString(), steps: {}, facts: { run: RUN } })
})

test("01 a new Hospital Admin signs up with the admin invitation code", async ({ page }) => {
  test.skip(!ADMIN_CODE, "ADMIN_INVITE_CODE not set for the e2e backend")
  const email = `admin.${RUN.toLowerCase()}@example.test`
  await page.goto("/register")
  await page.locator("[role=radio]", { hasText: /^Admin$/ }).click()
  await page.locator("#reg-field-1").fill(`Synthetic Admin ${RUN}`)
  await page.locator("#reg-field-phone").fill(`7${Date.now().toString().slice(-9)}`)
  await page.locator("#reg-field-2").fill(email)
  await page.locator("#reg-field-13").fill(ADMIN_CODE)
  await page.locator("#reg-field-14").fill(PASS)
  await page.locator("#reg-field-15").fill(PASS)
  const response = page.waitForResponse((r) => r.url().includes("/auth/register/") && r.request().method() === "POST")
  await page.getByRole("button", { name: "Create Account" }).click()
  const registered = await response
  const body = await registered.json().catch(() => ({}))
  await shot(page, "01-admin-signup")
  expect(registered.status(), JSON.stringify(body)).toBe(201)
  await fact("admin", { username: body.user?.username || email, email })
  await note("01-admin-signup", "PASS", `201; user ${body.user?.username}`)
})

test("02 the Admin creates the hospital, a department and a ward with beds", async ({ page }) => {
  const { admin } = await facts()
  await staffSignIn(page, admin.username)
  await page.goto("/admin/setup")
  await page.getByLabel(/Hospital name/).fill(`Synthetic Final Hospital ${RUN}`)
  await page.getByLabel(/Registration code/).fill(`SF${RUN.slice(-4)}`)
  await page.getByLabel(/^City/).fill("Pune")
  await page.getByLabel(/^State/).fill("Maharashtra")
  const created = page.waitForResponse((r) => /\/hospitals\/$/.test(new URL(r.url()).pathname) && r.request().method() === "POST")
  await page.getByRole("button", { name: "Create hospital" }).click()
  const hospital = await (await created).json()
  expect(hospital.id).toBeTruthy()
  await fact("hospital", { id: hospital.id, name: hospital.name, code: hospital.code || hospital.registration_code, uhid_prefix: hospital.uhid_prefix })
  await shot(page, "02-hospital-created")
  // Observation: the wizard sometimes stays on "1. Hospital" after creating one.
  const stayed = await page.getByRole("button", { name: "Add a new hospital instead" }).isVisible().catch(() => false)
  await fact("wizardStayedOnStep1", stayed)
  if (stayed) {
    // The step buttons stay disabled until the page picks up the new hospital: reload, as a user would.
    await page.reload()
  }
  await page.getByRole("button", { name: "2. Departments" }).click()
  await expect(page.getByRole("heading", { name: "Departments", level: 2 })).toBeVisible()
  await page.getByPlaceholder("e.g. General Medicine").fill("General Medicine")
  await page.getByRole("button", { name: "Add", exact: true }).click()
  await expect(page.getByText("General Medicine").first()).toBeVisible()
  await page.getByRole("button", { name: "3. Wards & beds" }).click()
  await page.getByLabel(/Ward name/).fill("Ward F1")
  await page.getByLabel("Beds").first().fill("3")
  await page.getByRole("button", { name: /Create ward with/ }).click()
  await expect(page.getByText(/was created with/)).toBeVisible()
  await shot(page, "02-ward-created")

  const detail = await call(page, "get", `/api/hospital/hospitals/${hospital.id}/`).catch(() => null)
  await fact("hospitalDetail", detail?.body || null)
  await note("02-hospital", "PASS", `hospital ${hospital.id} "${hospital.name}", department, ward with 3 beds`)
})

// ---------------------------------------------------------------- prices

const PRICES = [
  // category, code, name, applies_to, price, GST
  ["consultation", "CON-OPD", "OPD consultation", "", "450.50", "0"],
  ["laboratory", "LAB-CBC", "Complete blood count", "Complete Blood Count", "320.25", "0"],
  ["imaging", "IMG-XR-CHEST", "X-ray chest", "X-ray Chest PA", "610.75", "0"],
  ["bed", "BED-GEN", "General bed per day", "", "1200.00", "0"],
]

test("03 the Admin configures consultation, lab, X-ray and bed prices in Billing", async ({ page }) => {
  const { admin, hospital } = await facts()
  await staffSignIn(page, admin.username)
  await page.goto("/billing")
  const card = page.getByRole("heading", { name: "Price list" }).locator("xpath=ancestor::*[contains(@class,'rounded')][1]")
  await card.getByRole("button", { name: "Show" }).click()
  for (const [category, code, name, appliesTo, price, gst] of PRICES) {
    await card.getByLabel(/^Category/).selectOption(category)
    await card.getByLabel(/^Code/).fill(code)
    await card.getByLabel(/^Name/).fill(name)
    await card.getByLabel(/^Applies to/).fill(appliesTo)
    await card.getByLabel(/^Price/).fill(price)
    await card.getByLabel(/^GST/).fill(gst)
    await card.getByRole("button", { name: "Add price" }).click()
    await expect(card.getByText(code)).toBeVisible()
  }
  await shot(page, "03-price-list")
  const listed = rows((await call(page, "get", `/api/billing/price-list/?hospital=${hospital.id}`, undefined, hospital.id)).body)
  const found = Object.fromEntries(listed.map((p) => [p.code, [p.category, p.applies_to, p.unit_price, p.hospital]]))
  await fact("prices", found)
  for (const [category, code, , appliesTo, price] of PRICES) expect(found[code]).toEqual([category, appliesTo, price, hospital.id])
  await note("03-prices", "PASS", `4 prices saved for hospital ${hospital.id} through the Billing price list`)
})

// ---------------------------------------------------------------- staff

const STAFF = [
  ["doctor", "Doctor"], ["desk", "Receptionist"], ["nurse", "Nurse"], ["compounder", "Compounder"],
  ["lab", "Lab Staff"], ["labcheck", "Lab Staff"], ["radiology", "Radiology Staff"], ["pharmacist", "Pharmacist"],
  ["billing", "Billing Staff"],
]

test("04 the Admin invites every staff role; each accepts the link and signs in", async ({ page, browser }) => {
  test.setTimeout(240000)
  const { admin, hospital } = await facts()
  await staffSignIn(page, admin.username)
  await page.goto("/admin/setup")
  await page.getByRole("button", { name: "4. Staff" }).click()
  const accounts = {}
  for (const [key, role] of STAFF) {
    const phone = `6${Date.now().toString().slice(-9)}`
    await page.getByLabel(/^Full name/).fill(`Synthetic ${role} ${key} ${RUN}`)
    await page.getByLabel(/^Mobile number/).fill(phone)
    await page.getByLabel(/^Email/).fill(`${key}.${RUN.toLowerCase()}@example.test`)
    await page.getByLabel(/^Role/).selectOption(role)
    if (role === "Doctor") await page.getByLabel(/^Speciality/).fill("General Medicine")
    const response = page.waitForResponse((r) => r.url().endsWith("/users/invite/") && r.request().method() === "POST")
    await page.getByRole("button", { name: "Send invitation" }).click()
    const invite = await response
    const body = await invite.json()
    expect(invite.status(), JSON.stringify(body)).toBeLessThan(300)
    accounts[key] = { role, invite_path: body.invite_path, emailed: body.emailed }
    await page.waitForTimeout(150)
  }
  await shot(page, "04-staff-invited")

  for (const [key] of STAFF) {
    const context = await browser.newContext()
    const person = await context.newPage()
    await person.goto(accounts[key].invite_path)
    await person.getByLabel(/^New password/).fill(PASS)
    await person.getByLabel(/^Confirm password/).fill(PASS)
    await person.getByRole("button", { name: "Set password" }).click()
    const done = person.getByText(/Sign in with username/)
    await expect(done).toBeVisible()
    accounts[key].username = (await done.locator("strong").innerText()).trim()
    if (key === "doctor") await shot(person, "04-invite-accepted")
    await staffSignIn(person, accounts[key].username)
    const me = (await call(person, "get", "/api/auth/staff/me/")).body
    accounts[key].roles = me.roles
    accounts[key].hospitals = (me.hospitals || []).map((h) => h.id ?? h)
    delete accounts[key].invite_path
    await context.close()
  }
  await fact("staff", accounts)
  for (const [key, role] of STAFF) {
    expect(accounts[key].roles).toContain(role)
    expect(accounts[key].hospitals).toContain(hospital.id)
  }
  await note("04-staff", "PASS", `${STAFF.length} accounts invited, accepted the link, signed in with the right role and hospital`)
})

test("05 each role reaches only its own modules; other hospitals are refused", async ({ browser }) => {
  test.setTimeout(180000)
  const { staff, hospital } = await facts()
  const probes = {
    "/api/patients/": null, "/api/laboratory/": null, "/api/laboratory/imaging/": null, "/api/billing/invoices/": null,
    "/api/pharmacy-sales/": null, "/api/clinical/vitals/": null, "/api/nurses/assessments/": null, "/api/users/": null,
  }
  // What the role catalogue and permission classes say each role may NOT read.
  const forbidden = {
    desk: ["/api/laboratory/", "/api/clinical/vitals/", "/api/nurses/assessments/", "/api/users/"],
    nurse: ["/api/billing/invoices/", "/api/pharmacy-sales/", "/api/users/"],
    compounder: ["/api/clinical/vitals/", "/api/laboratory/", "/api/nurses/assessments/", "/api/users/"],
    lab: ["/api/billing/invoices/", "/api/pharmacy-sales/", "/api/clinical/vitals/", "/api/users/"],
    radiology: ["/api/patients/", "/api/laboratory/", "/api/billing/invoices/", "/api/pharmacy-sales/", "/api/clinical/vitals/", "/api/users/"],
    pharmacist: ["/api/laboratory/", "/api/clinical/vitals/", "/api/nurses/assessments/", "/api/users/"],
    billing: ["/api/laboratory/", "/api/clinical/vitals/", "/api/nurses/assessments/", "/api/users/"],
    doctor: ["/api/users/"],
  }
  const matrix = {}
  const problems = []
  for (const key of Object.keys(forbidden)) {
    const context = await browser.newContext()
    const page = await context.newPage()
    await staffSignIn(page, staff[key].username)
    matrix[key] = {}
    for (const url of Object.keys(probes)) {
      matrix[key][url] = (await call(page, "get", url, undefined, hospital.id)).status
      if (forbidden[key].includes(url) && matrix[key][url] !== 403) problems.push(`${key} ${url} → ${matrix[key][url]}`)
    }
    await context.close()
  }
  // A doctor of the seeded Demo City Hospital forcing this hospital.
  const context = await browser.newContext()
  const outsider = await context.newPage()
  await signIn(outsider, "demo.doctor1", E2E_PASSWORD)
  await expect(outsider).toHaveURL("/")
  matrix.otherHospitalDoctor = {
    "/api/patients/": (await call(outsider, "get", "/api/patients/", undefined, hospital.id)).status,
    "/api/appointments/": (await call(outsider, "get", "/api/appointments/", undefined, hospital.id)).status,
  }
  for (const [url, code] of Object.entries(matrix.otherHospitalDoctor)) if (code !== 403) problems.push(`other-hospital doctor ${url} → ${code}`)
  await context.close()
  await fact("accessMatrix", matrix)
  await note("05-rbac", problems.length ? "FAIL" : "PASS", problems.length ? problems.join("; ") : "every forbidden probe answered 403")
  expect(problems).toEqual([])
})

test("06 the pharmacist stocks a medicine with its price", async ({ page }) => {
  const { staff, hospital } = await facts()
  await staffSignIn(page, staff.pharmacist.username)
  await page.goto("/pharmacy")
  const name = `Synth Paracetamol 500 ${RUN}`
  await page.getByRole("button", { name: "Add medicine" }).click()
  const form = page.getByRole("dialog", { name: "Add Medicine" })
  await form.getByLabel("Medicine Name").fill(name)
  await form.getByLabel("Salt (generic name)").fill("paracetamol")
  await form.getByLabel("Category").selectOption("Tablet")
  await form.getByLabel("Batch Number").fill(`B-${RUN}`)
  await form.getByLabel("Stock Quantity").fill("20")
  await form.getByLabel("Expiry (month)").fill("2028-12")
  await form.getByLabel("Price").fill("2.50")
  await form.getByLabel(/^GST/).fill("12")
  await form.getByRole("button", { name: "Add Medicine", exact: true }).click()
  await expect(form).toBeHidden()
  const stock = rows((await call(page, "get", `/api/pharmacy/?hospital=${hospital.id}`, undefined, hospital.id)).body)
  const medicine = stock.find((m) => m.name === name)
  await fact("medicine", { id: medicine?.id, name, quantity: medicine?.quantity, price: medicine?.price, tax_rate: medicine?.tax_rate, hospital: medicine?.hospital })
  expect(medicine?.quantity).toBe(20)
  await shot(page, "06-medicine-stocked")
  await note("06-pharmacy-stock", "PASS", `${name}: 20 units at ₹${medicine?.price} (GST ${medicine?.tax_rate}%)`)
})

// ---------------------------------------------------------------- patient

async function latestOtp(phone) {
  const log = await readFile("backend/e2e-otp.log", "utf8").catch(() => "")
  const matches = [...log.matchAll(new RegExp(`OTP for \\+?9?1?${phone}\\b.*?: (\\d{6})`, "g"))]
  return matches.length ? matches[matches.length - 1][1] : null
}

const OTP_COOLDOWN_MS = 61000

async function otpSignIn(page, phone) {
  // The server allows one code per number per minute (OTP_RESEND_COOLDOWN).
  const { lastOtpAt = 0 } = await facts()
  const wait = lastOtpAt + OTP_COOLDOWN_MS - Date.now()
  if (wait > 0) await page.waitForTimeout(wait)
  await page.goto("/patient-login")
  await page.getByRole("tab", { name: "Mobile OTP" }).click()
  await page.locator("#pl-field-1").fill(phone)
  const previous = await latestOtp(phone)
  await page.getByRole("button", { name: "Send OTP" }).click()
  await fact("lastOtpAt", Date.now())
  let code = null
  await expect.poll(async () => (code = await latestOtp(phone)) && code !== previous ? code : null, { timeout: 20000 }).not.toBeNull()
  await page.locator("#pl-field-2").fill(code)
  await page.getByRole("button", { name: "Verify & Continue" }).click()
  await expect(page).toHaveURL(/\/patient$/)
  await page.context().storageState({ path: SESSION })
}

/** The patient's own signed-in session from the last OTP sign-in (cookies + the session flag). */
async function reuseSession(page) {
  const saved = JSON.parse(await readFile(SESSION, "utf8"))
  await page.context().addCookies(saved.cookies)
  const flags = (saved.origins || []).flatMap((o) => o.localStorage || [])
  await page.addInitScript((items) => { for (const { name, value } of items) localStorage.setItem(name, value) }, flags)
  await blockFonts(page)
  await page.goto("/patient")
  await expect(page).toHaveURL(/\/patient$/)
}

/** First sign-in by mobile OTP; later ones by email and password (OTP again if that is refused). */
async function patientSignIn(page, phone, { email } = {}) {
  await blockFonts(page)
  if (email) {
    await page.goto("/patient-login")
    await page.getByRole("tab", { name: "Email" }).click()
    await page.getByLabel("Email").first().fill(email)
    await page.getByLabel("Password").fill(PASS)
    await page.getByRole("button", { name: "Sign In" }).click()
    const ok = await page.waitForURL(/\/patient$/, { timeout: 10000 }).then(() => true).catch(() => false)
    const state = await load()
    state.facts.patientLoginPaths = [...(state.facts.patientLoginPaths || []), ok ? "email+password" : `email refused: ${await page.locator("[role=alert]").first().innerText().catch(() => "?")}`]
    await save(state)
    if (ok) return
  }
  await otpSignIn(page, phone)
}

test("07 a new patient registers at the new hospital and gets a UHID", async ({ page }) => {
  test.setTimeout(180000)
  const { hospital } = await facts()
  const phone = `9${Date.now().toString().slice(-9)}`
  const name = `Synthetic Patient ${RUN}`
  const checks = {}
  await page.goto("/register?role=Patient")
  const option = page.locator("#reg-field-hospital option", { hasText: hospital.name })
  await expect(option).toHaveCount(1)
  const fill = async () => {
    await page.locator("#reg-field-1").fill(name)
    await page.locator("#reg-field-phone").fill(phone)
    await page.locator("#reg-field-2").fill(`patient.${RUN.toLowerCase()}@example.test`)
    await page.locator("#reg-field-3").fill("1990-06-15")
    await page.locator("#reg-field-14").fill(PASS)
    await page.locator("#reg-field-15").fill(PASS)
  }
  // Invalid: no hospital chosen; mismatched passwords.
  await fill()
  await page.getByRole("button", { name: "Create Account" }).click()
  checks.missingHospital = await page.getByText("Choose the hospital where you want to be registered.").isVisible()
    || await page.locator("#reg-field-hospital").evaluate((el) => el.validity.valueMissing)
  await page.locator("#reg-field-hospital").selectOption(await option.getAttribute("value"))
  await page.locator("#reg-field-15").fill(`${PASS}-different`)
  await page.getByRole("button", { name: "Create Account" }).click()
  checks.passwordMismatch = await page.getByText(/match/i).first().isVisible().catch(() => false)
  await page.locator("#reg-field-15").fill(PASS)
  await page.getByRole("button", { name: "Create Account" }).click()
  const confirmation = page.getByText(`Registered at ${hospital.name}`)
  await expect(confirmation).toBeVisible()
  const uhid = ((await confirmation.locator("..").innerText()).match(/[A-Z0-9]+-\d{4}-\d{6}/) || [""])[0]
  await shot(page, "07-patient-registered")
  // Invalid: an unknown hospital id, and a duplicate of this account (API, public endpoint).
  const csrf = (await (await page.request.get("/api/auth/csrf/")).json()).csrfToken
  const base = { role: "Patient", full_name: name, phone, email: `patient.${RUN.toLowerCase()}@example.test`,
    password: PASS, confirm_password: PASS, date_of_birth: "1990-06-15", gender: "Female" }
  checks.duplicate = (await page.request.post("/api/auth/register/", { headers: { "X-CSRFToken": csrf }, data: { ...base, hospital: hospital.id } })).status()
  checks.unknownHospital = (await page.request.post("/api/auth/register/", { headers: { "X-CSRFToken": csrf },
    data: { ...base, phone: `9${Date.now().toString().slice(-9)}`, email: `other.${RUN.toLowerCase()}@example.test`, hospital: 999999 } })).status()

  await patientSignIn(page, phone)
  const me = (await call(page, "get", "/api/auth/patient/me/")).body
  const memberships = me.hospitals || me.patient?.hospitals || []
  const patientId = me.patient?.id ?? me.id
  await expect(page.getByText(uhid).first()).toBeVisible()
  await shot(page, "07-patient-dashboard-uhid")
  // Sign out and in again: the same UHID.
  await page.context().clearCookies()
  await patientSignIn(page, phone, { email: `patient.${RUN.toLowerCase()}@example.test` })
  const again = (await call(page, "get", "/api/auth/patient/me/")).body
  const uhidAgain = (again.hospitals || again.patient?.hospitals || []).find((h) => h.id === hospital.id)?.uhid
  // Someone else's record.
  checks.otherPatientRecord = (await call(page, "get", "/api/patients/1/")).status
  await fact("patient", { id: patientId, phone, name, uhid, memberships, email: `patient.${RUN.toLowerCase()}@example.test` })
  await fact("registrationChecks", { ...checks, uhidAfterRelogin: uhidAgain })
  const ok = uhid && uhidAgain === uhid && memberships.some((h) => h.id === hospital.id && h.uhid === uhid)
    && checks.missingHospital && checks.duplicate >= 400 && checks.unknownHospital >= 400 && [403, 404].includes(checks.otherPatientRecord)
  await note("07-patient", ok ? "PASS" : "FAIL", JSON.stringify({ uhid, ...checks, uhidAgain }))
  expect(ok, JSON.stringify(checks)).toBeTruthy()
})

// ---------------------------------------------------------------- appointment

const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date())
function nextWeekday(jsDay) {
  const d = new Date(`${today()}T12:00:00Z`)
  do d.setUTCDate(d.getUTCDate() + 1)
  while (d.getUTCDay() !== jsDay)
  return d.toISOString().slice(0, 10)
}

test("08 the patient books today with the new doctor; rules on days, slots and changes hold", async ({ page, browser }) => {
  test.setTimeout(180000)
  const { hospital, admin } = await facts()
  await reuseSession(page)
  await page.goto("/patient/appointments?book=1")
  const dialog = page.getByRole("dialog", { name: "Book an appointment" })
  const doctorSelect = dialog.getByLabel(/^Doctor/)
  const doctorOption = doctorSelect.locator("option", { hasText: `Synthetic Doctor doctor ${RUN}` })
  await expect(doctorOption).toHaveCount(1)
  const doctorId = await doctorOption.getAttribute("value")
  await doctorSelect.selectOption(doctorId)
  // Choosing the doctor already loaded another day's times; read today's only once they arrive.
  const todaysTimes = page.waitForResponse((r) => r.url().includes("/appointments/booking-options/") && r.url().includes(`date=${today()}`))
  await dialog.getByLabel(/^Date/).fill(today())
  await todaysTimes
  const time = dialog.getByLabel(/^Time/)
  await expect(time).toBeEnabled()
  await expect(time.locator("option")).not.toHaveCount(1)
  // The first time still open today (past times are listed but disabled).
  const slot = await time.locator("option:not([disabled])").nth(1).getAttribute("value")
  await time.selectOption(slot)
  const booked = page.waitForResponse((r) => r.url().includes("/appointments/book/"))
  await dialog.getByRole("button", { name: "Confirm booking" }).click()
  const appointment = await (await booked).json()
  await expect(page.getByText(/Booked with/)).toBeVisible()
  await shot(page, "08-booked")
  const checks = {}
  checks.sameSlotAgain = (await call(page, "post", "/api/appointments/book/", { doctor: Number(doctorId), appointment_date: today(), appointment_time: slot })).status

  // A second booking tomorrow-or-later: reschedule, then cancel through the patient's dialog.
  const later = nextWeekday(3)
  const second = await call(page, "post", "/api/appointments/book/", { doctor: Number(doctorId), appointment_date: later, appointment_time: "15:00" })
  checks.secondBooking = second.status
  await page.goto("/patient/appointments")
  const item = page.getByRole("listitem").filter({ hasText: "15:00" })
  await item.getByRole("button", { name: "Reschedule" }).click()
  const move = page.getByRole("dialog", { name: "Reschedule appointment" })
  await move.locator("#move-time").selectOption("15:30")
  await move.getByRole("button", { name: "Move appointment" }).click()
  await expect(page.getByText(/Moved to/)).toBeVisible()
  const moved = page.getByRole("listitem").filter({ hasText: "15:30" })
  await moved.getByRole("button", { name: "Cancel" }).click()
  const cancel = page.getByRole("dialog", { name: "Cancel appointment" })
  await cancel.locator("#cancel-reason").fill("Synthetic: plans changed")
  await cancel.getByRole("button", { name: "Cancel appointment" }).click()
  await expect(page.getByText(/was cancelled/)).toBeVisible()
  const history = rows((await call(page, "get", "/api/appointments/")).body).map((a) => [a.id, a.status, a.appointment_date, String(a.appointment_time).slice(0, 5)])
  checks.history = history
  await shot(page, "08-history")

  // The admin gives the doctor working days; a Sunday then offers no slots.
  const adminPage = await (await browser.newContext()).newPage()
  await staffSignIn(adminPage, admin.username)
  checks.setAvailability = (await call(adminPage, "patch", `/api/doctors/${doctorId}/`, { availability: "Mon-Sat 09:00-17:00" }, hospital.id)).status
  const sunday = (await call(page, "get", `/api/appointments/booking-options/?hospital=${hospital.id}&doctor=${doctorId}&date=${nextWeekday(0)}`)).body
  checks.sundaySlots = sunday.slots?.length
  checks.sundayReason = sunday.unavailable_reason
  checks.sundayBook = (await call(page, "post", "/api/appointments/book/", { doctor: Number(doctorId), appointment_date: nextWeekday(0), appointment_time: "10:00" })).status
  // Hospital isolation: the seeded hospital's doctor cannot be booked by this patient.
  checks.foreignDoctor = (await call(page, "post", "/api/appointments/book/", { doctor: 1, appointment_date: nextWeekday(1), appointment_time: "10:00" })).status
  await fact("doctorId", Number(doctorId))
  await fact("appointment", { id: appointment.id, date: appointment.appointment_date, time: appointment.appointment_time, status: appointment.status, hospital: appointment.hospital, doctor: appointment.doctor })
  await fact("bookingChecks", checks)
  const ok = appointment.hospital === hospital.id && checks.sameSlotAgain === 409 && checks.secondBooking === 201
    && history.some((h) => h[1] === "Cancelled" && h[3] === "15:30") && checks.sundaySlots === 0 && checks.sundayBook === 400
    && checks.foreignDoctor === 400
  await note("08-appointments", ok ? "PASS" : "FAIL", JSON.stringify({ appointment: appointment.id, ...checks, history: undefined }))
  expect(ok, JSON.stringify(checks)).toBeTruthy()
})

test("09 reception finds the patient with the UHID and issues the queue token", async ({ page }) => {
  const { staff, patient } = await facts()
  await staffSignIn(page, staff.desk.username)
  await page.goto("/patients")
  await page.getByPlaceholder(/Search/).first().fill(patient.name)
  await expect(page.getByText(patient.uhid).first()).toBeVisible()
  await shot(page, "09-reception-patient")
  await page.goto("/queue")
  await page.getByRole("button", { name: /^Issue token/ }).click()
  const dialog = page.getByRole("dialog", { name: "Check in a booked appointment" })
  await dialog.getByLabel(new RegExp(patient.name)).check()
  await dialog.getByRole("button", { name: `Issue token for ${patient.name}` }).click()
  await expect(page.getByText(new RegExp(`Token #\\d+ generated for ${patient.name}`))).toBeVisible()
  const row = page.getByRole("row", { name: new RegExp(patient.name) })
  await expect(row.getByText("Waiting")).toBeVisible()
  await shot(page, "09-token-issued")
  const forbidden = {
    vitals: (await call(page, "get", "/api/clinical/vitals/")).status,
    users: (await call(page, "get", "/api/users/")).status,
    lab: (await call(page, "get", "/api/laboratory/")).status,
  }
  await fact("receptionForbidden", forbidden)
  await note("09-reception", Object.values(forbidden).every((s) => s === 403) ? "PASS" : "FAIL", JSON.stringify(forbidden))
})

// ---------------------------------------------------------------- consultation

test("10 the doctor calls the patient, checks allergy status and records the consultation", async ({ page }) => {
  test.setTimeout(120000)
  const { staff, patient } = await facts()
  await staffSignIn(page, staff.doctor.username)
  await page.goto("/queue")
  const row = page.getByRole("row", { name: new RegExp(patient.name) })
  await row.getByRole("button", { name: "Call" }).click()
  await row.getByRole("button", { name: "Start consultation" }).click()
  await expect(row.getByText("In Consultation")).toBeVisible()

  await page.goto("/consultation")
  await page.getByRole("listbox", { name: "Visits" }).getByRole("option", { name: new RegExp(patient.name) }).first().click()
  await expect(page.getByText(patient.uhid).first()).toBeVisible()
  const strip = await page.locator("main").innerText()
  const allergy = { unknownShown: /Allergy status unknown|Allergies not recorded/i.test(strip), wrongNka: /No known allergies/.test(strip) && !/Record no known allergies/.test(strip) }
  await shot(page, "10-consultation-open")

  await page.getByRole("tab", { name: /Diagnoses/ }).click()
  await page.getByLabel(/^Diagnosis/).first().fill("Acute pharyngitis")
  await page.getByLabel(/^ICD-10 code/).fill("J02.9")
  await page.getByRole("button", { name: "Add diagnosis" }).click()
  await expect(page.getByText("Acute pharyngitis").first()).toBeVisible()
  await page.getByRole("tab", { name: /Notes/ }).click()
  await page.getByLabel(/^Chief complaint/).fill("Sore throat for 3 days (synthetic)")
  await page.getByLabel(/^Assessment/).fill("Viral pharyngitis likely")
  await page.getByRole("button", { name: "Add note" }).click()
  await page.getByRole("tab", { name: /Vitals/ }).click()
  await page.getByLabel("Systolic BP (mmHg)").fill("122")
  await page.getByLabel("Diastolic BP (mmHg)").fill("78")
  await page.getByLabel("Pulse (bpm)").fill("84")
  await page.getByLabel("Temperature (°C)").fill("37.8")
  await page.getByRole("button", { name: "Save vitals" }).click()
  await page.reload()
  await page.getByRole("listbox", { name: "Visits" }).getByRole("option", { name: new RegExp(patient.name) }).first().click()
  const visit = rows((await call(page, "get", `/api/encounters/visits/?patient=${patient.id}`)).body)[0]
  const diagnoses = rows((await call(page, "get", `/api/clinical/diagnoses/?visit=${visit.id}`)).body).map((d) => [d.name, d.icd10_code])
  const notes = rows((await call(page, "get", `/api/clinical/clinical-notes/?visit=${visit.id}`)).body).length
  const vitals = rows((await call(page, "get", `/api/clinical/vitals/?visit=${visit.id}`)).body).map((v) => [v.temperature, v.systolic_bp])
  await shot(page, "10-consultation-saved")
  await fact("visit", { id: visit.id, status: visit.status, hospital: visit.hospital, doctor: visit.doctor })
  await fact("consultation", { allergy, diagnoses, notes, vitals })
  const ok = allergy.unknownShown && !allergy.wrongNka && diagnoses.length === 1 && notes >= 1 && vitals.length >= 1
  await note("10-consultation", ok ? "PASS" : "FAIL", JSON.stringify({ visit: visit.id, allergy, diagnoses, notes, vitals }))
  expect(ok).toBeTruthy()
})

// ---------------------------------------------------------------- laboratory

test("11 lab staff order CBC, walk it through, a second lab user verifies; doctor and patient see it", async ({ page, browser }) => {
  test.setTimeout(180000)
  const { staff, patient, visit } = await facts()
  await staffSignIn(page, staff.lab.username)
  await page.goto("/laboratory")
  await page.getByRole("button", { name: "New lab order" }).first().click()
  const order = page.getByRole("dialog", { name: "New lab order" })
  await order.getByLabel(/^Patient/).fill(patient.name)
  await order.getByRole("button", { name: new RegExp(patient.name) }).first().click()
  await order.locator("#order-visit").waitFor({ timeout: 5000 }).catch(() => {})
  const visitFieldShown = await order.locator("#order-visit").isVisible().catch(() => false)
  if (visitFieldShown) await expect(order.locator("#order-visit")).not.toHaveValue("", { timeout: 5000 }).catch(() => {})
  const visitOptions = visitFieldShown ? (await order.locator("#order-visit option").count()) - 1 : null
  await fact("labVisitOptions", visitOptions)
  await order.getByLabel("Test").selectOption({ label: "Complete Blood Count" })
  await order.getByRole("button", { name: "Create order" }).click()
  await expect(order).toBeHidden()
  const tests = rows((await call(page, "get", `/api/laboratory/?patient=${patient.id}`)).body)
  const labTest = tests.find((t) => t.name === "Complete Blood Count")
  const row = page.getByRole("row", { name: new RegExp(`^LAB-${labTest.id} `) })
  for (const [action, stage] of [["Collect Sample", "Collected"], ["Dispatch Sample", "Dispatched"], ["Receive in Lab", "Received"], ["Start Processing", "Processing"]]) {
    await row.getByRole("button", { name: action }).click()
    await expect(row.getByRole("cell").nth(4)).toContainText(stage)
  }
  await row.getByRole("button", { name: "Enter Result" }).click()
  const result = page.getByRole("dialog", { name: /Result for Complete Blood Count/ })
  await result.getByRole("textbox").fill("Hb 13.4 g/dL; WBC 9.2 x10^9/L (synthetic)")
  await result.getByRole("button", { name: "Save" }).click()
  await expect(row.getByRole("cell").nth(4)).toContainText("Result Entered")
  const selfVerify = (await call(page, "post", `/api/laboratory/${labTest.id}/verify_result/`, {})).status

  const checker = await (await browser.newContext()).newPage()
  await staffSignIn(checker, staff.labcheck.username)
  await checker.goto("/laboratory")
  const checkerRow = checker.getByRole("row", { name: new RegExp(`^LAB-${labTest.id} `) })
  await checkerRow.getByRole("button", { name: "Verify Result" }).click()
  await expect(checkerRow.getByRole("cell").nth(4)).toContainText("Verified")
  await checkerRow.getByRole("button", { name: "Release Result" }).click()
  await expect(checkerRow.getByRole("cell").nth(4)).toContainText("Released")
  await shot(checker, "11-lab-released")

  const doctor = await (await browser.newContext()).newPage()
  await staffSignIn(doctor, staff.doctor.username)
  const seen = (await call(doctor, "get", `/api/laboratory/${labTest.id}/`)).body
  const pharmacist = await (await browser.newContext()).newPage()
  await staffSignIn(pharmacist, staff.pharmacist.username)
  const pharmacistRead = (await call(pharmacist, "get", `/api/laboratory/${labTest.id}/`)).status
  await fact("labTest", { id: labTest.id, visit: labTest.visit, visitFieldShownToLabStaff: visitFieldShown, selfVerify, doctorSees: [seen.status, seen.result], pharmacistRead })
  const ok = selfVerify === 403 && seen.status === "Released" && pharmacistRead === 403
  await note("11-laboratory", ok ? (labTest.visit === visit.id ? "PASS" : "PARTIAL") : "FAIL",
    `LAB-${labTest.id}; visit link ${labTest.visit ?? "none"} (expected ${visit.id}; visit field shown to Lab Staff: ${visitFieldShown}; visits offered: ${(await facts()).labVisitOptions}); self-verify ${selfVerify}; doctor sees ${seen.status}; pharmacist ${pharmacistRead}`)
  expect(ok).toBeTruthy()
})

// ---------------------------------------------------------------- radiology

const PNG = Buffer.from("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da6364f8ffbf1e0005fe02fea3c2a1b20000000049454e44ae426082", "hex")

test("12 X-ray: doctor orders on the visit, radiology performs and attaches, doctor signs", async ({ page, browser }) => {
  test.setTimeout(180000)
  const { staff, patient, visit } = await facts()
  await staffSignIn(page, staff.doctor.username)
  await page.goto("/radiology")
  await page.getByRole("button", { name: "New imaging order" }).click()
  const dialog = page.getByRole("dialog", { name: "New imaging order" })
  await dialog.getByLabel(/^Patient/).fill(patient.name)
  await dialog.getByRole("button", { name: new RegExp(patient.name) }).first().click()
  await expect(dialog.locator("#order-visit")).toHaveValue(String(visit.id))
  await dialog.getByLabel(/Body part/).fill("Chest PA")
  await dialog.getByLabel(/Clinical question/).fill("Persistent cough (synthetic)")
  await dialog.getByRole("button", { name: "Place order" }).click()
  await expect(dialog).toBeHidden()
  const study = rows((await call(page, "get", `/api/laboratory/imaging/?patient=${patient.id}`)).body)[0]
  const radiologyOrderByRadiographer = { note: "Radiology Staff cannot place orders: only doctors order (by design)" }

  const rad = await (await browser.newContext()).newPage()
  await staffSignIn(rad, staff.radiology.username)
  await rad.goto("/radiology")
  await rad.getByRole("row", { name: new RegExp(study.accession_number) }).getByRole("button", { name: "Performed" }).click()
  await rad.getByRole("dialog", { name: "Mark scan performed" }).getByRole("button", { name: "Mark performed" }).click()
  await rad.getByRole("tab", { name: /Awaiting report/ }).click()
  await rad.getByRole("row", { name: new RegExp(study.accession_number) }).getByRole("button", { name: "Images" }).click()
  const images = rad.getByRole("dialog", { name: "Study images" })
  const input = images.locator(`#study-image-${study.id}`)
  await input.setInputFiles({ name: "fake.exe", mimeType: "application/octet-stream", buffer: Buffer.from("MZ synthetic") })
  const exeRefused = await images.getByRole("alert").innerText().catch(() => "")
  const bigPath = join(tmpdir(), "hms-final-validation-51mb.png")
  await writeFile(bigPath, Buffer.concat([PNG, Buffer.alloc(51 * 1024 * 1024)]))
  await input.setInputFiles(bigPath)
  await expect(images.getByRole("alert")).toBeVisible()
  const bigRefused = await images.getByRole("alert").innerText().catch(() => "")
  await input.setInputFiles({ name: "chest-pa.png", mimeType: "image/png", buffer: PNG })
  await expect(images.getByRole("listitem")).toHaveCount(1)
  await shot(rad, "12-image-attached")
  const listed = (await call(rad, "get", `/api/laboratory/imaging/${study.id}/images/`)).body
  const imageUrl = listed[0]?.url

  const pharmacist = await (await browser.newContext()).newPage()
  await staffSignIn(pharmacist, staff.pharmacist.username)
  const pharmacistImage = (await pharmacist.request.get(imageUrl)).status()

  await page.getByRole("tab", { name: /Awaiting report/ }).click()
  await page.reload()
  await page.getByRole("tab", { name: /Awaiting report/ }).click()
  await page.getByRole("row", { name: new RegExp(study.accession_number) }).getByRole("button", { name: "Report" }).click()
  const report = page.getByRole("dialog", { name: "Report and sign" })
  await report.getByLabel(/Findings/).fill("Clear lung fields (synthetic).")
  await report.getByLabel(/Impression/).fill("No acute cardiopulmonary findings.")
  await report.getByRole("button", { name: "Sign report" }).click()
  await expect(report).toBeHidden()
  const doctorImage = (await page.request.get(imageUrl)).status()
  const signedAgain = (await call(page, "post", `/api/laboratory/imaging/${study.id}/report/`, { findings: "x", impression: "y" })).status
  await shot(page, "12-report-signed")
  await fact("study", { id: study.id, accession: study.accession_number, visit: study.visit, imageUrl, exeRefused, bigRefused, pharmacistImage, doctorImage, signedAgain, radiologyOrderByRadiographer })
  const ok = study.visit === visit.id && /PNG|JPEG|DICOM/.test(exeRefused) && /MB|large|size/i.test(bigRefused) && pharmacistImage === 403 && doctorImage === 200 && signedAgain === 400
  await note("12-radiology", ok ? "PASS" : "FAIL", JSON.stringify({ study: study.id, visit: study.visit, exeRefused, bigRefused, pharmacistImage, doctorImage, signedAgain }))
  expect(ok).toBeTruthy()
})

// ---------------------------------------------------------------- pharmacy

test("13 doctor prescribes; pharmacist searches, dispenses once; stock and ledger move", async ({ page, browser }) => {
  test.setTimeout(180000)
  const { staff, patient, medicine, hospital } = await facts()
  await staffSignIn(page, staff.doctor.username)
  await page.goto("/prescription")
  await page.getByLabel(/^Patient/).fill(patient.name)
  await page.getByRole("button", { name: new RegExp(patient.name) }).first().click()
  await page.getByPlaceholder("Drug and strength").first().fill(medicine.name)
  await page.getByLabel("Qty").first().fill("3")
  await page.getByRole("button", { name: "Save prescription" }).click()
  const saved = page.getByText(/Prescription RX-\d+ created successfully/)
  await expect(saved).toBeVisible()
  const rx = (await saved.textContent()).match(/RX-\d+/)[0]

  const ph = await (await browser.newContext()).newPage()
  const pageErrors = []
  ph.on("pageerror", (e) => pageErrors.push(e.message))
  await staffSignIn(ph, staff.pharmacist.username)
  await ph.goto("/pharmacy")
  const search = ph.getByPlaceholder("Search patient, medicine or SALE-number")
  for (const text of ["S", "Sy", "Synth", "zzzz-none", ""]) await search.fill(text)
  await ph.getByPlaceholder("RX-0001").fill(rx)
  await ph.getByRole("button", { name: "Search Prescription" }).click()
  await expect(ph.getByText("Required: 3")).toBeVisible()
  await ph.getByRole("button", { name: "Dispense Prescription" }).click()
  await expect(ph.getByText(`Prescription ${rx} dispensed successfully.`)).toBeVisible()
  await shot(ph, "13-dispensed")
  const stock = rows((await call(ph, "get", `/api/pharmacy/?hospital=${hospital.id}`, undefined, hospital.id)).body).find((m) => m.id === medicine.id)
  const rxRow = rows((await call(ph, "get", `/api/clinical/prescriptions/?hospital=${hospital.id}`, undefined, hospital.id)).body).find((p) => `RX-${String(p.id).padStart(4, "0")}` === rx || p.number === rx) || {}
  const again = await call(ph, "post", "/api/pharmacy-sales/dispense-prescription/", { prescription: rxRow.id, partial: false, lines: [] }, hospital.id)
  const negative = await call(ph, "post", "/api/pharmacy-sales/dispense-prescription/", { prescription: rxRow.id, partial: true, lines: [{ item: 1, medicine: medicine.id, quantity: -1 }] }, hospital.id)
  const ledger = rows((await call(ph, "get", `/api/procurement/stock-transactions/?hospital=${hospital.id}`, undefined, hospital.id)).body).filter((t) => t.medicine === medicine.id || t.medicine_name === medicine.name).map((t) => [t.transaction_type || t.type, t.quantity])
  await fact("pharmacy", { rx, prescription: rxRow.id, stockAfter: stock?.quantity, again: again.status, negative: [negative.status, negative.body?.message], ledger, pageErrors })
  const raw = /ErrorDetail|Traceback|\{'/.test(String(negative.body?.message))
  const ok = stock?.quantity === 17 && again.status >= 400 && negative.status === 400 && !raw && pageErrors.length === 0
  await note("13-pharmacy", ok ? "PASS" : "FAIL", JSON.stringify({ rx, stockAfter: stock?.quantity, againStatus: again.status, negative: negative.body?.message, ledger, pageErrors }))
  expect(ok).toBeTruthy()
})

test("14 the doctor completes the consultation", async ({ page }) => {
  const { staff, patient, visit } = await facts()
  await staffSignIn(page, staff.doctor.username)
  await page.goto("/queue")
  const row = page.getByRole("row", { name: new RegExp(patient.name) })
  await row.getByRole("button", { name: "Complete" }).click()
  await expect(row.getByText("Completed")).toBeVisible()
  const after = (await call(page, "get", `/api/encounters/visits/${visit.id}/`)).body
  await note("14-complete", after.status === "Completed" ? "PASS" : "FAIL", `visit ${visit.id} → ${after.status}`)
  expect(after.status).toBe("Completed")
})

// ---------------------------------------------------------------- billing

const paise = (value) => Math.round(Number(value) * 100)

test("15 every charge reconciles; partial then full payment; receipts and statuses agree", async ({ page }) => {
  test.setTimeout(180000)
  const { staff, patient, hospital } = await facts()
  await staffSignIn(page, staff.billing.username)
  const invoices = rows((await call(page, "get", `/api/billing/invoices/?hospital=${hospital.id}&patient=${patient.id}`, undefined, hospital.id)).body)
  const bills = []
  for (const invoice of invoices) {
    const d = (await call(page, "get", `/api/billing/invoices/${invoice.id}/`, undefined, hospital.id)).body
    const lineSum = d.items.reduce((sum, i) => sum + paise(i.subtotal), 0) + paise(d.tax_amount ?? d.tax ?? 0) - paise(d.discount ?? 0)
    bills.push({ id: d.id, number: d.invoice_number, visit: d.visit, prescription: d.prescription, total: d.total_amount, lineSum: (lineSum / 100).toFixed(2),
      lines: d.items.map((i) => ({ category: i.category, description: i.description, unit_price: i.unit_price, quantity: i.quantity, tax: i.tax_amount, key: i.charge_key })) })
  }
  const allLines = bills.flatMap((b) => b.lines)
  const keyed = allLines.filter((l) => l.key).map((l) => l.key)
  const duplicates = keyed.filter((k, i) => keyed.indexOf(k) !== i)
  const byCategory = Object.fromEntries(["consultation", "laboratory", "imaging"].map((c) => [c, allLines.filter((l) => l.category === c).map((l) => l.unit_price)]))
  const pharmacyLines = allLines.filter((l) => !["consultation", "laboratory", "imaging", "bed"].includes(l.category))

  await page.goto("/billing")
  const rowFor = (number) => page.getByRole("row", { name: new RegExp(number.replace(/[/]/g, "\\/")) })
  async function discount(bill, amount) {
    await rowFor(bill.number).getByRole("button", { name: "Edit" }).click()
    await page.locator("input[name=discount]").fill(amount)
    await page.getByRole("button", { name: "Save Changes" }).click()
    let state = null
    await expect.poll(async () => {
      state = (await call(page, "get", `/api/billing/invoices/${bill.id}/`, undefined, hospital.id)).body
      return state.discount
    }, { timeout: 15000 }).toBe(amount)
    return state
  }
  // Discount before payment on the visit bill. Its lines depend on which
  // orders were linked to the visit (since P2-1 the lab order is too).
  const visitBill = bills.find((b) => b.visit)
  const visitExpected = ((paise(visitBill.lineSum) - 6125) / 100).toFixed(2)
  const afterDiscount = await discount(visitBill, "61.25")
  visitBill.total = afterDiscount.total_amount
  await shot(page, "15-discount")
  const payments = []
  for (const bill of bills) {
    const due = paise(bill.total)
    if (due === 0) continue
    const row = page.getByRole("row", { name: new RegExp(bill.number.replace(/[/]/g, "\\/")) })
    const partial = bills.indexOf(bill) === 0 ? Math.min(10025, due - 1) : due
    for (const amount of partial < due ? [partial, due] : [due]) {
      await row.getByRole("button", { name: "Payment" }).click()
      await page.locator("input[name=paid]").fill((amount / 100).toFixed(2))
      await page.locator("select[name=payment]").selectOption("Cash")
      await page.getByRole("button", { name: "Save Changes" }).click()
      // Wait for the bill's paid total AND its status: a read that lands while
      // the payment commits can pair the old status with the new total (P3-5).
      let state = null
      const expected = amount < due ? "Partially Paid" : "Paid"
      await expect.poll(async () => {
        state = (await call(page, "get", `/api/billing/invoices/${bill.id}/`, undefined, hospital.id)).body
        return `${paise(state.total_paid)} ${state.status}`
      }, { timeout: 15000 }).toBe(`${amount} ${expected}`)
      payments.push({ bill: bill.number, paidTotal: state.total_paid, due: state.balance_due, status: state.status })
      if (amount < due) await shot(page, "15-partially-paid")
    }
  }
  // Refund part of the lab bill through the Refund dialog, then settle it with a discount.
  const labBill = bills.find((b) => b.lines.some((l) => l.category === "laboratory"))
  await page.reload()
  await rowFor(labBill.number).getByRole("button", { name: "Refund" }).click()
  const refund = page.getByRole("dialog", { name: "Refund" })
  await refund.locator("#refund-amount").fill("20.25")
  await refund.locator("#refund-reason").fill("Synthetic: one parameter not reported")
  await refund.getByRole("button", { name: "Record refund" }).click()
  await expect(refund).toBeHidden()
  const afterRefund = (await call(page, "get", `/api/billing/invoices/${labBill.id}/`, undefined, hospital.id)).body
  await shot(page, "15-refund")
  // The discount field is the bill's whole discount: add the refund to what is already there.
  const labSettled = await discount(labBill, ((paise(afterRefund.discount ?? 0) + 2025) / 100).toFixed(2))
  await fact("discountRefund", {
    visitBillAfterDiscount: [afterDiscount.total_amount, afterDiscount.discount, afterDiscount.status],
    labAfterRefund: [afterRefund.status, afterRefund.total_paid, afterRefund.balance_due],
    labAfterDiscount: [labSettled.status, labSettled.total_amount, labSettled.total_paid, labSettled.balance_due],
  })
  await page.waitForTimeout(1500)
  const finalStatuses = []
  for (const bill of bills) {
    const d = (await call(page, "get", `/api/billing/invoices/${bill.id}/`, undefined, hospital.id)).body
    finalStatuses.push([bill.number, d.status, d.total_amount, d.total_paid, d.balance_due])
  }
  await fact("billingFinalStatuses", finalStatuses)
  await page.reload({ waitUntil: "domcontentloaded" })
  await shot(page, "15-all-paid")
  const history = rows((await call(page, "get", `/api/billing/payments/?patient=${patient.id}`, undefined, hospital.id)).body).map((p) => [p.invoice, p.kind, p.amount, p.receipt_number])
  await fact("billing", { bills, byCategory, pharmacyLines, duplicates, payments, history })
  // Re-read every bill: its total must equal lines + tax - discount, to the paisa.
  const reread = []
  for (const bill of bills) {
    const d = (await call(page, "get", `/api/billing/invoices/${bill.id}/`, undefined, hospital.id)).body
    const sum = d.items.reduce((total, i) => total + paise(i.subtotal), 0) + paise(d.tax_amount ?? d.tax ?? 0) - paise(d.discount ?? 0)
    reread.push([d.invoice_number, d.total_amount, (sum / 100).toFixed(2), d.tax_amount ?? d.tax, d.discount])
  }
  await fact("billingReconciliation", reread)
  const reconciled = reread.every(([, total, sum]) => total === sum)
  const { discountRefund } = await facts()
  const discountAndRefundOk = discountRefund.visitBillAfterDiscount[0] === visitExpected
    && discountRefund.labAfterRefund[0] === "Partially Paid" && discountRefund.labAfterRefund[2] === "20.25"
    && discountRefund.labAfterDiscount[0] === "Paid" && discountRefund.labAfterDiscount[3] === "0.00"
  const pharmacyTotal = bills.find((b) => b.prescription)?.total
  const priced = byCategory.consultation.join() === "450.50" && byCategory.laboratory.join() === "320.25" && byCategory.imaging.join() === "610.75"
  const settled = finalStatuses.every(([, status, , , due]) => status === "Paid" && due === "0.00")
  const partialSeen = payments.some((p) => p.status === "Partially Paid")
  const ok = reconciled && priced && duplicates.length === 0 && pharmacyLines.length >= 1 && settled && partialSeen
    && history.every((h) => h[3]) && history.some((h) => h[1] === "refund") && discountAndRefundOk && pharmacyTotal === "8.40"
  await note("15-billing", ok ? "PASS" : "FAIL", JSON.stringify({ reconciled, priced, duplicates, pharmacyLines: pharmacyLines.length, partialSeen, settled, receipts: history.length, finalStatuses, discountAndRefundOk, pharmacyTotal, reread }))
  expect(ok).toBeTruthy()
})

// ---------------------------------------------------------------- patient portal

test("16 the patient sees UHID, visits, results, report, prescription and paid bills after re-login", async ({ page }) => {
  test.setTimeout(150000)
  const { patient, study } = await facts()
  await otpSignIn(page, patient.phone)
  await page.reload()
  const shows = (locator) => locator.first().waitFor({ timeout: 15000 }).then(() => true).catch(() => false)
  const seen = {}
  await shows(page.getByText("My health record"))
  seen.uhid = await shows(page.getByText(patient.uhid))
  seen.diagnosis = await shows(page.getByText(/Acute pharyngitis/))
  seen.imaging = await shows(page.getByText(/No acute cardiopulmonary findings/))
  seen.lab = await shows(page.getByText(/Hb 13.4/))
  await shot(page, "16-patient-dashboard")
  seen.imageFile = (await page.request.get(study.imageUrl)).status()
  await page.goto("/patient/prescriptions")
  seen.prescription = await shows(page.getByText(/Synth Paracetamol/))
  await page.goto("/patient/lab-results")
  seen.labPage = await shows(page.getByText(/Complete Blood Count/))
  await page.goto("/patient/bills")
  await shows(page.getByText(/INV\//))
  const billsText = await page.locator("main").innerText()
  seen.billsPaid = /Paid/.test(billsText) && !/Partially Paid/.test(billsText)
  await shot(page, "16-patient-bills")
  seen.dashboardDue = (await call(page, "get", "/api/billing/invoices/")).body
  seen.dashboardDue = rows(seen.dashboardDue).filter((b) => paise(b.balance_due) > 0).length
  await fact("portal", seen)
  const ok = seen.uhid && seen.diagnosis && seen.imaging && seen.lab && seen.imageFile === 200 && seen.prescription && seen.billsPaid && seen.dashboardDue === 0
  await note("16-portal", ok ? "PASS" : "FAIL", JSON.stringify(seen))
  expect(ok).toBeTruthy()
})

// ---------------------------------------------------------------- inpatient

test("17 admission, ward vitals with a unit, and discharge", async ({ page, browser }) => {
  test.setTimeout(240000)
  const { staff, patient, admin } = await facts()
  const out = {}
  await staffSignIn(page, staff.doctor.username)
  await page.goto("/ipd")
  await page.getByRole("button", { name: "New admission" }).first().click()
  const admit = page.getByRole("dialog", { name: "New admission" })
  await admit.getByLabel(/^Patient/).fill(patient.name)
  await admit.getByRole("button", { name: new RegExp(patient.name) }).first().click()
  const doctorSelect = admit.locator("select").first()
  await doctorSelect.selectOption(await doctorSelect.locator("option", { hasText: `Synthetic Doctor doctor ${RUN}` }).first().getAttribute("value"))
  await admit.locator("textarea").fill("Observation for fever (synthetic)")
  await admit.getByRole("button", { name: "Admit patient" }).click()
  await expect(admit).toBeHidden()

  const adminPage = await (await browser.newContext()).newPage()
  await staffSignIn(adminPage, admin.username)
  await adminPage.goto("/ipd")
  await adminPage.getByRole("tab", { name: /Admissions/ }).click()
  const row = adminPage.getByRole("row", { name: new RegExp(patient.name) })
  await row.getByRole("button", { name: "Allocate bed" }).click()
  const allocate = adminPage.getByRole("dialog", { name: "Allocate bed" })
  const bed = allocate.locator("select")
  await bed.selectOption(await bed.locator("option").nth(1).getAttribute("value"))
  await allocate.getByRole("button", { name: "Allocate" }).click()
  await expect(adminPage.getByText("Bed allocated")).toBeVisible()
  out.admitted = true

  const nurse = await (await browser.newContext()).newPage()
  await staffSignIn(nurse, staff.nurse.username)
  await nurse.goto("/nurses")
  await nurse.getByRole("tablist", { name: "Nursing sections" }).waitFor()
  await nurse.waitForTimeout(1500)
  out.nursePageError = await nurse.getByText(/Could not load/).first().isVisible().catch(() => false)
  out.nurseBillingTab = await nurse.getByRole("tab", { name: "Billing" }).isVisible().catch(() => false)
  await nurse.getByRole("tablist", { name: "Nursing sections" }).getByRole("tab", { name: "Vitals" }).click()
  await nurse.getByRole("button", { name: "+ Record Vitals" }).click()
  const select = nurse.getByLabel(/^Patient/).last()
  await select.selectOption(await select.locator("option", { hasText: patient.name }).first().getAttribute("value"))
  await nurse.getByLabel("Temperature °F").fill("100.4")
  await nurse.getByLabel("Pulse").fill("92")
  await nurse.getByLabel(/Blood Pressure|BP/).first().fill("118/76").catch(() => {})
  await nurse.getByLabel(/SpO/).first().fill("97").catch(() => {})
  await nurse.getByLabel(/Respiratory|Resp/).first().fill("18").catch(() => {})
  await nurse.getByRole("button", { name: "Save Vitals" }).click()
  await expect(nurse.getByRole("row", { name: new RegExp(`${patient.name}.*100\\.4 °F`) }).first()).toBeVisible()
  await shot(nurse, "17-nurse-vitals")
  const assessments = rows((await call(page, "get", `/api/nurses/assessments/?patient=${patient.id}`)).body)
  out.doctorSeesNurse = assessments.map((a) => [a.nurse_name, a.vitals?.temperature, a.vitals?.temperature_unit, Boolean(a.assessed_at)])
  await page.goto("/consultation")
  await page.getByRole("listbox", { name: "Visits" }).getByRole("option", { name: new RegExp(patient.name) }).first().click()
  const obs = page.getByRole("heading", { name: "Nursing observations" }).locator("xpath=ancestor::*[contains(@class,'rounded')][1]")
  out.consultationShowsUnit = await obs.getByText("100.4 °F").first().waitFor({ timeout: 15000 }).then(() => true).catch(() => false)
  await shot(page, "17-doctor-sees-nurse-vitals")

  // Discharge: plan, summary, finalize, final bill, complete.
  await page.goto("/ipd")
  await page.getByRole("tab", { name: /Admissions/ }).click()
  const admissionRow = page.getByRole("row", { name: new RegExp(patient.name) })
  await admissionRow.getByRole("button", { name: "Start discharge" }).click()
  const plan = page.getByRole("dialog", { name: "Start discharge" })
  await plan.getByLabel(/Discharge instructions/).fill("Paracetamol as needed; review in 5 days (synthetic)")
  for (const box of await plan.getByRole("checkbox").all()) await box.check().catch(() => {})
  await plan.getByRole("button", { name: "Start discharge" }).click()
  await expect(plan).toBeHidden()
  await page.getByRole("tab", { name: /Discharges/ }).click()
  await page.getByRole("button", { name: /Write summary/ }).first().click()
  const summary = page.getByRole("dialog", { name: "Discharge summary" })
  await summary.getByLabel(/Clinical summary/).fill("Admitted for fever; improved; discharged stable (synthetic).")
  await summary.getByRole("button", { name: "Save draft" }).click()
  await expect(summary).toBeHidden()
  for (let i = 0; i < 8; i += 1) {
    const box = page.getByRole("checkbox", { checked: false }).first()
    if (!(await box.isVisible().catch(() => false))) break
    await box.check()
    await page.waitForTimeout(600)
  }
  out.checklistTicked = (await page.getByRole("checkbox", { checked: true }).count())
  await page.getByRole("button", { name: "Finalize" }).first().click()
  await page.getByRole("button", { name: "Finalize and sign" }).click()
  await expect(page.getByText("Discharge summary finalized")).toBeVisible()
  await shot(page, "17-discharge-steps")
  const complete = page.getByRole("button", { name: "Complete discharge" }).first()
  out.completeEnabled = await complete.isEnabled().catch(() => false)
  out.dischargeStepsText = (await page.locator("main").innerText()).split("\n").filter((l) => /bill|Bill|sign|Sign|discharge|Discharge/.test(l)).slice(0, 12)
  await fact("inpatient", out)
  const reading = out.doctorSeesNurse.find((a) => a[1] === "100.4" && a[2] === "F")
  out.nurseNameMissing = Boolean(reading && !reading[0])
  const ok = out.admitted && Boolean(reading) && out.consultationShowsUnit
  await note("17-inpatient", ok && !out.nurseNameMissing && !out.nursePageError ? "PASS" : (ok ? "PARTIAL" : "FAIL"), JSON.stringify(out))
  expect(ok).toBeTruthy()
})

test("18 discharge completes after the final bill is settled", async ({ page, browser }) => {
  test.setTimeout(180000)
  const { staff, patient, hospital } = await facts()
  const out = {}
  const billing = await (await browser.newContext()).newPage()
  await staffSignIn(billing, staff.billing.username)
  await billing.goto("/billing")
  const card = billing.getByRole("heading", { name: "Discharge bills" }).locator("xpath=ancestor::*[contains(@class,'rounded')][1]")
  out.bedChargesShown = (await card.innerText().catch(() => "")).match(/Bed charges from the price list: ₹[\d,.]+/)?.[0] || null
  const create = card.getByRole("button", { name: "Create final bill" }).first()
  out.createFinalBill = await create.isVisible().catch(() => false)
  if (out.createFinalBill) {
    await create.click()
    await expect(card.getByText(/Final bill INV/)).toBeVisible({ timeout: 15000 })
  }
  const invoices = rows((await call(billing, "get", `/api/billing/invoices/?hospital=${hospital.id}&patient=${patient.id}`, undefined, hospital.id)).body)
  const final = invoices.find((i) => i.admission && i.is_final)
  out.finalBill = final ? [final.invoice_number, final.total_amount, final.status] : null
  if (final && paise(final.balance_due ?? final.total_amount) > 0) {
    await billing.reload()
    const row = billing.getByRole("row", { name: new RegExp(final.invoice_number.replace(/[/]/g, "\\/")) })
    await row.getByRole("button", { name: "Payment" }).click()
    await billing.locator("input[name=paid]").fill(final.total_amount)
    await billing.locator("select[name=payment]").selectOption("Cash")
    await billing.getByRole("button", { name: "Save Changes" }).click()
    await expect.poll(async () => (await call(billing, "get", `/api/billing/invoices/${final.id}/`, undefined, hospital.id)).body.status, { timeout: 15000 }).toBe("Paid")
    out.finalBillPaid = true
  }
  await shot(billing, "18-final-bill")
  await billing.context().close()

  // A fresh browser context for the doctor (the step's own API context hung after the billing step).
  const doctor = await (await browser.newContext()).newPage()
  await staffSignIn(doctor, staff.doctor.username)
  await doctor.goto("/ipd")
  await doctor.getByRole("tab", { name: /Discharges/ }).click()
  await doctor.getByText("Discharge checklist").first().waitFor({ timeout: 15000 })
  // Each tick saves to the server (the box is disabled while it saves).
  for (const label of ["Medications reconciled", "Patient and family counselled", "Follow-up arranged", "Documents handed over"]) {
    const box = doctor.getByRole("checkbox", { name: label })
    if (await box.isChecked().catch(() => true)) continue
    await expect(box).toBeEnabled({ timeout: 10000 })
    await box.click()
    await expect(box).toBeChecked({ timeout: 10000 })
  }
  out.checklistTicked = await doctor.getByRole("checkbox", { checked: true }).count()
  await doctor.getByText("Ready to complete").waitFor({ timeout: 15000 })
  const complete = doctor.getByRole("button", { name: "Complete discharge" }).first()
  await expect(complete).toBeEnabled({ timeout: 10000 })
  out.completeEnabled = true
  await complete.click()
  const confirmDialog = doctor.getByRole("dialog", { name: "Complete discharge?" })
  await confirmDialog.waitFor({ timeout: 10000 })
  out.confirmShown = true
  await confirmDialog.getByRole("button", { name: "Complete discharge" }).click()
  await doctor.getByText("Discharge completed and bed released").waitFor({ timeout: 20000 })
  out.toast = true
  const admissions = rows((await call(doctor, "get", `/api/ipd/admissions/?patient=${patient.id}`)).body)
  out.admission = admissions.map((a) => [a.id, a.status, a.discharge_date])
  out.pageText = (await doctor.locator("main").innerText()).split("\n").filter((l) => /bill|paid|discharge|sign/i.test(l)).slice(0, 10)
  const page2 = doctor
  await shot(page2, "18-discharge-result")
  await fact("discharge", out)
  const discharged = out.admission.some((a) => a[1] === "Discharged" && a[2])
  await note("18-discharge", discharged ? "PASS" : "FAIL", JSON.stringify(out))
  expect(discharged).toBeTruthy()
})

test("18b the discharged patient sees the discharge in their record", async ({ page }) => {
  const { discharge } = await facts()
  test.skip(!discharge?.admission?.some((a) => a[1] === "Discharged"), "discharge did not complete")
  await reuseSession(page)
  await page.getByText("My health record").waitFor({ timeout: 15000 })
  const shows = (locator) => locator.first().waitFor({ timeout: 15000 }).then(() => true).catch(() => false)
  const seen = {
    discharged: await shows(page.getByText("Discharged", { exact: true })),
    followUp: await shows(page.getByText(/review in 5 days/)),
    wardVitals: await shows(page.getByText(/100\.4 °F/)),
  }
  await shot(page, "18b-patient-discharge")
  await fact("patientDischargeView", seen)
  await note("18b-patient-discharge", seen.discharged ? "PASS" : "FAIL", JSON.stringify(seen))
  expect(seen.discharged).toBeTruthy()
})

// ---------------------------------------------------------------- security

test("19 storage, isolation and audit", async ({ page, browser }) => {
  const { staff, patient, admin, hospital } = await facts()
  const out = {}
  await staffSignIn(page, staff.desk.username)
  const stored = await page.evaluate(() => Object.keys(localStorage))
  out.storageAfterLogin = stored.sort()
  out.profileInStorage = await page.evaluate(() => Boolean(localStorage.getItem("user") || localStorage.getItem("roles") || localStorage.getItem("hospitals")))
  await page.getByRole("button", { name: /^Profile menu for/ }).click()
  await page.getByRole("menuitem", { name: /Logout/ }).click()
  await expect.poll(() => page.evaluate(() => Object.keys(localStorage)), { timeout: 8000 }).not.toContain("hms_session")
  out.storageAfterLogout = (await page.evaluate(() => Object.keys(localStorage))).sort()
  out.anonymousPatients = (await page.request.get(`/api/patients/${patient.id}/`)).status()

  const adminPage = await (await browser.newContext()).newPage()
  await staffSignIn(adminPage, admin.username)
  const logs = rows((await call(adminPage, "get", `/api/audit/audit-logs/?hospital=${hospital.id}`, undefined, hospital.id)).body)
  const actions = [...new Set(logs.map((l) => l.action))]
  out.auditActions = actions.slice(0, 60)
  out.auditCount = logs.length
  const outsider = await (await browser.newContext()).newPage()
  await signIn(outsider, "demo.doctor1", E2E_PASSWORD)
  await expect(outsider).toHaveURL("/")
  out.otherHospitalReadsPatient = (await call(outsider, "get", `/api/patients/${patient.id}/`, undefined, hospital.id)).status
  out.otherHospitalReadsOwnScope = (await call(outsider, "get", `/api/patients/${patient.id}/`, undefined, 1)).status
  await fact("security", out)
  const ok = !out.profileInStorage && !out.storageAfterLogout.includes("selectedHospital") && out.anonymousPatients === 401
    && out.otherHospitalReadsPatient === 403 && [403, 404].includes(out.otherHospitalReadsOwnScope) && out.auditCount > 0
  await note("19-security", ok ? "PASS" : "FAIL", JSON.stringify({ ...out, auditActions: undefined }))
  expect(ok).toBeTruthy()
})

test("99 export the run's facts to the evidence folder", async () => {
  await mkdir(DIR, { recursive: true })
  await copyFile(STATE, `${DIR}/state.json`)
})
