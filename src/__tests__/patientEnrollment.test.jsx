import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Prompt 3 (E2E audit 2026-11-24): a self-registered patient had no hospital,
// so no UHID and no booking; the desk had no screen to enrol an existing patient.
vi.mock("../services/api.js", () => ({
  default: {
    auth: {
      register: vi.fn(), verifyEmailOtp: vi.fn(), requestEmailOtp: vi.fn(),
      selfRegistrationHospitals: vi.fn(), joinHospital: vi.fn(), patientMe: vi.fn(),
    },
    patients: { link: vi.fn() },
  },
}))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import Register from "../pages/Register.jsx"
import EnrolExistingPatientDialog from "../components/patients/EnrolExistingPatientDialog.jsx"
import { JoinHospitalForm, MyHospitalsCard } from "../components/patient/HospitalMembership.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const HOSPITALS = [{ id: 4, name: "Synthetic General", city: "Pune" }, { id: 9, name: "Synthetic Care", city: "" }]
let host
let root
const flush = (ms = 0) => act(() => new Promise((resolve) => setTimeout(resolve, ms)))
const $ = (selector) => document.body.querySelector(selector)
const button = (label) => [...document.body.querySelectorAll("button")].find((b) => b.textContent.trim() === label)
const text = () => document.body.textContent

function type(element, value) {
  const proto = element.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype
  act(() => {
    Object.getOwnPropertyDescriptor(proto, "value").set.call(element, value)
    element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  })
}

async function render(node) {
  await act(async () => {
    root.render(
      <LanguageProvider>
        <MemoryRouter>{node}</MemoryRouter>
      </LanguageProvider>,
    )
  })
  await flush()
}

function fillPatient() {
  type($("#reg-field-1"), "Synthetic Signup")
  type($("#reg-field-phone"), "9000044401")
  type($("#reg-field-2"), "signup@example.test")
  type($("#reg-field-3"), "1990-01-01")
  type($("#reg-field-14"), "Synth-Pass-4401")
  type($("#reg-field-15"), "Synth-Pass-4401")
}

const submit = () => act(async () => $("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })))

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
})

afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

describe("Create account: hospital choice", () => {
  it("lists the hospitals from the API and requires a choice (TEST 1, 2)", async () => {
    api.auth.selfRegistrationHospitals.mockResolvedValue(HOSPITALS)
    api.auth.register.mockResolvedValue({
      message: "Patient account created.",
      user: { email: "signup@example.test" },
      patient: { id: 21, hospitals: [{ id: 4, name: "Synthetic General", uhid: "SG-2026-000001" }] },
      verification: { message: "Code sent." },
    })
    await render(<Register />)

    const select = $("#reg-field-hospital")
    expect([...select.options].map((o) => o.textContent)).toEqual(["Select hospital", "Synthetic General (Pune)", "Synthetic Care"])

    fillPatient()
    await submit()
    expect(api.auth.register).not.toHaveBeenCalled()
    expect(text()).toContain("Choose the hospital where you want to be registered.")

    type(select, "4")
    await submit()
    await flush()
    expect(api.auth.register).toHaveBeenCalledWith(expect.objectContaining({ role: "Patient", hospital: "4" }))
    expect(text()).toContain("Synthetic General")
    expect(text()).toContain("SG-2026-000001")
  })

  it("offers a retry when the hospital list does not load, and does not submit meanwhile", async () => {
    api.auth.selfRegistrationHospitals.mockRejectedValueOnce(new Error("offline")).mockResolvedValue(HOSPITALS)
    await render(<Register />)
    expect(text()).toContain("Hospitals could not be loaded")

    fillPatient()
    await submit()
    expect(api.auth.register).not.toHaveBeenCalled()

    await act(async () => button("Try again").click())
    await flush()
    expect($("#reg-field-hospital").options.length).toBe(3)
  })

  it("still creates the account when no hospital accepts online registration", async () => {
    api.auth.selfRegistrationHospitals.mockResolvedValue([])
    api.auth.register.mockResolvedValue({ message: "Created", user: { email: "signup@example.test" }, patient: { id: 22, hospitals: [] } })
    await render(<Register />)
    expect(text()).toContain("No hospital accepts online registration")

    fillPatient()
    await submit()
    await flush()
    expect(api.auth.register).toHaveBeenCalledTimes(1)
    expect(api.auth.register.mock.calls[0][0]).not.toHaveProperty("hospital")
  })

  it("asks no hospital of an Admin sign-up", async () => {
    api.auth.selfRegistrationHospitals.mockResolvedValue(HOSPITALS)
    await render(<Register />)
    await act(async () => [...document.body.querySelectorAll("[role=radio]")].find((b) => b.textContent === "Admin").click())
    expect($("#reg-field-hospital")).toBeNull()
  })
})

