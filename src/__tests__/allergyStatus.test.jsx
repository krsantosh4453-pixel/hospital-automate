import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// BUG-001: the consultation strip said "No known allergies" for a patient
// nobody had asked. Only an explicit "No known allergies" may say so.
vi.mock("../services/api.js", () => ({
  default: {
    patients: { get: vi.fn(), setAllergyStatus: vi.fn() },
    ipd: { admissions: { currentForPatient: vi.fn() } },
    clinical: { allergies: { list: vi.fn(), create: vi.fn() } },
  },
}))
vi.mock("../assets/context/RoleContext.jsx", () => ({ useRole: () => ({ activeRoleName: "Doctor" }) }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import { allergySummary } from "../components/clinical/allergyStatus.js"
import PatientContextStrip from "../components/clinical/PatientContextStrip.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const PENICILLIN = { id: 7, name: "Penicillin", severity: "Severe" }
const loaded = (allergy_status) => ({ state: "loaded", data: { id: 1, allergy_status } })

describe("allergySummary", () => {
  it("never reads an empty allergy list as no known allergies (TEST 1)", () => {
    expect(allergySummary({ patient: loaded("Unknown"), allergies: { state: "loaded", data: [] } }).kind).toBe("unknown")
  })

  it("shows no known allergies only when it was recorded (TEST 2)", () => {
    expect(allergySummary({ patient: loaded("No known allergies"), allergies: { state: "loaded", data: [] } }).kind).toBe("nka")
  })

  it("lists recorded allergies (TEST 3)", () => {
    const summary = allergySummary({ patient: loaded("Has allergies"), allergies: { state: "loaded", data: [PENICILLIN] } })
    expect(summary).toEqual({ kind: "known", allergies: [PENICILLIN] })
  })

  it("asks for a review when allergies are on record but none can be shown here (TEST 4)", () => {
    // The list is scoped to this hospital; the status counts every hospital.
    expect(allergySummary({ patient: loaded("Has allergies"), allergies: { state: "loaded", data: [] } }).kind).toBe("review")
  })

  it.each([
    ["a null status", loaded(null)],
    ["a missing status", { state: "loaded", data: { id: 1 } }],
    ["an unexpected status", loaded("Maybe")],
    ["no patient record", { state: "loaded", data: null }],
  ])("treats %s as unknown, never as no known allergies (TEST 6)", (_label, patient) => {
    expect(allergySummary({ patient, allergies: { state: "loaded", data: [] } }).kind).toBe("unknown")
  })

  it("cannot confirm anything while either request failed or is loading (TEST 6)", () => {
    const none = { state: "loaded", data: [] }
    expect(allergySummary({ patient: { state: "failed" }, allergies: none }).kind).toBe("failed")
    expect(allergySummary({ patient: loaded("No known allergies"), allergies: { state: "failed" } }).kind).toBe("failed")
    expect(allergySummary({ patient: { state: "loading" }, allergies: none }).kind).toBe("loading")
  })

  it("still shows recorded allergies when the patient record did not load", () => {
    expect(allergySummary({ patient: { state: "failed" }, allergies: { state: "loaded", data: [PENICILLIN] } }).kind).toBe("known")
  })
})

let host
let root
const flush = (ms = 0) => act(() => new Promise((resolve) => setTimeout(resolve, ms)))
const text = () => host.textContent

async function render(patientId) {
  await act(async () => {
    root.render(
      <LanguageProvider>
        <PatientContextStrip patientId={patientId} />
      </LanguageProvider>,
    )
  })
  await flush()
}

function serve(records) {
  api.patients.get.mockImplementation(async (id) => records[id].patient)
  api.clinical.allergies.list.mockImplementation(async ({ patientId }) => records[patientId].allergies)
  api.ipd.admissions.currentForPatient.mockResolvedValue([])
}

describe("PatientContextStrip", () => {
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

  it("says allergy status unknown for a patient nobody has asked (original BUG-001)", async () => {
    serve({ 1: { patient: { id: 1, allergy_status: "Unknown" }, allergies: [] } })
    await render(1)
    expect(text()).toContain("Allergy status unknown")
    expect(text()).not.toContain("No known allergies")
  })

  it("says no known allergies when it was recorded", async () => {
    serve({ 1: { patient: { id: 1, allergy_status: "No known allergies" }, allergies: [] } })
    await render(1)
    expect(text()).toContain("No known allergies")
  })

  it("shows recorded allergies by name and severity", async () => {
    serve({ 1: { patient: { id: 1, allergy_status: "Has allergies" }, allergies: [PENICILLIN] } })
    await render(1)
    expect(text()).toContain("Penicillin (Severe)")
  })

  it("asks for a review when allergies are on record elsewhere", async () => {
    serve({ 1: { patient: { id: 1, allergy_status: "Has allergies" }, allergies: [] } })
    await render(1)
    expect(text()).toContain("review")
    expect(text()).not.toContain("No known allergies")
  })

  it("does not claim no known allergies when the patient record fails to load", async () => {
    serve({ 1: { patient: null, allergies: [] } })
    api.patients.get.mockRejectedValue(new Error("offline"))
    await render(1)
    expect(text()).toContain("could not be checked")
    expect(text()).not.toContain("No known allergies")
  })

  it("never shows the previous patient's allergies after switching (TEST 5)", async () => {
    let releaseSecond
    serve({
      1: { patient: { id: 1, allergy_status: "Has allergies" }, allergies: [PENICILLIN] },
      2: { patient: { id: 2, allergy_status: "Unknown" }, allergies: [] },
    })
    await render(1)
    expect(text()).toContain("Penicillin")

    // The second patient's answers arrive late: nothing of patient 1 may show meanwhile.
    api.clinical.allergies.list.mockImplementation(() => new Promise((resolve) => { releaseSecond = () => resolve([]) }))
    await render(2)
    expect(text()).not.toContain("Penicillin")
    expect(text()).toContain("Checking allergies")

    await act(async () => releaseSecond())
    await flush()
    expect(text()).toContain("Allergy status unknown")
  })

  it("records no known allergies through the audited endpoint after confirmation", async () => {
    const records = { 1: { patient: { id: 1, allergy_status: "Unknown" }, allergies: [] } }
    serve(records)
    // Like the server: the strip shows what it reads back, not what it sent.
    api.patients.setAllergyStatus.mockImplementation(async (_id, status) => {
      records[1].patient = { ...records[1].patient, allergy_status: status }
      return { allergy_status: status }
    })
    await render(1)

    const button = (label) => [...document.body.querySelectorAll("button")].find((b) => b.textContent.trim() === label)
    await act(async () => button("Record no known allergies").click())
    await flush()
    expect(api.patients.setAllergyStatus).not.toHaveBeenCalled() // asks first
    await act(async () => button("Patient has no known allergies").click())
    await flush()

    expect(api.patients.setAllergyStatus).toHaveBeenCalledWith(1, "No known allergies")
    expect(text()).toContain("No known allergies")
  })
})
