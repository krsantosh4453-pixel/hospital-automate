import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it } from "vitest"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { PatientProvider } from "../assets/context/PatientProvider.jsx"
import { CACHED_PATIENT_DATA_KEYS } from "../services/api.js"

// R-13: hospital PCs are shared, so patient rows live in memory only.
const PATIENT_KEYS = [...CACHED_PATIENT_DATA_KEYS, "patientToken", "patient"]

let container
let root

const mount = () => {
  let context
  const Probe = () => {
    context = usePatient()
    return null
  }
  act(() => {
    root.render(<PatientProvider><Probe /></PatientProvider>)
  })
  return () => context
}

describe("PatientContext storage", () => {
  beforeEach(() => {
    localStorage.clear()
    container = document.createElement("div")
    root = createRoot(container)
  })

  afterEach(() => {
    act(() => root.unmount())
  })

  it("keeps patients, appointments and tokens out of localStorage", () => {
    const context = mount()
    act(() => {
      context().savePatient({ id: 1, name: "Synthetic Patient" })
      context().addPatient({ name: "Synthetic Walk-in" })
      context().saveAppointment({ id: 7, patient: "Synthetic Patient" })
      context().saveToken("T-12")
    })
    expect(context().patient.name).toBe("Synthetic Patient")
    expect(context().patients).toHaveLength(1)
    expect(context().token).toBe("T-12")
    for (const key of PATIENT_KEYS) expect(localStorage.getItem(key)).toBeNull()
  })

  it("clears patient rows an older version left in localStorage", () => {
    for (const key of PATIENT_KEYS) localStorage.setItem(key, '[{"name":"Synthetic Old"}]')
    const context = mount()
    expect(context().patient).toBeNull()
    expect(context().patients).toEqual([])
    for (const key of PATIENT_KEYS) expect(localStorage.getItem(key)).toBeNull()
  })

  it("still remembers the selected hospital, which holds no patient data", () => {
    const context = mount()
    act(() => context().selectHospital({ id: 3, name: "Synthetic Hospital" }))
    expect(JSON.parse(localStorage.getItem("selectedHospital")).id).toBe(3)
  })
})
