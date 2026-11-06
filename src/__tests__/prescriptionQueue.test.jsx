import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// F6/F8: the pharmacy queue lists prescriptions from the server with UHID,
// doctor, medicines and stock; each medicine shows its saved instructions.
vi.mock("../services/api.js", () => ({ default: { prescriptions: { list: vi.fn() } } }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import PrescriptionQueue from "../components/pharmacy/PrescriptionQueue.jsx"
import DispenseLine from "../components/pharmacy/DispenseLine.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
let host
let root

const ROW = {
  id: 7, hospital: 4, patient: 9, patient_name: "Synthetic Queue", patient_uhid: "DCH-2026-000007",
  doctor: 1, doctor_name: "Dr Synthetic", status: "Confirmed", created_at: "2026-11-05T09:30:00Z",
  source: "Electronic",
  items: [
    { id: 1, name: "Paracetamol", quantity: 10, dispensed_quantity: 0, instructions: "After food" },
    { id: 2, name: "Cetirizine", quantity: 5, dispensed_quantity: 0, instructions: "" },
  ],
}
const STOCK = [{ id: 11, name: "Paracetamol", stock: 50, expiry: "12/2099" }]

function render(element) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<LanguageProvider>{element}</LanguageProvider>))
}

describe("Pharmacy prescription queue", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.prescriptions.list.mockResolvedValue({ count: 1, results: [ROW] })
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("asks for what is still to dispense, oldest first, at this hospital", async () => {
    render(<PrescriptionQueue hospitalId={4} stock={STOCK} onOpen={() => {}} />)
    await flush()
    expect(api.prescriptions.list).toHaveBeenCalledWith(expect.objectContaining({
      hospitalId: 4, status: "Confirmed,Pending,Partially Dispensed", order: "oldest", page: 1,
    }))
  })

  it("shows number, patient UHID, doctor and stock for each medicine", async () => {
    render(<PrescriptionQueue hospitalId={4} stock={STOCK} onOpen={() => {}} />)
    await flush()
    const text = host.textContent
    expect(text).toContain("RX-0007")
    expect(text).toContain("DCH-2026-000007")
    expect(text).toContain("Dr Synthetic")
    expect(text).toContain("In stock")
    expect(text).toContain("Not in stock")
  })

  it("opens a prescription from its row button, which names it", async () => {
    const onOpen = vi.fn()
    render(<PrescriptionQueue hospitalId={4} stock={STOCK} onOpen={onOpen} />)
    await flush()
    const button = host.querySelector('button[aria-label="Open RX-0007 for Synthetic Queue"]')
    expect(button).not.toBeNull()
    act(() => button.click())
    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ apiId: 7, patientUhid: "DCH-2026-000007" }))
  })

  it("switches to transcriptions awaiting verification", async () => {
    render(<PrescriptionQueue hospitalId={4} stock={STOCK} onOpen={() => {}} />)
    await flush()
    const tab = [...host.querySelectorAll('[role="tab"]')].find((el) => el.textContent.includes("Awaiting verification"))
    act(() => tab.click())
    await flush()
    expect(api.prescriptions.list).toHaveBeenLastCalledWith(expect.objectContaining({ status: "Pending Verification" }))
  })
})

describe("Dispense line instructions", () => {
  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("shows the saved instructions and never makes one up", () => {
    const line = (medicine) => (
      <DispenseLine medicine={medicine} stock={STOCK} choice={{}} onChange={() => {}} done={false} />
    )
    render(
      <>
        {line({ id: 1, name: "Paracetamol", dosage: "1 tablet", frequency: "1-1-1", duration: "5 days", quantity: 15, instructions: "After food" })}
        {line({ id: 2, name: "Cetirizine", dosage: "", frequency: "0-0-1", duration: "5 days", quantity: 5, instructions: "" })}
      </>,
    )
    const [first, second] = host.querySelectorAll("dl")
    expect(first.textContent).toContain("After food")
    expect(first.textContent).toContain("1-1-1")
    expect(second.textContent).toContain("None written")
    expect(second.textContent).not.toContain("After food")
  })
})