describe("Enrol existing patient (reception)", () => {
  const HOSPITAL = { id: 5, name: "Synthetic Desk Hospital" }

  async function open(onEnrolled = vi.fn()) {
    await render(<EnrolExistingPatientDialog open hospital={HOSPITAL} onClose={vi.fn()} onEnrolled={onEnrolled} />)
    return onEnrolled
  }

  it("needs a 10-digit mobile number and a date of birth before asking the server", async () => {
    await open()
    type($("#enrol-phone"), "90000")
    await act(async () => button("Find and enrol").click())
    expect(api.patients.link).not.toHaveBeenCalled()
    expect(text()).toContain("10-digit mobile number")
  })

  it("enrols the patient and shows the new UHID (TEST 5)", async () => {
    api.patients.link.mockResolvedValue({ id: 31, name: "Synthetic Existing", uhid: "SDH-2026-000004", created: true })
    const onEnrolled = await open()
    type($("#enrol-phone"), "9000012345")
    type($("#enrol-dob"), "1990-01-01")
    await act(async () => button("Find and enrol").click())
    await flush()

    expect(api.patients.link).toHaveBeenCalledWith(5, { phone: "9000012345", date_of_birth: "1990-01-01" })
    expect(text()).toContain("Synthetic Existing is now registered at Synthetic Desk Hospital")
    expect(text()).toContain("SDH-2026-000004")
    expect(onEnrolled).toHaveBeenCalledWith(expect.objectContaining({ id: 31 }))
  })

  it("says so when the patient is already registered here (TEST 6)", async () => {
    api.patients.link.mockResolvedValue({ id: 31, name: "Synthetic Existing", uhid: "SDH-2026-000004", created: false })
    await open()
    type($("#enrol-phone"), "9000012345")
    type($("#enrol-dob"), "1990-01-01")
    await act(async () => button("Find and enrol").click())
    await flush()
    expect(text()).toContain("already registered at Synthetic Desk Hospital")
  })

  it("shows the server's reason when nobody matches", async () => {
    api.patients.link.mockRejectedValue(Object.assign(new Error("No patient has this mobile number and date of birth. Register them as new."), { status: 404 }))
    await open()
    type($("#enrol-phone"), "9000012345")
    type($("#enrol-dob"), "1990-01-01")
    await act(async () => button("Find and enrol").click())
    await flush()
    expect(text()).toContain("No patient has this mobile number and date of birth")
  })
})

describe("Patient portal: hospitals and UHID", () => {
  it("shows each hospital the patient is registered at, with its UHID (TEST 10)", async () => {
    api.auth.patientMe.mockResolvedValue({ hospitals: [{ id: 4, name: "Synthetic General", uhid: "SG-2026-000001" }] })
    await render(<MyHospitalsCard />)
    expect(text()).toContain("Synthetic General")
    expect(text()).toContain("SG-2026-000001")
  })

  it("lets a patient with no hospital join an open one", async () => {
    api.auth.selfRegistrationHospitals.mockResolvedValue(HOSPITALS)
    api.auth.joinHospital.mockResolvedValue({ hospital: 9, uhid: "SC-2026-000001", created: true, hospitals: [] })
    const onJoined = vi.fn()
    await render(<JoinHospitalForm onJoined={onJoined} />)

    type($("#join-hospital"), "9")
    await act(async () => button("Register at this hospital").click())
    await flush()

    expect(api.auth.joinHospital).toHaveBeenCalledWith("9")
    expect(onJoined).toHaveBeenCalledWith(expect.objectContaining({ uhid: "SC-2026-000001" }))
  })
})
