import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// P1-10: the Schedule H1 register lists every scheduled sale with its prescriber and patient.
vi.mock("../services/api.js", () => ({
  default: { pharmacy: { sales: { h1Register: vi.fn() } } },
}))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import H1Register from "../components/pharmacy/H1Register.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const ROW = {
  date: "2026-11-08 10:15", sale: "SALE-12", prescription: 4, patient: "Synthetic Scheduled", patient_uhid: "REG-1",
  prescriber: "Dr Synthetic", prescriber_registration: "MCI-12345", medicine: "Tab Synthetic H1", schedule: "H1",
  batch: "H1B", quantity: 6, dispensed_by: "pharmacist",
}

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))

function setDate(input, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value").set
  act(() => {
    setter.call(input, value)
    input.dispatchEvent(new Event("input", { bubbles: true }))
  })
}

async function render() {
  act(() => root.render(<LanguageProvider><H1Register hospitalId={4} /></LanguageProvider>))
  await flush()
}

describe("H1Register", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    api.pharmacy.sales.h1Register.mockResolvedValue({ results: [ROW] })
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("lists prescriber with registration, patient with UHID, drug, batch and quantity", async () => {
    await render()

    expect(api.pharmacy.sales.h1Register).toHaveBeenCalledWith(4, expect.objectContaining({ from: expect.any(String) }))
    const text = host.textContent
    for (const part of ["Dr Synthetic", "MCI-12345", "Synthetic Scheduled", "REG-1", "Tab Synthetic H1", "H1B", "SALE-12"]) {
      expect(text).toContain(part)
    }
  })

  it("asks the server again when the date range changes", async () => {
    await render()

    setDate(host.querySelector('input[name="from"]'), "2026-10-01")
    await flush()

    expect(api.pharmacy.sales.h1Register).toHaveBeenLastCalledWith(4, expect.objectContaining({ from: "2026-10-01" }))
  })

  it("says so when nothing was recorded", async () => {
    api.pharmacy.sales.h1Register.mockResolvedValue({ results: [] })
    await render()

    expect(host.textContent).toContain("No scheduled sales in these dates")
  })
})
