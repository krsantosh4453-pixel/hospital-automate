import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Hospital services panel: buttons follow status and role; forms send typed values.
vi.mock("../services/api.js", () => ({
  default: { services: { list: vi.fn(), create: vi.fn(), act: vi.fn() } },
}))
vi.mock("../components/Toast.jsx", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn() }) }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import ResourcePanel from "../components/services/ResourcePanel.jsx"
import { SERVICE_TABS } from "../components/services/serviceConfigs.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const laundry = SERVICE_TABS.find((tab) => tab.id === "laundry").panels[0]
const leave = SERVICE_TABS.find((tab) => tab.id === "leave").panels[0]

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const buttons = (label) => [...document.body.querySelectorAll("button")].filter((b) => b.textContent.trim() === label)

async function render(config, role) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(<LanguageProvider><ResourcePanel hospitalId={4} config={config} role={role} /></LanguageProvider>))
  await flush()
}

function type(element, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event("input", { bubbles: true }))
  })
}

describe("Hospital services panel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.services.act.mockResolvedValue({})
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("offers each status action only on rows in that status", async () => {
    api.services.list.mockResolvedValue([
      { id: 1, status: "Sent", department_name: "Ward A", item_type: "Sheets", quantity_sent: 40 },
      { id: 2, status: "Returned", department_name: "Ward A", item_type: "Gowns", quantity_sent: 10, quantity_returned: 9, shortfall: 1 },
    ])
    await render(laundry, "Nurse")
    expect(buttons("Received back")).toHaveLength(1)
  })

  it("hides manager-only actions from other roles", async () => {
    api.services.list.mockResolvedValue([{ id: 5, status: "Pending", staff_name: "nurse", kind: "Casual" }])
    await render(leave, "Nurse")
    expect(buttons("Approve")).toHaveLength(0)
    act(() => root.unmount())
    host.remove()
    await render(leave, "Hospital Manager")
    await act(async () => buttons("Approve")[0].click())
    await flush()
    expect(api.services.act).toHaveBeenCalledWith("leave", 5, "approve", {}, 4)
  })

  it("asks for an action's fields and sends numbers as numbers", async () => {
    api.services.list.mockResolvedValue([{ id: 1, status: "Sent", department_name: "Ward A", item_type: "Sheets", quantity_sent: 40 }])
    await render(laundry, "Nurse")
    await act(async () => buttons("Received back")[0].click())
    type(document.body.querySelector('input[type="number"]'), "38")
    await act(async () => buttons("Save")[0].click())
    expect(api.services.act).toHaveBeenCalledWith("laundry", 1, "returned", { quantity_returned: 38 }, 4)
  })
})
