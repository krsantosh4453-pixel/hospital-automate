import { describe, expect, it } from "vitest"
import { appointmentRef } from "../utils/appointmentRef.js"

describe("appointmentRef (P5-07)", () => {
  it("formats the reference the front desk searches by", () => {
    expect(appointmentRef(7)).toBe("A007")
    expect(appointmentRef("42")).toBe("A042")
    expect(appointmentRef(12345)).toBe("A12345")
  })

  it("is empty without an id", () => {
    expect(appointmentRef(undefined)).toBe("")
    expect(appointmentRef(null)).toBe("")
  })
})
