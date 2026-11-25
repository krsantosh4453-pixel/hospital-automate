import { expect, test } from "./fixtures.js"
import { E2E_PASSWORD, signInAs } from "./helpers.js"

// Prompt 4 (E2E audit BUG-003, BUG-005/INT-001, BUG-006, BUG-007), against the
// real e2e backend. Synthetic seed data only (Demo City Hospital).

const SHOTS = "reports/e2e-evidence/prompt-4"
test.describe.configure({ mode: "serial" })

const isoDay = (date) => date.toISOString().slice(0, 10)
function nextWeekday(target) { // 0 = Sunday … 6 = Saturday (JS numbering)
  const day = new Date()
  day.setUTCHours(12, 0, 0, 0)
  do day.setUTCDate(day.getUTCDate() + 1)
  while (day.getUTCDay() !== target)
  return isoDay(day)
}

async function patientSignsIn(page) {
  await page.goto("/patient-login")
  await page.getByRole("tab", { name: "Email" }).click()
  await page.getByLabel("Email").first().fill("demo.patient@example.test")
  await page.getByLabel("Password").fill(E2E_PASSWORD)
  await page.getByRole("button", { name: "Sign In" }).click()
  await expect(page).toHaveURL(/\/patient$/)
}

test("a doctor's day off offers no slots and cannot be booked; a working day can (BUG-003)", async ({ page }) => {
  await patientSignsIn(page)
  await page.goto("/patient/appointments?book=1")
  const dialog = page.getByRole("dialog", { name: "Book an appointment" })
  const doctorSelect = dialog.getByLabel(/^Doctor/)
  await expect(doctorSelect.locator("option", { hasText: "Dr Asha Mehta" })).toHaveCount(1)
  await doctorSelect.selectOption(await doctorSelect.locator("option", { hasText: "Dr Asha Mehta" }).getAttribute("value"))
  await dialog.getByLabel(/^Date/).fill(nextWeekday(0))

  await expect(dialog).toContainText("does not see patients on Sundays")
  await expect(dialog.getByLabel(/^Time/).locator("option")).toHaveCount(1)
  await page.screenshot({ path: `${SHOTS}/1-sunday-no-slots.png` })

  // The same request straight to the API is refused too.
  const csrf = (await (await page.request.get("/api/auth/csrf/")).json()).csrfToken
  const options = await (await page.request.get("/api/appointments/booking-options/?hospital=1")).json()
  const doctor = options.doctors.find((d) => d.name === "Dr Asha Mehta")
  expect(doctor.working_days).toEqual([0, 1, 2, 3, 4, 5])
  const refused = await page.request.post("/api/appointments/book/", {
    headers: { "X-CSRFToken": csrf },
    data: { doctor: doctor.id, appointment_date: nextWeekday(0), appointment_time: "10:00" },
  })
  expect(refused.status()).toBe(400)
  expect(await refused.text()).toContain("does not see patients on Sundays")

  await dialog.getByLabel(/^Date/).fill(nextWeekday(3))
  const time = dialog.getByLabel(/^Time/)
  await expect(time.locator("option")).not.toHaveCount(1)
  await time.selectOption({ index: 1 })
  await dialog.getByRole("button", { name: "Confirm booking" }).click()
  await expect(page.getByText(/Booked with Dr Asha Mehta/)).toBeVisible()
})

test("the doctor sees the vitals a nurse recorded, with the unit (BUG-005, INT-001)", async ({ page, browser }) => {
  await signInAs(page, "demo.nurse")
  await page.goto("/nurses")
  await page.getByRole("tablist", { name: "Nursing sections" }).getByRole("tab", { name: "Vitals" }).click()
  await page.getByRole("button", { name: "+ Record Vitals" }).click()
  const patientSelect = page.getByLabel(/^Patient/).last()
  await patientSelect.selectOption(await patientSelect.locator("option", { hasText: "Demo Kiran" }).first().getAttribute("value"))
  await page.getByLabel("Temperature °F").fill("99.1")
  await page.getByLabel("Pulse").fill("88")
  await page.getByRole("button", { name: "Save Vitals" }).click()
  await expect(page.getByRole("row", { name: /Demo Kiran.*99\.1 °F/ }).first()).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/2-nurse-saved-with-unit.png` })

  const doctorPage = await (await browser.newContext()).newPage()
  await signInAs(doctorPage, "demo.doctor1")
  // An OPD visit with this doctor puts the ward patient in their care.
  const csrf = (await (await doctorPage.request.get("/api/auth/csrf/")).json()).csrfToken
  const kiran = ((await (await doctorPage.request.get("/api/patients/?hospital=1&search=Demo%20Kiran")).json()).results || [])[0]
  const doctorId = (await (await doctorPage.request.get("/api/encounters/visits/")).json()).results?.[0]?.doctor
  await doctorPage.request.post("/api/encounters/visits/", {
    headers: { "X-CSRFToken": csrf, "X-Hospital-ID": "1" },
    data: { hospital: 1, patient: kiran.id, doctor: doctorId, visit_type: "OPD" },
  })
  await doctorPage.goto("/consultation")
  await doctorPage.getByRole("listbox", { name: "Visits" }).getByRole("option", { name: /Demo Kiran/ }).first().click()
  const observations = doctorPage.getByRole("heading", { name: "Nursing observations" }).locator("xpath=ancestor::*[contains(@class,'rounded')][1]")
  await expect(observations).toContainText("99.1 °F")
  await expect(observations).toContainText("88")
  await doctorPage.screenshot({ path: `${SHOTS}/3-doctor-sees-nurse-vitals.png`, fullPage: true })
})

test("pharmacy returns search stays up while typing, and errors are readable (BUG-006, BUG-007)", async ({ page }) => {
  const pageErrors = []
  page.on("pageerror", (error) => pageErrors.push(error.message))
  await signInAs(page, "demo.pharmacist")
  await page.goto("/pharmacy")
  const search = page.getByPlaceholder("Search patient, medicine or SALE-number")
  for (const text of ["D", "Do", "Dolo", "", "zzzz", "SALE-"]) await search.fill(text)
  await search.fill("")
  expect(pageErrors).toEqual([])
  await page.screenshot({ path: `${SHOTS}/4-pharmacy-search.png` })

  // The server's own answer to a bad quantity reads as a sentence, never a Python repr.
  const csrf = (await (await page.request.get("/api/auth/csrf/")).json()).csrfToken
  // Body validation runs before any lookup, so synthetic ids are enough (the seed has no prescription).
  const response = await page.request.post("/api/pharmacy-sales/dispense-prescription/", {
    headers: { "X-CSRFToken": csrf, "X-Hospital-ID": "1" },
    data: { prescription: 1, partial: true, lines: [{ item: 1, medicine: 1, quantity: -1 }] },
  })
  expect(response.status()).toBe(400)
  const body = await response.json()
  expect(body.message).not.toMatch(/ErrorDetail|\{|\[|code=/)
  expect(body.message).toMatch(/Line 1, quantity: /)
})
