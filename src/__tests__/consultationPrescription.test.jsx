import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// F4: "Write prescription" on a consultation opens /prescription?visit=<id>
// with that visit and its patient already chosen, even when neither is on the
// first page of the dropdown lists.
vi.mock("../services/api.js", () => ({
  default: {
    patients: { list: vi.fn() },
    doctors: { list: vi.fn() },
    visits: { list: vi.fn(), get: vi.fn() },
    prescriptions: { safetyCheck: vi.fn() },
  },
}))
// Context values are stable objects, as the real providers' are: the page's
// effects depend on them.
vi.mock("../assets/context/PatientContext.jsx", () => {
  const value = { selectedHospital: { id: 4, name: "Synthetic" } }
  return { usePatient: () => value }
})
vi.mock("../assets/context/RoleContext.jsx", () => {
  const value = { canAdd: () => true }
  return { useRole: () => value }
})
vi.mock("../assets/context/PrescriptionContext.jsx", () => {
  const value = {
    prescriptions: [], getHospitalPrescriptions: () => [], loadPrescriptions: () => Promise.resolve([]),
    createPrescription: () => Promise.resolve({}), deletePrescription: () => Promise.resolve(true),
    loading: false, error: null, usingFallback: false,
  }
  return { usePrescription: () => value }
})

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import Prescription from "../pages/Prescription.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
let host
let root

async function render(path) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(
    <LanguageProvider><MemoryRouter initialEntries={[path]}><Prescription /></MemoryRouter></LanguageProvider>,
  ))
  await flush()
  await flush()
}

const selectNear = (label) => {
  const field = [...host.querySelectorAll("label")].find((el) => el.textContent.trim().startsWith(label))
  return host.querySelector(`#${CSS.escape(field.htmlFor)}`)
}

describe("Prescription opened from a consultation", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.patients.list.mockResolvedValue({ results: [{ id: 1, name: "Someone Else" }] })
    api.doctors.list.mockResolvedValue({ results: [] })
    api.visits.list.mockResolvedValue({ results: [] })
    api.visits.get.mockResolvedValue({ id: 3, hospital: 4, patient: 6, patient_name: "Synthetic Consult" })
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("fills in the visit and its patient and offers the way back", async () => {
    await render("/prescription?visit=3")
    expect(api.visits.get).toHaveBeenCalledWith("3")
    expect(selectNear("Visit").value).toBe("3")
    expect(selectNear("Patient").value).toBe("6")
    expect(host.textContent).toContain("Synthetic Consult")
    expect(host.querySelector('a[href="/consultation?visit=3"]')).not.toBeNull()
  })

  it("ignores a visit of another hospital", async () => {
    api.visits.get.mockResolvedValue({ id: 3, hospital: 99, patient: 6, patient_name: "Elsewhere" })
    await render("/prescription?visit=3")
    expect(selectNear("Visit").value).toBe("")
    expect(host.querySelector('a[href="/consultation?visit=3"]')).toBeNull()
  })

  it("starts empty without a visit", async () => {
    await render("/prescription")
    expect(api.visits.get).not.toHaveBeenCalled()
    expect(selectNear("Patient").value).toBe("")
  })
})
