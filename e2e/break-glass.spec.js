import { expect, test } from "@playwright/test"
import { signInAs } from "./helpers.js"

// G-8: an Orthopaedics doctor cannot open a Ward A patient of another doctor.
// They open break-glass access with a reason, can then read the record, and
// the administrator signs the grant off on the same screen.
const PATIENT = "Demo Kiran (Ward A)"
const REASON = `Collapsed in corridor, treating doctor unreachable E2E${Date.now().toString(36).toUpperCase()}`

test("doctor opens emergency access and an administrator reviews it", async ({ browser }) => {
  const admin = await (await browser.newContext()).newPage()
  await signInAs(admin, "demo.admin")
  const found = await (await admin.request.get(`/api/patients/?search=${encodeURIComponent("Demo Kiran")}`)).json()
  const patientId = (found.results || found).find((p) => p.name === PATIENT).id

  const doctor = await (await browser.newContext()).newPage()
  await signInAs(doctor, "demo.doctor2")
  expect((await doctor.request.get(`/api/patients/${patientId}/`)).status()).toBe(404)

  await doctor.goto("/emergency-access")
  await doctor.getByPlaceholder("P012").fill(`P${String(patientId).padStart(3, "0")}`)
  await doctor.getByLabel(/^Reason/).fill(REASON)
  await doctor.getByRole("button", { name: "Open access" }).click()
  const grant = doctor.getByRole("row", { name: new RegExp(REASON) })
  await expect(grant).toContainText(PATIENT)
  await expect(grant).toContainText("Active")
  expect((await doctor.request.get(`/api/patients/${patientId}/`)).status()).toBe(200)

  await admin.goto("/emergency-access")
  const pending = admin.getByRole("row", { name: new RegExp(REASON) })
  await expect(pending).toContainText("demo.doctor2")
  await pending.getByRole("button", { name: "Review" }).click()
  await admin.getByLabel("Review note (what you checked)").fill("Checked with the ward sister: genuine emergency.")
  await admin.getByRole("button", { name: "Sign off" }).click()
  await expect(pending).toHaveCount(0)

  await admin.getByRole("button", { name: "All" }).click()
  await expect(admin.getByRole("row", { name: new RegExp(REASON) })).toContainText("genuine emergency")
})
