import { describe, expect, it } from "vitest"
import { displayPatientId } from "../utils/patientIdentity.js"

// F1: patients are identified by their UHID once the hospital has issued one.
describe("displayPatientId", () => {
  it("shows the UHID when there is one", () => {
    expect(displayPatientId({ id: 6, uhid: "DCH-2026-000001" })).toBe("DCH-2026-000001")
  })

  it("falls back to the record number", () => {
    expect(displayPatientId({ id: 6, uhid: "" })).toBe("PAT-6")
    expect(displayPatientId({ id: "PAT-17" })).toBe("PAT-17")
  })
})
