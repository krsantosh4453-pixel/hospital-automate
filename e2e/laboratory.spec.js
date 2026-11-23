import { expect, test } from "@playwright/test"
import { pickPatient, signInAs } from "./helpers.js"

// A doctor orders a test; lab staff take it through every stage to release,
// and the doctor then reads the released result.
const PATIENT = "Demo Ravi (Cardiology OPD)"
const TEST = "Thyroid Profile"
const RESULT = `TSH 2.1 mIU/L (run ${Date.now().toString(36)})`

const STAGES = [
  ["Collect Sample", "Collected"],
  ["Dispatch Sample", "Dispatched"],
  ["Receive in Lab", "Received"],
  ["Start Processing", "Processing"],
]

test("doctor orders a test, lab releases the result, doctor reads it", async ({ browser }) => {
  // Three sign-ins, eight stages and a rejection: allow for a loaded machine.
  test.setTimeout(90000)
  const doctor = await (await browser.newContext()).newPage()
  await signInAs(doctor, "demo.doctor1")
  await doctor.goto("/laboratory")
  await doctor.getByRole("button", { name: "New lab order" }).first().click()
  const order = doctor.getByRole("dialog", { name: "New lab order" })
  await pickPatient(order, PATIENT)
  await order.getByLabel("Test").selectOption({ label: TEST })
  await order.getByLabel("Priority").selectOption("Urgent")
  await order.getByRole("button", { name: "Create order" }).click()
  await expect(order).toBeHidden()

  const newest = doctor.getByRole("row", { name: new RegExp(`${TEST} Urgent Ordered`) }).first()
  // The order cell runs the id into the date ("LAB-13/11/2026"); the View button names it alone.
  const viewLabel = await newest.getByRole("button", { name: /^View LAB-\d+$/ }).getAttribute("aria-label")
  const orderId = viewLabel.replace("View ", "")

  const lab = await (await browser.newContext()).newPage()
  await signInAs(lab, "demo.lab")
  await lab.goto("/laboratory")
  const row = lab.getByRole("row", { name: new RegExp(`^${orderId} `) })
  for (const [action, stage] of STAGES) {
    await row.getByRole("button", { name: action }).click()
    await expect(row.getByRole("cell").nth(4)).toContainText(stage)
  }

  await row.getByRole("button", { name: "Enter Result" }).click()
  const resultDialog = lab.getByRole("dialog", { name: new RegExp(`Result for ${TEST}`) })
  await resultDialog.getByRole("textbox").fill(RESULT)
  await resultDialog.getByRole("button", { name: "Save" }).click()
  await expect(row.getByRole("cell").nth(4)).toContainText("Result Entered")

  // BUG-06: a different authorised person verifies (maker-checker). The demo
  // hospital has one lab technician, so its administrator verifies.
  const checker = await (await browser.newContext()).newPage()
  await signInAs(checker, "demo.admin")
  await checker.goto("/laboratory")
  const checkerRow = checker.getByRole("row", { name: new RegExp(`^${orderId} `) })

  // L-1: the checker first sends a wrong entry back; the technician enters it again.
  await checkerRow.getByRole("button", { name: "Reject Result" }).click()
  const rejectDialog = checker.getByRole("dialog", { name: /Reject the result/ })
  await rejectDialog.getByRole("textbox").fill("Units missing, please re-enter")
  await rejectDialog.getByRole("button", { name: "Reject Result" }).click()
  await expect(checkerRow.getByRole("cell").nth(4)).toContainText("Processing")

  await lab.reload()
  await row.getByRole("button", { name: "Enter Result" }).click()
  await resultDialog.getByRole("textbox").fill(RESULT)
  await resultDialog.getByRole("button", { name: "Save" }).click()
  await expect(row.getByRole("cell").nth(4)).toContainText("Result Entered")
  await checker.reload()

  await checkerRow.getByRole("button", { name: "Verify Result" }).click()
  await expect(checkerRow.getByRole("cell").nth(4)).toContainText("Verified")
  await checkerRow.getByRole("button", { name: "Release Result" }).click()
  await expect(checkerRow.getByRole("cell").nth(4)).toContainText("Released")

  await doctor.reload()
  await doctor.getByRole("tab", { name: /Released/ }).click()
  await doctor.getByRole("button", { name: `View ${orderId}` }).click()
  const view = doctor.getByRole("dialog", { name: "Laboratory order" })
  await expect(view.getByText(RESULT)).toBeVisible()
  await expect(view.getByText("Released")).toBeVisible()
})

test("lab staff find a walk-in patient by search and place the order", async ({ page }) => {
  await signInAs(page, "demo.lab")
  await page.goto("/laboratory")
  await page.getByRole("button", { name: "New lab order" }).first().click()
  const order = page.getByRole("dialog", { name: "New lab order" })
  // Lab Staff may not browse patients: the picker is empty until they search.
  await order.getByLabel(/^Patient/).fill("Demo Ravi")
  // The result tells patients apart by UHID and a masked phone, never the full number.
  const walkIn = order.getByRole("button", { name: /Demo Ravi \(Cardiology OPD\).*3011/ })
  await expect(walkIn).toContainText("******3011")
  await walkIn.click()
  await order.getByLabel("Test").selectOption({ label: "Blood Sugar" })
  await order.getByLabel("Priority").selectOption("Urgent")
  await order.getByRole("button", { name: "Create order" }).click()

  await expect(order).toBeHidden()
  await expect(page.getByRole("row", { name: /Blood Sugar Urgent Ordered/ }).first()).toBeVisible()
})
