import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useRefreshTick } from "../hooks/useRefreshTick.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true
let root
let tick
function Probe() {
  tick = useRefreshTick(1000)
  return null
}
const setVisibility = (state) => Object.defineProperty(document, "visibilityState", { configurable: true, get: () => state })

beforeEach(() => {
  vi.useFakeTimers()
  setVisibility("visible")
  root = createRoot(document.createElement("div"))
  act(() => root.render(<Probe />))
})
afterEach(() => {
  act(() => root.unmount())
  vi.useRealTimers()
})

describe("useRefreshTick (MF-010)", () => {
  it("ticks on the interval while the page is visible", () => {
    expect(tick).toBe(0)
    act(() => vi.advanceTimersByTime(2000))
    expect(tick).toBe(2)
  })

  it("does not tick while hidden, and ticks when the patient returns", () => {
    setVisibility("hidden")
    act(() => vi.advanceTimersByTime(3000))
    expect(tick).toBe(0)

    setVisibility("visible")
    act(() => document.dispatchEvent(new Event("visibilitychange")))
    expect(tick).toBe(1)
  })
})
