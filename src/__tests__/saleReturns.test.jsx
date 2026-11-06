import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// F5: the pharmacy returns card. Returns are capped by the server; the card
// offers a return only while something is left and only to pharmacists.
vi.mock("../services/api.js", () => ({
  default: { pharmacy: { sales: { list: vi.fn(), returnSale: vi.fn() } } },
}))
vi.mock("../components/Toast.jsx", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }) }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import SaleReturns from "../components/pharmacy/SaleReturns.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const buttons = (label) => [...document.body.querySelectorAll("button")].filter((b) => b.textContent.trim() === label)

function type(element, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event("input", { bubbles: true }))
  })
}

async function render(canReturn) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<LanguageProvider><SaleReturns hospitalId={4} canReturn={canReturn} /></LanguageProvider>))
  await flush()
}

describe("Medicine returns card", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.pharmacy.sales.list.mockResolvedValue([
      { id: 1, patient_name: "Synthetic Buyer", medicine_name: "Dolo 500", substituted_for: "Crocin 500", quantity: 10, returned_quantity: 2 },
      { id: 2, patient_name: "Synthetic Other", medicine_name: "Brufen 400", quantity: 5, returned_quantity: 5 },
    ])
    api.pharmacy.sales.returnSale.mockResolvedValue({ refund_amount: "6.00" })
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("shows substitutions and offers returns only while something is left", async () => {
    await render(true)
    expect(host.textContent).toContain("Instead of Crocin 500")
    expect(buttons("Return")).toHaveLength(1)
  })

  it("hides returns from roles that may not take them", async () => {
    await render(false)
    expect(buttons("Return")).toHaveLength(0)
  })

  it("sends quantity, reason and the restock choice", async () => {
    await render(true)
    await act(async () => buttons("Return")[0].click())
    type(document.body.querySelector('input[type="number"]'), "3")
    type(document.body.querySelector('input[placeholder="e.g. Course stopped by doctor"]'), "Course stopped")
    await act(async () => document.body.querySelector('input[type="checkbox"]').click())
    await act(async () => buttons("Record return")[0].click())
    expect(api.pharmacy.sales.returnSale).toHaveBeenCalledWith(1, { quantity: 3, reason: "Course stopped", restock: true })
  })

  it("uses the sales the Pharmacy page already loaded instead of asking again (F7)", async () => {
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    const sales = [{ id: 5, patient_name: "Synthetic Given", medicine_name: "Pan 40", quantity: 3, returned_quantity: 0 }]
    act(() => root.render(<LanguageProvider><SaleReturns hospitalId={4} canReturn sales={sales} /></LanguageProvider>))
    await flush()
    expect(host.textContent).toContain("Synthetic Given")
    expect(api.pharmacy.sales.list).not.toHaveBeenCalled()
  })
})
