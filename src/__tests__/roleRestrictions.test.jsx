import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Admins narrow a built-in role per module at their hospital; the screens follow.
vi.mock("../assets/context/AuthContext.jsx", () => ({
  useAuth: () => ({ isStaff: true, isPatient: false, user: { roles: ["Admin"] } }),
}))
vi.mock("../services/api.js", () => ({
  default: { roleRestrictions: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() } },
}))
vi.mock("../components/Toast.jsx", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn() }) }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import { PatientContext } from "../assets/context/PatientContext.jsx"
import { RoleProvider } from "../assets/context/RoleProvider.jsx"
import Permissions from "../pages/admin/Permissions.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))

async function render() {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(
    <MemoryRouter><LanguageProvider>
      <PatientContext.Provider value={{ selectedHospital: { id: 4, name: "Synthetic" } }}>
        <RoleProvider><Permissions /></RoleProvider>
      </PatientContext.Provider>
    </LanguageProvider></MemoryRouter>,
  ))
  await flush()
  const pharmacist = [...host.querySelectorAll("[role=tab]")].find((b) => b.textContent === "Pharmacist")
  act(() => pharmacist.click())
}

const row = (module) => [...host.querySelectorAll("tbody tr")].find((tr) => tr.querySelector("td").textContent === module)

describe("Role restrictions on the Permissions page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.roleRestrictions.create.mockResolvedValue({})
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("shows a view-only rule and lets the admin narrow another module", async () => {
    api.roleRestrictions.list.mockResolvedValue([{ id: 3, role: "Pharmacist", module: "Pharmacy", access: "view" }])
    await render()
    const pharmacy = row("Pharmacy")
    expect(pharmacy.querySelector("select").value).toBe("view")
    // View stays allowed; adding is now refused.
    const cells = [...pharmacy.querySelectorAll("td")].map((td) => td.querySelector("svg")?.getAttribute("aria-label"))
    expect(cells.slice(1, 3)).toEqual(["Allowed", "Not allowed"])

    const select = row("Inventory").querySelector("select")
    const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(select), "value").set
    await act(async () => {
      setter.call(select, "none")
      select.dispatchEvent(new Event("change", { bubbles: true }))
    })
    expect(api.roleRestrictions.create).toHaveBeenCalledWith({ role: "Pharmacist", module: "Inventory", access: "none" }, 4)
  })
})
