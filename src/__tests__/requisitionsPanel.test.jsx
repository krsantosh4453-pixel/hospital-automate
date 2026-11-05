import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// I2: who sees which requisition action, and the order request sent.
vi.mock("../services/api.js", () => ({
  default: {
    departments: { list: vi.fn() },
    procurement: {
      requisitions: { list: vi.fn(), create: vi.fn(), approve: vi.fn(), reject: vi.fn(), order: vi.fn() },
      quotations: { list: vi.fn(), create: vi.fn(), accept: vi.fn() },
    },
  },
}))
vi.mock("../components/Toast.jsx", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }) }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import RequisitionsPanel from "../components/inventory/RequisitionsPanel.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const ROWS = [
  { id: 1, reference: "REQ-1", status: "Submitted", department_name: "Ward A", requested_by_name: "pharmacist",
    items: [{ id: 11, medicine_name: "Saline", quantity: 30 }] },
  { id: 2, reference: "REQ-2", status: "Approved", department_name: "", requested_by_name: "pharmacist",
    items: [{ id: 21, medicine_name: "Gloves", quantity: 100 }] },
]

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const buttons = (label) => [...document.body.querySelectorAll("button")].filter((b) => b.textContent.trim() === label)

function type(element, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  })
}

async function render(props) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(
    <LanguageProvider>
      <RequisitionsPanel hospital={{ id: 4 }} medicines={[]} suppliers={[{ id: 7, name: "Synthetic Pharma", is_active: true }]} {...props} />
    </LanguageProvider>,
  ))
  await flush()
}

describe("Requisitions panel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.procurement.requisitions.list.mockResolvedValue(ROWS)
    api.procurement.quotations.list.mockResolvedValue([])
    api.procurement.requisitions.order.mockResolvedValue({})
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("shows approve only to approvers and order only to the store", async () => {
    await render({ canRaise: true, canApprove: false, canOrder: false })
    expect(buttons("Approve")).toHaveLength(0)
    expect(buttons("Order")).toHaveLength(0)
    act(() => root.unmount())
    host.remove()
    await render({ canRaise: true, canApprove: true, canOrder: true })
    expect(buttons("Approve")).toHaveLength(1)
    expect(buttons("Order")).toHaveLength(1)
  })

  it("orders an approved requisition with a cost for every line", async () => {
    await render({ canRaise: true, canApprove: true, canOrder: true })
    await act(async () => buttons("Order")[0].click())
    await flush()
    type(document.body.querySelector("select"), "7")
    expect(buttons("Place purchase order")[0].disabled).toBe(true)
    type(document.body.querySelector('input[type="number"]'), "4.5")
    await act(async () => buttons("Place purchase order")[0].click())
    expect(api.procurement.requisitions.order).toHaveBeenCalledWith(2, { supplier: 7, unit_costs: [{ item: 21, unit_cost: "4.5" }] }, 4)
  })
})
