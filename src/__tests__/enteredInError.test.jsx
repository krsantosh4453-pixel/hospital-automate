import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// R-03 and the doctor's-order rule (2026-11-05): removals need a reason, and
// only a doctor orders medicine.
vi.mock("../services/api.js", () => ({
  default: {
    nurses: { mar: { list: vi.fn(), create: vi.fn(), generateSchedule: vi.fn(), stop: vi.fn() } },
    prescriptions: { list: vi.fn() },
  },
}))
vi.mock("../components/Toast.jsx", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }) }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import { RemoveRecordDialog } from "../components/ui"
import MedicationOrders from "../components/ipd/MedicationOrders.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))

function render(element) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<LanguageProvider>{element}</LanguageProvider>))
}

const button = (label) => [...document.body.querySelectorAll("button")].find((b) => b.textContent.trim() === label)

function type(element, value) {
  const proto = Object.getPrototypeOf(element)
  const setter = Object.getOwnPropertyDescriptor(proto, "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  })
}

afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

describe("Remove record dialog", () => {
  it("asks for a reason and passes it on", async () => {
    const onConfirm = vi.fn()
    render(<RemoveRecordDialog open title="Remove this diagnosis?" onCancel={() => {}} onConfirm={onConfirm} />)
    expect(button("Remove").disabled).toBe(true)
    type(document.body.querySelector("textarea"), "Wrong patient")
    expect(button("Remove").disabled).toBe(false)
    await act(async () => button("Remove").click())
    expect(onConfirm).toHaveBeenCalledWith("Wrong patient")
  })
})

describe("Medicine orders", () => {
  const admission = { id: 5, patient: 12, patient_name: "Synthetic Patient" }
  const ORDER = { id: 3, medicine_name: "Synthetic Paracetamol", dose: "500 mg", route: "Oral", frequency: "TID",
    start_date: "2026-11-05", end_date: null, is_active: true, ordered_by_name: "Dr Synthetic" }

  beforeEach(() => {
    vi.clearAllMocks()
    api.nurses.mar.list.mockResolvedValue([ORDER])
    api.prescriptions.list.mockResolvedValue([{ id: 40, items: [{ id: 41, name: "Synthetic Amoxicillin", dosage: "250 mg", frequency: "BID" }] }])
    api.nurses.mar.create.mockResolvedValue({ id: 9 })
    api.nurses.mar.generateSchedule.mockResolvedValue([])
  })

  it("lets a nurse read orders but not write or stop them", async () => {
    render(<MedicationOrders open admission={admission} hospitalId={4} canOrder={false} onClose={() => {}} />)
    await flush()
    expect(document.body.textContent).toContain("Synthetic Paracetamol")
    expect(document.body.textContent).toContain("Dr Synthetic")
    expect(document.body.textContent).toContain("Only a doctor can order or stop a medicine")
    expect(button("Order medicine")).toBeUndefined()
    expect(button("Stop")).toBeUndefined()
  })

  it("lets a doctor order a medicine from the patient's prescription and schedules it", async () => {
    render(<MedicationOrders open admission={admission} hospitalId={4} canOrder onClose={() => {}} />)
    await flush()
    type(document.body.querySelector("select"), "41")
    await act(async () => button("Order medicine").click())
    await flush()
    expect(api.nurses.mar.create).toHaveBeenCalledWith(expect.objectContaining({
      patient: 12, admission: 5, hospital: 4, prescription: 40, prescription_item: 41,
      medicine_name: "Synthetic Amoxicillin", dose: "250 mg", frequency: "BID", route: "Oral",
    }))
    expect(api.nurses.mar.generateSchedule).toHaveBeenCalledWith(9)
  })
})
