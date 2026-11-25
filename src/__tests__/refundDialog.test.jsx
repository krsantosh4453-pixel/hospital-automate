import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Remaining work (final validation): a bill's refund had no screen; the API
// alone could record one. Synthetic data only.
vi.mock("../services/api.js", () => ({ default: { billing: { invoices: { refund: vi.fn() } } } }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import RefundDialog, { refundToRecord } from "../components/billing/RefundDialog.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const BILL = { id: 5, invoice_number: "INV/26-27/000005", total_paid: "100.50" }
let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const text = () => document.body.textContent

function type(selector, value) {
  const element = document.body.querySelector(selector)
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(element, value)
    element.dispatchEvent(new Event("input", { bubbles: true }))
  })
}
const submit = () => act(async () => document.body.querySelector("#refund-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })))

async function open(handlers = {}) {
  await act(async () => root.render(<LanguageProvider><RefundDialog invoice={BILL} onClose={handlers.onClose || vi.fn()} onRefunded={handlers.onRefunded || vi.fn()} /></LanguageProvider>))
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

describe("refundToRecord", () => {
  it("keeps paise exact and never more than was paid", () => {
    expect(refundToRecord("10.25", "100.50")).toEqual({ amount: "10.25" })
    expect(refundToRecord("100.50", "100.50")).toEqual({ amount: "100.50" })
    expect(refundToRecord("100.51", "100.50").error).toMatch(/At most ₹100.50/)
    expect(refundToRecord("10.999", "100.50").error).toMatch(/2 decimal/)
    expect(refundToRecord("0", "100.50").error).toBeTruthy()
    expect(refundToRecord("-5", "100.50").error).toBeTruthy()
  })
})

describe("RefundDialog", () => {
  it("sends amount, reason, method and one idempotency key, then reports back", async () => {
    api.billing.invoices.refund.mockResolvedValue({ amount: "10.25", receipt_number: "RCPT-1" })
    const onRefunded = vi.fn()
    const onClose = vi.fn()
    await open({ onRefunded, onClose })

    type("#refund-amount", "10.25")
    type("#refund-reason", "Synthetic: test not done")
    await submit()
    await flush()

    const [id, body] = api.billing.invoices.refund.mock.calls[0]
    expect(id).toBe(5)
    expect(body).toMatchObject({ amount: "10.25", reason: "Synthetic: test not done", payment_method: "Cash" })
    expect(body.idempotency_key).toBeTruthy()
    expect(onRefunded).toHaveBeenCalledWith(expect.objectContaining({ receipt_number: "RCPT-1" }))
    expect(onClose).toHaveBeenCalled()
  })

  it("asks for a reason and refuses more than was paid, before any request", async () => {
    await open()
    type("#refund-amount", "10.00")
    await submit()
    expect(text()).toContain("Give the reason for the refund.")
    type("#refund-reason", "Synthetic")
    type("#refund-amount", "500.00")
    await submit()
    expect(text()).toContain("At most ₹100.50")
    expect(api.billing.invoices.refund).not.toHaveBeenCalled()
  })

  it("shows the server's refusal and keeps the same key for a retry", async () => {
    api.billing.invoices.refund.mockRejectedValueOnce(new Error("Refund exceeds the amount paid (50.00)."))
      .mockResolvedValueOnce({ amount: "10.00", receipt_number: "RCPT-2" })
    await open()
    type("#refund-amount", "10.00")
    type("#refund-reason", "Synthetic")
    await submit()
    await flush()
    expect(text()).toContain("Refund exceeds the amount paid")
    await submit()
    await flush()
    const keys = api.billing.invoices.refund.mock.calls.map(([, body]) => body.idempotency_key)
    expect(keys[0]).toBe(keys[1])
  })
})
