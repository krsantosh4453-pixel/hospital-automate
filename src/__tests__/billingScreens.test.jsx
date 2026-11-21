import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// B-4: price list, unbilled work and priced bill lines on the Billing page.
// Synthetic data only.
const toast = { success: vi.fn(), error: vi.fn(), warning: vi.fn() }
vi.mock("../components/Toast.jsx", () => ({ useToast: () => toast }))
vi.mock("../services/api.js", () => ({
  default: {
    billing: {
      priceList: { list: vi.fn(), create: vi.fn(), retire: vi.fn(), unbilled: vi.fn(), chargeUnbilled: vi.fn() },
    },
  },
}))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import PriceList from "../components/billing/PriceList.jsx"
import PricedServicePicker from "../components/billing/PricedServicePicker.jsx"
import UnbilledWork from "../components/billing/UnbilledWork.jsx"
import { itemsData, otherLinesOf, pickablePrices, pricedAmount } from "../utils/billingLines.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const button = (label) => [...document.body.querySelectorAll("button")].find((b) => b.textContent.trim() === label)
const buttonStarting = (label) =>
  [...document.body.querySelectorAll("button")].find((b) => b.textContent.trim().startsWith(label))

function type(element, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  })
}

const inputLabelled = (text) => {
  const label = [...document.body.querySelectorAll("label")].find((l) => l.textContent.trim().startsWith(text))
  return label && (document.getElementById(label.htmlFor) || label.parentElement.querySelector("input, select"))
}

async function render(element) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<LanguageProvider>{element}</LanguageProvider>))
  await flush()
}

const PRICES = [
  { id: 1, category: "consultation", code: "CON-OPD", name: "OPD consultation", applies_to: "OPD", unit_price: "500.00",
    tax_rate: "0.00", effective_from: "2026-11-01", is_current: true },
  { id: 2, category: "procedure", code: "PRO-DRESS", name: "Dressing", applies_to: "", unit_price: "150.00",
    tax_rate: "18.00", effective_from: "2026-11-01", is_current: true },
  { id: 3, category: "bed", code: "BED-GEN", name: "General bed", applies_to: "", unit_price: "1000.00",
    tax_rate: "0.00", effective_from: "2026-11-01", is_current: true },
]

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  if (root) act(() => root.unmount())
  host?.remove()
  root = null
  host = null
})

describe("bill line helpers", () => {
  it("offers only services that are not charged automatically", () => {
    expect(pickablePrices(PRICES).map((p) => p.id)).toEqual([2])
  })

  it("counts GST in a priced line", () => {
    expect(pricedAmount({ unit_price: "150.00", tax_rate: "18.00", quantity: 2 })).toBe(354)
  })

  it("keeps an edited bill's priced and other lines instead of dropping them", () => {
    const { priced, kept } = otherLinesOf([
      { description: "Doctor Consultation", unit_price: "300.00", quantity: 1 },
      { description: "Dressing", service_price: 2, unit_price: "150.00", tax_rate: "18.00", quantity: 1 },
      { description: "Ambulance", unit_price: "800.00", tax_rate: "0.00", quantity: 1 },
    ])
    expect(priced).toEqual([expect.objectContaining({ id: 2, quantity: 1 })])
    expect(kept).toEqual([{ description: "Ambulance", quantity: 1, unit_price: "800.00", tax_rate: "0.00" }])
    expect(itemsData([{ name: "Other Services", amount: 50 }], priced, kept)).toEqual([
      { description: "Other Services", quantity: 1, unit_price: 50 },
      { service_price: 2, quantity: 1 },
      { description: "Ambulance", quantity: 1, unit_price: "800.00", tax_rate: "0.00" },
    ])
  })
})

