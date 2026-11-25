import { describe, expect, it } from "vitest"
import { opdTriagePatients } from "../utils/opdTriage.js"

const token = (over) => ({ patient: 1, hospital: 3, token_number: 1, token_date: "2026-11-25", status: "Waiting",
  patient_name: "Synthetic OPD", doctor_name: "Dr Synthetic", ...over })

describe("opdTriagePatients (MF-012)", () => {
  it("offers today's patients who have not gone in to the doctor, in token order", () => {
    const rows = opdTriagePatients([
      token({ patient: 2, token_number: 2, status: "Called", patient_name: "Second" }),
      token({ patient: 1, token_number: 1 }),
      token({ patient: 3, token_number: 3, status: "In Consultation" }),
      token({ patient: 4, token_number: 4, status: "Completed" }),
      token({ patient: 5, token_number: 5, token_date: "2026-11-24" }),
    ], "2026-11-25")

    expect(rows.map((row) => [row.id, row.token, row.ward])).toEqual([[1, 1, "OPD"], [2, 2, "OPD"]])
    expect(rows[0]).toMatchObject({ admissionId: null, hospitalId: 3, name: "Synthetic OPD", doctor: "Dr Synthetic" })
  })

  it("leaves out patients already listed from the ward and repeats", () => {
    const rows = opdTriagePatients([token({ patient: 7 }), token({ patient: 7, token_number: 2 }), token({ patient: 8 })],
      "2026-11-25", [{ id: 8 }])

    expect(rows.map((row) => row.id)).toEqual([7])
  })
})
