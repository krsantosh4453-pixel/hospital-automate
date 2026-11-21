import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// H-14: verified critical values wait on the lab page until a doctor
// acknowledges them with a note. Synthetic data only.
vi.mock("../components/Toast.jsx", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn() }) }))
vi.mock("../services/api.js", () => ({
  default: { laboratory: { tests: { criticalResults: vi.fn(), acknowledgeCritical: vi.fn() } } },
}))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import CriticalResults from "../components/laboratory/CriticalResults.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const CRITICAL = {
  id: 31, name: "CBC", patient_name: "Synthetic Patient", doctor_name: "Dr Synthetic",
  lab_result: {
    has_critical: true,
    flag_details: [
      { parameter: "Hb", value: "6", unit: "g/dL", flag: "LL" },
      { parameter: "WBC", value: "12", unit: "", flag: "H" },
    ],
  },
}

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))

async function render(props) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<LanguageProvider><CriticalResults hospitalId={4} {...props} /></LanguageProvider>))
  await flush()
}

const button = (label) => [...host.querySelectorAll("button")].find((b) => b.textContent.trim() === label)

describe("Critical results panel (H-14)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("shows only the critical parameters and lets a doctor acknowledge with a note", async () => {
    api.laboratory.tests.criticalResults.mockResolvedValueOnce([CRITICAL]).mockResolvedValueOnce([])
    api.laboratory.tests.acknowledgeCritical.mockResolvedValue({})
    const promptText = vi.fn().mockResolvedValue("  Called ward, transfusion ordered ")
    const onChange = vi.fn()
    await render({ canAcknowledge: true, promptText, onChange })

    expect(api.laboratory.tests.criticalResults).toHaveBeenCalledWith(4)
    expect(host.textContent).toContain("Synthetic Patient · CBC")
    expect(host.textContent).toContain("Hb 6 g/dL (LL)")
    expect(host.textContent).not.toContain("WBC")

    await act(async () => button("Acknowledge").click())
    await flush()
    expect(api.laboratory.tests.acknowledgeCritical).toHaveBeenCalledWith(31, "Called ward, transfusion ordered")
    expect(onChange).toHaveBeenCalled()
    expect(host.textContent).toBe("")
  })

  it("does not acknowledge when the note is cancelled", async () => {
    api.laboratory.tests.criticalResults.mockResolvedValue([CRITICAL])
    await render({ canAcknowledge: true, promptText: vi.fn().mockResolvedValue(null) })
    await act(async () => button("Acknowledge").click())
    await flush()
    expect(api.laboratory.tests.acknowledgeCritical).not.toHaveBeenCalled()
  })

  it("shows the list without the button to staff who cannot acknowledge", async () => {
    api.laboratory.tests.criticalResults.mockResolvedValue({ results: [CRITICAL] })
    await render({ canAcknowledge: false, promptText: vi.fn() })
    expect(host.textContent).toContain("Hb 6 g/dL (LL)")
    expect(button("Acknowledge")).toBeUndefined()
  })

  it("says so when the list cannot be loaded instead of showing nothing", async () => {
    api.laboratory.tests.criticalResults.mockRejectedValue(new Error("Network down"))
    await render({ canAcknowledge: true, promptText: vi.fn() })
    expect(host.querySelector("[role=alert]").textContent).toContain("Network down")
  })
})
