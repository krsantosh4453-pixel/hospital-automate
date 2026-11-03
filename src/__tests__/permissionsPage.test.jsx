import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { MemoryRouter } from "react-router-dom"
import { afterEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import { RoleProvider } from "../assets/context/RoleProvider.jsx"
import Permissions from "../pages/admin/Permissions.jsx"

vi.mock("../assets/context/AuthContext.jsx", () => ({
  useAuth: () => ({ isStaff: true, isPatient: false, user: { roles: ["Admin"] } }),
}))

// vi.mock is hoisted above the imports, so RoleProvider sees this useAuth.
globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe("Permissions page (F-3)", () => {
  let root
  let host

  const render = () => {
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    act(() =>
      root.render(
        <MemoryRouter>
          <LanguageProvider>
            <RoleProvider>
              <Permissions />
            </RoleProvider>
          </LanguageProvider>
        </MemoryRouter>,
      ),
    )
  }

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("is a read-only view of the built-in roles", () => {
    render()

    expect(host.querySelectorAll("input[type=checkbox]")).toHaveLength(0)
    expect(host.textContent).toContain("Roles are built in")
  })

  it("shows what the chosen role can do", () => {
    render()

    const pharmacist = [...host.querySelectorAll("[role=tab]")].find((b) => b.textContent === "Pharmacist")
    act(() => pharmacist.click())

    const rows = [...host.querySelectorAll("tbody tr")].map((tr) => tr.querySelector("td").textContent)
    expect(rows).toContain("Pharmacy")
    expect(rows).not.toContain("Users")
  })

  it("removes permission edits an older version saved in this browser", () => {
    localStorage.setItem("hms_role_permissions", "[]")

    render()

    expect(localStorage.getItem("hms_role_permissions")).toBeNull()
  })
})
