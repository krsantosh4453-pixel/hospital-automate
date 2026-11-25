import { describe, expect, it } from "vitest"
import { visitStatusShown } from "../utils/visitQueueStatus.js"

describe("visitStatusShown (BUG-011)", () => {
  it("shows the queue's word while a waiting visit's patient has been called", () => {
    expect(visitStatusShown("Waiting", "Called")).toBe("Called")
    expect(visitStatusShown("Waiting", "Acknowledged")).toBe("Acknowledged")
    expect(visitStatusShown("Waiting", "Ready")).toBe("Ready")
  })

  it("keeps the visit's own status otherwise", () => {
    expect(visitStatusShown("Waiting", "Waiting")).toBe("Waiting")
    expect(visitStatusShown("Waiting", null)).toBe("Waiting")
    expect(visitStatusShown("In Consultation", "Called")).toBe("In Consultation")
    expect(visitStatusShown("Completed", "Completed")).toBe("Completed")
  })
})
