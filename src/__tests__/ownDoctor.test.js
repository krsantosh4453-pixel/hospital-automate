import { describe, expect, it } from "vitest"
import { ownDoctorId } from "../utils/ownDoctor.js"

// BUG-013: the signed-in doctor is the default doctor on orders and prescriptions.
describe("ownDoctorId", () => {
  const doctors = [{ id: 4, user: 11 }, { id: 9, user: 12 }, { id: 15, user: null }]

  it("finds the signed-in user's own doctor record", () => {
    expect(ownDoctorId(doctors, { id: 12 })).toBe("9")
    expect(ownDoctorId(doctors, { user: { id: 11 } })).toBe("4")
  })

  it("leaves the field empty for anyone who is not one of these doctors", () => {
    expect(ownDoctorId(doctors, { id: 99 })).toBe("")
    expect(ownDoctorId(doctors, null)).toBe("")
    expect(ownDoctorId([], { id: 11 })).toBe("")
  })
})
