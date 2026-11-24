import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Prompt 4 (BUG-005 / INT-001): ward vitals a nurse records reach the doctor,
// and a temperature is never shown without its unit.
vi.mock("../services/api.js", () => ({ default: { nurses: { assessments: { list: vi.fn() } } } }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import { formatTemperature } from "../utils/temperature.js"
import NursingObservations from "../components/clinical/NursingObservations.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe("formatTemperature", () => {
  it("always names the unit", () => {
    expect(formatTemperature("98.6", "F")).toBe("98.6 °F")
    expect(formatTemperature("37.2", "C")).toBe("37.2 °C")
  })

  it("never guesses a unit for an older reading that has none (TEST 10)", () => {
    expect(formatTemperature("98.6", undefined)).toBe("98.6 (unit not recorded)")
    expect(formatTemperature("98.6", "")).toBe("98.6 (unit not recorded)")
  })

  it("shows a dash when nothing was measured", () => {
    expect(formatTemperature("", "F")).toBe("—")
    expect(formatTemperature(null, null)).toBe("—")
  })
})

describe("NursingObservations (doctor's Vitals tab)", () => {
  let host
  let root
  beforeEach(() => {
    vi.clearAllMocks()
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
  })
  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  async function render(patientId = 3) {
    await act(async () => {
      root.render(<LanguageProvider><NursingObservations patientId={patientId} /></LanguageProvider>)
    })
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)))
  }

  it("lists the nurse's readings with unit, nurse and time (TEST 6, 9)", async () => {
    api.nurses.assessments.list.mockResolvedValue([
      { id: 1, nurse_name: "Synthetic Nurse A", assessed_at: "2026-11-24T07:17:11Z",
        vitals: { temperature: "98.6", temperature_unit: "F", bp: "120/80", pulse: "72", spo2: "98", respiratory_rate: "16" } },
      { id: 2, nurse_name: "Synthetic Nurse B", assessed_at: "2026-11-24T06:00:00Z", vitals: { temperature: "99.1" } },
      { id: 3, nurse_name: "Synthetic Nurse A", assessed_at: "2026-11-24T05:00:00Z", vitals: {} },
    ])
    await render()

    expect(api.nurses.assessments.list).toHaveBeenCalledWith(undefined, 3)
    expect(host.textContent).toContain("98.6 °F")
    expect(host.textContent).toContain("99.1 (unit not recorded)")
    expect(host.textContent).toContain("Synthetic Nurse A")
    expect(host.textContent).toContain("120/80")
    expect(host.querySelectorAll("tbody tr")).toHaveLength(2)
  })

  it("says so when there are none, and when they cannot be loaded", async () => {
    api.nurses.assessments.list.mockResolvedValue([])
    await render()
    expect(host.textContent).toContain("No nursing observations")

    api.nurses.assessments.list.mockRejectedValue(new Error("You do not have permission to perform this action."))
    await render(4)
    expect(host.textContent).toContain("could not be loaded")
  })
})
