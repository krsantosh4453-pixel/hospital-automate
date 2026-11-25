import React, { act, createContext, useContext, useState } from "react"
import { createRoot } from "react-dom/client"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Final validation P3-1: after "Create hospital" the wizard sometimes stayed
// on step 1, because it only moved on once the user profile refresh succeeded.
const mocks = vi.hoisted(() => ({
  refreshUser: null,
  addHospital: null,
  SelectionContext: null,
}))

vi.mock("../assets/context/AuthContext.jsx", () => ({
  useAuth: () => ({ user: { roles: ["Admin"], hospitals: [] }, refreshUser: mocks.refreshUser }),
}))
vi.mock("../assets/context/HospitalsContext.jsx", () => ({
  useHospitals: () => ({ addHospital: mocks.addHospital }),
}))
vi.mock("../assets/context/PatientContext.jsx", () => ({
  usePatient: () => useContext(mocks.SelectionContext),
}))
vi.mock("../services/api.js", () => ({
  default: {
    departments: { list: vi.fn().mockResolvedValue([]), create: vi.fn() },
    wards: { list: vi.fn().mockResolvedValue([]) },
  },
}))

import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import HospitalSetup from "../pages/admin/HospitalSetup.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true
mocks.SelectionContext = createContext(null)

function Selection({ children }) {
  const [selectedHospital, selectHospital] = useState(null)
  return <mocks.SelectionContext.Provider value={{ selectedHospital, selectHospital }}>{children}</mocks.SelectionContext.Provider>
}

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const text = () => document.body.textContent

function type(element, value) {
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(element, value)
    element.dispatchEvent(new Event("input", { bubbles: true }))
  })
}

async function createHospital() {
  await act(async () => {
    root.render(<LanguageProvider><MemoryRouter><Selection><HospitalSetup /></Selection></MemoryRouter></LanguageProvider>)
  })
  await flush()
  type(document.body.querySelector("form input"), "Synthetic Setup Hospital")
  await act(async () => document.body.querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })))
  await flush()
}

beforeEach(() => {
  mocks.addHospital = vi.fn().mockResolvedValue({ id: 7, name: "Synthetic Setup Hospital" })
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
})
afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

describe("Hospital setup wizard", () => {
  it("moves on to Departments once the hospital is created", async () => {
    mocks.refreshUser = vi.fn().mockResolvedValue({})
    await createHospital()
    expect(mocks.addHospital).toHaveBeenCalled()
    expect(text()).toContain("Department name")
  })

  it("still moves on when refreshing the signed-in profile fails or is slow", async () => {
    mocks.refreshUser = vi.fn().mockRejectedValue(new Error("Forbidden"))
    await createHospital()
    expect(text()).toContain("Department name")
    expect(text()).not.toContain("The hospital was not created")
  })
})
