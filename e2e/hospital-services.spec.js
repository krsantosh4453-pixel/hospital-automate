import { expect, test } from "@playwright/test"
import { signInAs } from "./helpers.js"

// J5/J6: a theatre is booked and run, an ambulance call is dispatched and
// completed, and a leave request is decided by a manager.
const RUN = Date.now().toString(36).toUpperCase()

async function open(page, user, tab) {
  await signInAs(page, user)
  await page.goto("/services")
  await page.getByRole("tab", { name: tab }).click()
}

async function choose(dialog, label, text) {
  const select = dialog.getByRole("combobox", { name: label })
  const option = select.locator("option", { hasText: text })
  await option.first().waitFor({ state: "attached" })
  await select.selectOption(await option.first().getAttribute("value"))
}

test("theatre booked by a doctor, refused twice, then started and completed", async ({ browser }) => {
  const manager = await (await browser.newContext()).newPage()
  await open(manager, "demo.manager", "Operation theatre")
  await manager.getByRole("button", { name: "Add theatre" }).click()
  await manager.getByRole("dialog").getByLabel(/^Name/).fill(`OT ${RUN}`)
  await manager.getByRole("dialog").getByRole("button", { name: "Save" }).click()
  await expect(manager.getByRole("cell", { name: `OT ${RUN}`, exact: true })).toBeVisible()

  const doctor = await (await browser.newContext()).newPage()
  await open(doctor, "demo.doctor1", "Operation theatre")
  const book = async () => {
    await doctor.getByRole("button", { name: "Book theatre" }).click()
    const dialog = doctor.getByRole("dialog")
    await choose(dialog, "Theatre", `OT ${RUN}`)
    await choose(dialog, "Surgeon", "Dr")
    await dialog.getByPlaceholder("Search by name or phone").fill("Kiran")
    await choose(dialog, "Patient", "Demo Kiran")
    await dialog.getByLabel(/^Procedure/).fill(`Hernia repair ${RUN}`)
    await dialog.getByLabel(/^Starts/).fill("2030-01-15T09:00")
    await dialog.getByLabel(/^Ends/).fill("2030-01-15T11:00")
    await dialog.getByRole("button", { name: "Save" }).click()
    return dialog
  }
  await expect(await book()).toBeHidden()
  const row = doctor.getByRole("row", { name: new RegExp(`Hernia repair ${RUN}`) })
  await expect(row).toContainText("Scheduled")
  const second = await book()
  await expect(second).toContainText("is booked from")
  await second.getByRole("button", { name: "Cancel" }).click()

  const nurse = await (await browser.newContext()).newPage()
  await open(nurse, "demo.nurse", "Operation theatre")
  const nurseRow = nurse.getByRole("row", { name: new RegExp(`Hernia repair ${RUN}`) })
  await nurseRow.getByRole("button", { name: "Start" }).click()
  await expect(nurseRow).toContainText("In progress")
  await nurseRow.getByRole("button", { name: "Complete" }).click()
  await expect(nurseRow).toContainText("Completed")
})

test("ambulance call is dispatched and completed, and leave is approved", async ({ browser }) => {
  const manager = await (await browser.newContext()).newPage()
  await open(manager, "demo.manager", "Ambulance")
  await manager.getByRole("button", { name: "Add ambulance" }).click()
  const fleet = manager.getByRole("dialog")
  await fleet.getByLabel(/^Vehicle number/).fill(`MH${RUN}`)
  await fleet.getByRole("combobox", { name: "Type" }).selectOption("ALS")
  await fleet.getByRole("button", { name: "Save" }).click()

  const desk = await (await browser.newContext()).newPage()
  await open(desk, "demo.desk.main", "Ambulance")
  await desk.getByRole("button", { name: "New call" }).click()
  const call = desk.getByRole("dialog")
  await call.getByLabel(/^Caller name/).fill(`Caller ${RUN}`)
  await call.getByLabel(/^Caller phone/).fill("9000005555")
  await call.getByLabel(/^Pickup address/).fill("Sector 9")
  await call.getByLabel(/^Destination/).fill("Emergency")
  await call.getByRole("button", { name: "Save" }).click()
  const trip = desk.getByRole("row", { name: new RegExp(`Caller ${RUN}`) })
  await trip.getByRole("button", { name: "Dispatch" }).click()
  await choose(desk.getByRole("dialog"), "Ambulance", `MH${RUN}`)
  await desk.getByRole("dialog").getByRole("button", { name: "Save" }).click()
  await expect(trip).toContainText("Dispatched")
  await trip.getByRole("button", { name: "Complete" }).click()
  await expect(trip).toContainText("Completed")

  const nurse = await (await browser.newContext()).newPage()
  await open(nurse, "demo.nurse", "Leave")
  await nurse.getByRole("button", { name: "Apply for leave" }).click()
  const form = nurse.getByRole("dialog")
  await form.getByRole("combobox", { name: "Type" }).selectOption("Casual")
  await form.getByLabel(/^From/).fill("2030-02-01")
  await form.getByLabel(/^To/).fill("2030-02-02")
  await form.getByLabel(/^Reason/).fill(`Family function ${RUN}`)
  await form.getByRole("button", { name: "Save" }).click()
  await expect(nurse.getByRole("row", { name: /2030-02-01/ })).toContainText("Pending")

  await manager.getByRole("tab", { name: "Leave" }).click()
  const request = manager.getByRole("row", { name: /2030-02-01/ })
  await request.getByRole("button", { name: "Approve" }).click()
  await expect(request).toContainText("Approved")
})
