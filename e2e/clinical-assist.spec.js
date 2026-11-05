import { expect, test } from "@playwright/test"
import { signInAs } from "./helpers.js"

// D6: the doctor picks an ICD-10 code while typing a diagnosis.
// K6: an AI discharge draft is built from the admission's records for the
// doctor to review; nothing is saved to the discharge summary by it.

test("doctor picks an ICD-10 code from the diagnosis suggestions", async ({ page }) => {
  await signInAs(page, "demo.doctor1")
  await page.goto("/consultation")
  await page.getByRole("listbox", { name: "Visits" }).getByRole("option").first().click()
  await page.getByRole("tab", { name: /Diagnoses/ }).click()

  await page.getByRole("combobox", { name: /Diagnosis/ }).fill("E11")
  const suggestion = page.getByRole("option", { name: /E11\.9/ })
  await expect(suggestion).toContainText("Type 2 diabetes mellitus")
  await suggestion.click()
  await expect(page.getByRole("combobox", { name: /Diagnosis/ })).toHaveValue("Type 2 diabetes mellitus without complications")
  await expect(page.getByLabel(/^ICD-10 code/)).toHaveValue("E11.9")
})

test("doctor gets a discharge draft to review, built from the admission's records", async ({ page }) => {
  await signInAs(page, "demo.doctor1")
  const api = page.request
  const csrf = (await (await api.get("/api/auth/csrf/")).json()).csrfToken
  const found = await (await api.get("/api/ipd/admissions/")).json()
  const admission = (found.results || found).find((a) => a.status === "Admitted")
  const headers = { "X-CSRFToken": csrf, "X-Hospital-ID": String(admission.hospital) }

  const drafted = await api.post(`/api/ai/discharge/admissions/${admission.id}/draft/`, { headers })
  expect(drafted.status()).toBe(201)
  const draft = await drafted.json()
  expect(draft.text.length).toBeGreaterThan(0)
  expect(draft.notice).toContain("AI-assisted draft")
  // No AI provider in the test stack: the draft is assembled from the records.
  expect(draft.source).toBe("records")

  const reviewed = await api.post(`/api/ai/discharge/admissions/${admission.id}/draft-review/`, {
    headers, data: { draft_id: draft.draft_id, outcome: "edited" },
  })
  expect(reviewed.status()).toBe(200)
  // The draft never writes the discharge summary itself.
  const summaries = await (await api.get("/api/ipd/discharge-summaries/")).json()
  expect((summaries.results || summaries).filter((s) => s.admission === admission.id)).toHaveLength(0)
})
