import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// G-8: the break-glass screen offers each role only its own actions.
let role = "Doctor"
vi.mock("../assets/context/RoleContext.jsx", () => ({ useRole: () => ({ activeRoleName: role }) }))
vi.mock("../assets/context/PatientContext.jsx", () => ({
  usePatient: () => ({ selectedHospital: { id: 4, name: "Synthetic Hospital" } }),
}))
vi.mock("../services/api.js", () => ({
  default: {
    breakGlass: {
      list: vi.fn(),
      open: vi.fn(),
      end: vi.fn(),
      review: vi.fn(),
    },
  },
}))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import EmergencyAccess from "../pages/EmergencyAccess.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const GRANT = {
  id: 9, username: "dr_synthetic", patient: 12, patient_name: "Synthetic Patient",
  reason: "Unconscious on arrival, treating doctor unavailable",
  created_at: "2026-11-03T10:00:00Z", expires_at: "2026-11-03T11:00:00Z", ended_at: null,
  is_active: true, reviewed_at: null, reviewed_by_username: "", review_note: "",
}

let host
let root

const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))

async function renderPage() {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(
    <LanguageProvider><MemoryRouter><EmergencyAccess /></MemoryRouter></LanguageProvider>,
  ))
  await flush()
}

const button = (label) => [...host.querySelectorAll("button")].find((b) => b.textContent.trim() === label)

function type(element, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event("input", { bubbles: true }))
  })
}

describe("Emergency access page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.breakGlass.list.mockResolvedValue({ results: [GRANT] })
    api.breakGlass.open.mockResolvedValue({ id: 10 })
    api.breakGlass.end.mockResolvedValue({})
    api.breakGlass.review.mockResolvedValue({})
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("lets a doctor open access with a patient number and a reason, and end it", async () => {
    role = "Doctor"
    await renderPage()
    expect(api.breakGlass.list).toHaveBeenCalledWith(4, { pendingReview: false })
    expect(button("Review")).toBeUndefined()

    type(host.querySelector('input[placeholder="P012"]'), "P012")
    type(host.querySelector("textarea"), "Unconscious on arrival, treating doctor unavailable")
    await act(async () => button("Open access").click())
    expect(api.breakGlass.open).toHaveBeenCalledWith(4, 12, "Unconscious on arrival, treating doctor unavailable")

    await act(async () => button("End now").click())
    expect(api.breakGlass.end).toHaveBeenCalledWith(9)
  })

  it("refuses a short reason before calling the server", async () => {
    role = "Nurse"
    await renderPage()
    type(host.querySelector('input[placeholder="P012"]'), "12")
    type(host.querySelector("textarea"), "urgent")
    await act(async () => button("Open access").click())
    expect(api.breakGlass.open).not.toHaveBeenCalled()
    expect(host.textContent).toContain("at least 20 characters")
  })

  it("shows the review queue to an administrator, without the open form", async () => {
    role = "Hospital Manager"
    await renderPage()
    expect(api.breakGlass.list).toHaveBeenCalledWith(4, { pendingReview: true })
    expect(host.querySelector("textarea")).toBeNull()
    expect(host.textContent).toContain("dr_synthetic")
    expect(button("Review")).toBeDefined()
    expect(button("End now")).toBeUndefined()
  })

  it("tells other roles the page is not for them and loads nothing", async () => {
    role = "Pharmacist"
    await renderPage()
    expect(api.breakGlass.list).not.toHaveBeenCalled()
    expect(host.textContent).toContain("Not available for your role")
  })
})
