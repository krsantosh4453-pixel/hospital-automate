import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// P1-03 (DPDP Act): the patient sees who answers data requests and can file one.
vi.mock("../services/api.js", () => ({
  default: { consent: { rights: { list: vi.fn(), create: vi.fn(), notice: vi.fn() } } },
}))
vi.mock("../components/Toast.jsx", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn() }) }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import DataRightsCard from "../components/consent/DataRightsCard.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const NOTICE = {
  hospital: 4, hospital_name: "Synthetic Hospital", response_days: 30,
  grievance_officer: { name: "Synthetic Officer", email: "privacy@example.test", phone: "9000000080" },
  kinds: [{ value: "access", label: "A summary of my data" }, { value: "erasure", label: "Erase my data" }],
}
const EARLIER = { id: 9, kind: "access", kind_label: "A summary of my data", status: "completed", status_label: "",
  response: "Sent by post.", created_at: "2026-11-01T10:00:00Z", due_at: "2026-12-01T10:00:00Z", overdue: false }

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))

function change(element, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  })
}

describe("DataRightsCard", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    api.consent.rights.notice.mockResolvedValue(NOTICE)
    api.consent.rights.list.mockResolvedValue({ results: [EARLIER] })
    api.consent.rights.create.mockResolvedValue({ ...EARLIER, id: 10, kind: "erasure", status: "received" })
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    act(() => root.render(<LanguageProvider><DataRightsCard hospitalId={4} /></LanguageProvider>))
    await flush()
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("names the grievance officer and the answer time", () => {
    expect(host.textContent).toContain("Synthetic Officer")
    expect(host.textContent).toContain("privacy@example.test")
    expect(host.textContent).toContain("30")
  })

  it("lists earlier requests with their answer", () => {
    expect(host.textContent).toContain("A summary of my data")
    expect(host.textContent).toContain("Sent by post.")
  })

  it("files a request for this hospital", async () => {
    change(host.querySelector("select"), "erasure")
    change(host.querySelector("textarea"), "Remove my old address.")
    await act(async () => host.querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })))

    expect(api.consent.rights.create).toHaveBeenCalledWith({ hospital: 4, kind: "erasure", details: "Remove my old address." })
  })
})
