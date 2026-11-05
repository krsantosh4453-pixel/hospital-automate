import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// H4: the billing page's advance card sends one ledger movement at a time.
vi.mock("../services/api.js", () => ({
  default: {
    patients: { list: vi.fn() },
    billing: {
      invoices: { list: vi.fn() },
      advances: { list: vi.fn(), deposit: vi.fn(), refund: vi.fn(), applyToInvoice: vi.fn() },
    },
  },
}))
vi.mock("../components/Toast.jsx", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }) }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import AdvancePayments from "../components/billing/AdvancePayments.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const ACCOUNT = { id: 7, patient: 12, patient_name: "Synthetic Depositor", balance: "1000.00", transactions: [
  { id: 1, kind: "deposit", amount: "1000.00", receipt_number: "ADV-1", created_at: "2026-11-05T10:00:00Z", created_by_name: "desk" },
] }

let host
let root
const flush = (ms = 0) => act(() => new Promise((resolve) => setTimeout(resolve, ms)))
const button = (label) => [...document.body.querySelectorAll("button")].find((b) => b.textContent.trim() === label)

function type(element, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  })
}

async function render(props = {}) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<LanguageProvider><AdvancePayments hospitalId={4} canRefund={false} {...props} /></LanguageProvider>))
  await flush()
}

describe("Advance payments card", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.billing.advances.list.mockResolvedValue([ACCOUNT])
    api.billing.advances.deposit.mockResolvedValue({})
    api.billing.advances.applyToInvoice.mockResolvedValue({})
    api.patients.list.mockResolvedValue({ results: [{ id: 12, name: "Synthetic Depositor" }] })
    api.billing.invoices.list.mockResolvedValue({ results: [
      { id: 30, invoice_number: "INV-30", patient: 12, status: "Unpaid", balance_due: "600.00" },
      { id: 31, invoice_number: "INV-31", patient: 12, status: "Paid", balance_due: "0.00" },
      { id: 32, invoice_number: "INV-32", patient: 99, status: "Unpaid", balance_due: "50.00" },
    ] })
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("lists balances and hides refunds from roles that may not refund", async () => {
    await render()
    expect(host.textContent).toContain("Synthetic Depositor")
    expect(host.textContent).toContain("₹1,000.00")
    expect(button("Refund")).toBeUndefined()
    expect(button("Adjust against bill")).toBeDefined()
  })

  it("receives an advance for a chosen patient with an idempotency key", async () => {
    await render()
    await act(async () => button("Receive advance").click())
    type(document.body.querySelector('input[placeholder="Search by name or phone"]'), "Synth")
    await flush(300)
    await act(async () => [...document.body.querySelectorAll("li button")].find((b) => b.textContent.includes("Synthetic")).click())
    type(document.body.querySelector('input[type="number"]'), "500")
    await act(async () => button("Save").click())
    expect(api.billing.advances.deposit).toHaveBeenCalledWith(expect.objectContaining({
      hospital: 4, patient: 12, amount: "500", payment_method: "Cash", idempotency_key: expect.stringMatching(/^adv-/),
    }))
  })

  it("offers only this patient's unpaid bills when adjusting", async () => {
    await render()
    await act(async () => button("Adjust against bill").click())
    await flush()
    const options = [...document.body.querySelectorAll("select option")].map((o) => o.textContent)
    expect(options.some((o) => o.includes("INV-30"))).toBe(true)
    expect(options.some((o) => o.includes("INV-31") || o.includes("INV-32"))).toBe(false)
    type(document.body.querySelector("select"), "30")
    type(document.body.querySelector('input[type="number"]'), "600")
    await act(async () => button("Save").click())
    expect(api.billing.advances.applyToInvoice).toHaveBeenCalledWith("30", expect.objectContaining({ amount: "600" }))
  })
})
