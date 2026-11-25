import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Found by the fresh-hospital journey (2026-11-25): when the date changes
// while the previous day's free times are still loading, the slower answer
// could overwrite the newer one, showing another day's times.
vi.mock("../services/api.js", () => ({ default: { appointments: { bookingOptions: vi.fn(), book: vi.fn() } } }))
vi.mock("../components/patient/HospitalMembership.jsx", () => ({ JoinHospitalForm: () => null }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import BookAppointmentModal from "../pages/patient/BookAppointmentModal.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const select = (label) => [...document.body.querySelectorAll("select")].find((s) => s.closest("div")?.parentElement?.textContent.includes(label))

function change(element, value) {
  const proto = element.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype
  act(() => {
    Object.getOwnPropertyDescriptor(proto, "value").set.call(element, value)
    element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
})
afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

describe("free times", () => {
  it("show the chosen day's times even when an older request answers last", async () => {
    let releaseOld
    api.appointments.bookingOptions.mockImplementation(({ doctor, date } = {}) => {
      if (!doctor) return Promise.resolve({ hospitals: [{ id: 1, name: "Synthetic" }], doctors: [{ id: 3, name: "Dr Synthetic", working_days: null }] })
      if (date === "2030-01-07") return new Promise((resolve) => { releaseOld = () => resolve({ slots: [{ time: "09:00", available: true }] }) })
      return Promise.resolve({ slots: [{ time: "15:30", available: true }] })
    })
    await act(async () => root.render(<LanguageProvider><BookAppointmentModal open onClose={vi.fn()} onBooked={vi.fn()} /></LanguageProvider>))
    await flush()

    const dateInput = document.body.querySelector("input[type=date]")
    change(dateInput, "2030-01-07")
    change(document.body.querySelectorAll("select")[1], "3")
    await flush()
    change(dateInput, "2030-01-08")
    await flush()
    await act(async () => releaseOld())
    await flush()

    const times = [...document.body.querySelectorAll("select")[2].options].map((o) => o.value).filter(Boolean)
    expect(times).toEqual(["15:30"])
    expect(document.body.querySelectorAll("select")[2].disabled).toBe(false)
  })
})
