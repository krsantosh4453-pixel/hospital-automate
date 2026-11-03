import { expect, test } from "@playwright/test"
import { signInAs } from "./helpers.js"

// The nurse registers two ER arrivals (the second used to fail on a duplicate
// visit number), triages one up to Critical, and the board puts it first.
const COMPLAINT = `Head injury after fall ${Date.now().toString(36)}`

async function pickOption(select, text) {
  const value = await select.locator("option", { hasText: text }).first().getAttribute("value")
  await select.selectOption(value)
}

async function registerVisit(page, patient, level) {
  await page.getByRole("button", { name: "New ER visit" }).first().click()
  const dialog = page.getByRole("dialog", { name: "New emergency visit" })
  await pickOption(dialog.getByLabel("Patient"), patient)
  await dialog.getByLabel("Initial triage level").selectOption({ label: level })
  await dialog.getByRole("button", { name: "Register visit" }).click()
  await expect(dialog).toBeHidden()
}

test("nurse registers two arrivals and triage moves the worse one to the top", async ({ page }) => {
  await signInAs(page, "demo.nurse")
  await page.goto("/emergency")

  await registerVisit(page, "Demo Kiran (Ward A)", "Urgent (< 30 min)")
  await registerVisit(page, "Demo Sunil (Ortho OPD)", "Non-Urgent (< 120 min)")

  const board = page.getByRole("table", { name: /Active emergency visits/ })
  const sunil = board.getByRole("row", { name: /Demo Sunil/ })
  await expect(sunil.getByRole("cell").first()).toHaveText("Non-Urgent")
  await expect(board.getByRole("row").nth(1)).toContainText("Demo Kiran")

  await sunil.getByRole("button", { name: "Triage" }).click()
  const triage = page.getByRole("dialog", { name: "Triage" })
  await triage.getByLabel("Chief complaint").fill(COMPLAINT)
  await triage.getByLabel("Pain score").fill("8")
  await triage.getByLabel("Glasgow Coma Scale").fill("11")
  await triage.getByLabel("Triage level").selectOption({ label: "Critical (Immediate)" })
  await triage.getByLabel("Triaged by").selectOption({ label: "Nurse Priya" })
  await triage.getByRole("button", { name: "Complete triage" }).click()
  await expect(triage).toBeHidden()

  await expect(sunil.getByRole("cell").first()).toHaveText("Critical")
  await expect(sunil.getByRole("cell").nth(3)).toHaveText("Waiting")
  await expect(board.getByRole("row").nth(1)).toContainText("Demo Sunil")

  await page.getByRole("tab", { name: /Triage log/ }).click()
  const logRow = page.getByRole("row", { name: new RegExp(COMPLAINT) })
  await expect(logRow).toContainText("Critical")
})
