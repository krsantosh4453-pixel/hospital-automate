import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Prompt 5 (MF-003): a patient cancels or moves their own booking.
vi.mock("../services/api.js", () => ({
  default: { appointments: { selfCancel: vi.fn(), selfReschedule: vi.fn(), bookingOptions: vi.fn() } },
}))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import ManageAppointmentDialog, { canManageOnline } from "../components/patient/ManageAppointmentDialog.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const BOOKING = { id: 7, hospital: 1, doctor: 3, doctor_name: "Dr Synthetic", status: "Scheduled",
  appointment_date: "2030-01-07", appointment_time: "10:00:00" }
let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const button = (label) => [...document.body.querySelectorAll("button")].find((b) => b.textContent.trim() === label)
const text = () => document.body.textContent

function type(element, value) {
  const proto = element.tagName === "SELECT" ? HTMLSelectElement.prototype
    : element.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
  act(() => {
    Object.getOwnPropertyDescriptor(proto, "value").set.call(element, value)
    element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  })
}

async function render(mode, onChanged = vi.fn(), onClose = vi.fn()) {
  await act(async () => {
    root.render(<LanguageProvider><ManageAppointmentDialog appointment={BOOKING} mode={mode} onChanged={onChanged} onClose={onClose} /></LanguageProvider>)
  })
  await flush()
  return { onChanged, onClose }
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

describe("canManageOnline", () => {
  const now = new Date("2030-01-06T12:00:00")
  it("allows only a Scheduled booking that has not started", () => {
    expect(canManageOnline(BOOKING, now)).toBe(true)
    for (const status of ["Checked In", "In Consultation", "Completed", "Cancelled", "No Show"]) {
      expect(canManageOnline({ ...BOOKING, status }, now)).toBe(false)
    }
    expect(canManageOnline({ ...BOOKING, appointment_date: "2030-01-05" }, now)).toBe(false)
  })
})

describe("Cancel", () => {
  it("sends the reason and reports the cancelled booking (TEST 14)", async () => {
    api.appointments.selfCancel.mockResolvedValue({ ...BOOKING, status: "Cancelled" })
    const { onChanged, onClose } = await render("cancel")

    type(document.body.querySelector("#cancel-reason"), "Feeling better")
    await act(async () => button("Cancel appointment").click())
    await flush()

    expect(api.appointments.selfCancel).toHaveBeenCalledWith(7, "Feeling better")
    expect(onChanged).toHaveBeenCalledWith(expect.objectContaining({ status: "Cancelled" }), "cancelled")
    expect(onClose).toHaveBeenCalled()
  })

  it("shows the server's refusal and keeps the dialog open", async () => {
    api.appointments.selfCancel.mockRejectedValue(new Error("A checked in appointment cannot be changed online."))
    const { onChanged } = await render("cancel")
    await act(async () => button("Cancel appointment").click())
    await flush()
    expect(text()).toContain("cannot be changed online")
    expect(onChanged).not.toHaveBeenCalled()
  })
})

describe("Reschedule", () => {
  it("offers only free slots from the server and moves the booking (TEST 15)", async () => {
    api.appointments.bookingOptions.mockResolvedValue({ slots: [
      { time: "10:00", available: false }, { time: "11:30", available: true }] })
    api.appointments.selfReschedule.mockResolvedValue({ ...BOOKING, appointment_time: "11:30:00" })
    const { onChanged } = await render("reschedule")

    expect(api.appointments.bookingOptions).toHaveBeenCalledWith({ hospital: 1, doctor: 3, date: "2030-01-07" })
    const options = [...document.body.querySelectorAll("#move-time option")].map((o) => o.value)
    expect(options).toEqual(["", "11:30"])
    type(document.body.querySelector("#move-time"), "11:30")
    await act(async () => button("Move appointment").click())
    await flush()

    expect(api.appointments.selfReschedule).toHaveBeenCalledWith(7, { appointment_date: "2030-01-07", appointment_time: "11:30" })
    expect(onChanged).toHaveBeenCalledWith(expect.objectContaining({ appointment_time: "11:30:00" }), "moved")
  })

  it("explains a day off and offers no time", async () => {
    api.appointments.bookingOptions.mockResolvedValue({ slots: [], unavailable_reason: "Dr Synthetic does not see patients on Sundays." })
    await render("reschedule")
    expect(text()).toContain("does not see patients on Sundays")
    expect(document.body.querySelector("#move-time").disabled).toBe(true)
  })

  it("keeps the booking when the server refuses the move", async () => {
    api.appointments.bookingOptions.mockResolvedValue({ slots: [{ time: "11:30", available: true }] })
    api.appointments.selfReschedule.mockRejectedValue(new Error("This slot was just booked. Please choose another time."))
    const { onChanged } = await render("reschedule")
    type(document.body.querySelector("#move-time"), "11:30")
    await act(async () => button("Move appointment").click())
    await flush()
    expect(text()).toContain("This slot was just booked")
    expect(onChanged).not.toHaveBeenCalled()
  })
})