describe("Price list", () => {
  it("lets an admin add a price and retire one", async () => {
    api.billing.priceList.list.mockResolvedValue(PRICES)
    api.billing.priceList.create.mockResolvedValue({ id: 9 })
    api.billing.priceList.retire.mockResolvedValue({})
    await render(<PriceList hospitalId={4} canManage />)
    await act(async () => button("Show").click())
    expect(document.body.textContent).toContain("OPD consultation")

    type(inputLabelled("Code"), "LAB-LIPID")
    type(inputLabelled("Name"), "Lipid profile")
    type(inputLabelled("Category"), "laboratory")
    type(inputLabelled("Applies to"), "Lipid Profile")
    type(inputLabelled("Price"), "650")
    await act(async () => button("Add price").click())
    await flush()
    expect(api.billing.priceList.create).toHaveBeenCalledWith(expect.objectContaining({
      hospital: 4, category: "laboratory", code: "LAB-LIPID", name: "Lipid profile", applies_to: "Lipid Profile",
      unit_price: "650",
    }))

    await act(async () => [...document.body.querySelectorAll("button")].filter((b) => b.textContent.trim() === "Retire")[0].click())
    await act(async () => button("Retire price").click())
    await flush()
    expect(api.billing.priceList.retire).toHaveBeenCalledWith(1)
  })

  it("refuses a price of ₹0 before sending", async () => {
    api.billing.priceList.list.mockResolvedValue([])
    await render(<PriceList hospitalId={4} canManage />)
    await act(async () => button("Show").click())
    type(inputLabelled("Code"), "X")
    type(inputLabelled("Name"), "Free thing")
    type(inputLabelled("Price"), "0")
    // The browser's own min/required check blocks this too; submit directly
    // to prove the form's guard as well.
    const form = button("Add price").closest("form")
    await act(async () => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })))
    expect(document.body.textContent).toContain("price above ₹0")
    expect(api.billing.priceList.create).not.toHaveBeenCalled()
  })

  it("is read-only for billing staff", async () => {
    api.billing.priceList.list.mockResolvedValue(PRICES)
    await render(<PriceList hospitalId={4} canManage={false} />)
    await act(async () => button("Show").click())
    expect(document.body.textContent).toContain("Dressing")
    expect(button("Add price")).toBeUndefined()
    expect(button("Retire")).toBeUndefined()
  })
})

describe("Unbilled work", () => {
  const ROWS = {
    count: 2,
    results: [
      { kind: "consultation", id: 12, patient: 3, service: "OPD", date: "2026-11-20", priced: true },
      { kind: "laboratory", id: 5, patient: 3, service: "Lipid Profile", date: "2026-11-20", priced: false },
    ],
  }

  it("lists the work and bills the priced part after confirmation", async () => {
    api.billing.priceList.unbilled.mockResolvedValueOnce(ROWS).mockResolvedValueOnce({ count: 1, results: [ROWS.results[1]] })
    api.billing.priceList.chargeUnbilled.mockResolvedValue({ charged: [ROWS.results[0]], unpriced: [ROWS.results[1]] })
    const onCharged = vi.fn()
    await render(<UnbilledWork hospitalId={4} canCharge onCharged={onCharged} />)
    expect(document.body.textContent).toContain("Unbilled work (2)")
    expect(document.body.textContent).toContain("Add a price first")

    await act(async () => buttonStarting("Bill priced work").click())
    await act(async () => button("Bill them").click())
    await flush()
    expect(api.billing.priceList.chargeUnbilled).toHaveBeenCalledWith(4, undefined)
    expect(onCharged).toHaveBeenCalled()
    expect(document.body.textContent).toContain("Unbilled work (1)")
  })

  it("is hidden when nothing is unbilled, and offers no button without the right", async () => {
    api.billing.priceList.unbilled.mockResolvedValue({ count: 0, results: [] })
    await render(<UnbilledWork hospitalId={4} canCharge />)
    expect(host.textContent).toBe("")
    act(() => root.unmount())
    host.remove()
    root = null

    api.billing.priceList.unbilled.mockResolvedValue(ROWS)
    await render(<UnbilledWork hospitalId={4} canCharge={false} />)
    expect(document.body.textContent).toContain("Unbilled work (2)")
    expect(buttonStarting("Bill priced work")).toBeUndefined()
  })
})

describe("Services from the price list", () => {
  it("offers only non-automatic services and adds the chosen one with its quantity", async () => {
    api.billing.priceList.list.mockResolvedValue(PRICES)
    const onChange = vi.fn()
    await render(<PricedServicePicker hospitalId={4} lines={[]} onChange={onChange} />)
    const select = document.body.querySelector("select")
    const offered = [...select.options].map((o) => o.textContent)
    expect(offered.some((text) => text.includes("Dressing"))).toBe(true)
    expect(offered.some((text) => text.includes("OPD consultation") || text.includes("General bed"))).toBe(false)

    type(select, "2")
    type(inputLabelled("Qty"), "2")
    await act(async () => button("Add service").click())
    expect(onChange).toHaveBeenCalledWith([expect.objectContaining({ id: 2, name: "Dressing", quantity: 2 })])
  })
})
