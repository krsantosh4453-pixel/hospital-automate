// @vitest-environment node
import { describe, expect, it } from "vitest"
import { ER_ACTIONS, patientLink } from "../components/emergency/erActionList.js"

// Spec Part 4 §13: the emergency row action menu.
const SPEC = [
  "Service order", "Allergy", "Investigation result", "Transfer to in-patient", "Billing", "Bill preview",
  "Discharge", "Emergency forms", "Discharge summary", "Update details", "Vitals", "Patient medical record",
  "Doctor notes", "Bed transfer", "Sample collection", "ER blood request", "ER blood receive", "Consent forms",
  "Generic consent form", "Sample dispatch", "ER drug / consumable request", "ER drug / consumable receive",
  "Medical certificate", "Charge slip details",
]

describe("ER action menu", () => {
  it("offers every one of the 24 actions in the specification", () => {
    expect(ER_ACTIONS.map((a) => a.label).sort()).toEqual([...SPEC].sort())
  })

  it("hands the patient to the target module in the URL", () => {
    const visit = { patient: 7, patient_name: "Asha Devi" }
    const byId = Object.fromEntries(ER_ACTIONS.map((a) => [a.id, a]))

    expect(patientLink(byId["blood-request"], visit)).toBe("/blood-bank?patient=7&q=Asha+Devi")
    expect(patientLink(byId["update-details"], visit)).toBe("/patients?patient=7&q=Asha+Devi&edit=7")
    expect(patientLink(byId["medical-record"], visit)).toBe("/patients?patient=7&q=Asha+Devi&record=7")
  })
})
