import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { MemoryRouter } from "react-router-dom"
import { afterEach, describe, expect, it } from "vitest"
import GuestHome from "../pages/GuestHome.jsx"
import { eligibleRolesFor } from "../assets/context/RoleContext.jsx"
import { roleHomeFor, ROLE_HOMES } from "../config/roleHomes.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const ADD_ACTION = /register patient|new appointment|create invoice|add /i

describe("role homes", () => {
  it("Admin and Hospital Manager keep the full dashboard", () => {
    expect(roleHomeFor("Admin")).toBeNull()
    expect(roleHomeFor("Hospital Manager")).toBeNull()
  })

  it("clinical and department roles get no front-desk add actions", () => {
    for (const role of ["Doctor", "Nurse", "Compounder", "Pharmacist", "Lab Staff", "Blood Bank Staff", "Inventory Staff"]) {
      const labels = roleHomeFor(role).actions.map((a) => a.label)
      expect(labels.filter((label) => ADD_ACTION.test(label)), role).toEqual([])
    }
  })

  it("only the front desk and billing can start registrations, appointments or invoices", () => {
    const withAdd = Object.entries(ROLE_HOMES)
      .filter(([, home]) => home.actions.some((a) => ADD_ACTION.test(a.label)))
      .map(([role]) => role)
    expect(withAdd.sort()).toEqual(["Billing Staff", "Receptionist"])
  })

  it("names the roles that may work in a department", () => {
    expect(eligibleRolesFor("Billing")).toContain("Admin")
    expect(eligibleRolesFor("Billing")).not.toContain("Nurse")
  })
})

describe("guest home", () => {
  let root
  let host

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  const render = () => {
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    act(() =>
      root.render(
        <MemoryRouter>
          <GuestHome />
        </MemoryRouter>,
      ),
    )
  }

  it("offers booking and sign-in only, with no add or create actions and no figures", () => {
    render()
    const actions = [...host.querySelectorAll("a, button")].map((el) => el.textContent.trim())
    expect(actions.filter((text) => ADD_ACTION.test(text))).toEqual([])
    expect(actions).toContain("Book appointment")
    const glance = host.querySelector("section[aria-label='Today at a glance']")
    expect(glance.textContent).not.toMatch(/\d/)
  })

  it("explains who may work in a department instead of opening it", () => {
    render()
    const billing = [...host.querySelectorAll("button")].find((b) => b.textContent.includes("Billing"))
    act(() => billing.click())
    const dialog = document.querySelector("[role='dialog']")
    expect(dialog.textContent).toContain("You are not eligible for this work")
    expect(dialog.textContent).toContain("Billing Staff")
  })
})
