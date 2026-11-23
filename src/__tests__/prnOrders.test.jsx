import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// H-10: as-needed (PRN) orders carry optional dose limits set by the doctor,
// and nurses record PRN doses from the medicine orders view. Synthetic data only.
const toast = { success: vi.fn(), error: vi.fn(), info: vi.fn() }
vi.mock("../services/api.js", () => ({
  default: {
    nurses: { mar: { list: vi.fn(), create: vi.fn(), stop: vi.fn(), givePrn: vi.fn() } },
    prescriptions: { list: vi.fn() },
  },
}))
vi.mock("../components/Toast.jsx", () => ({ useToast: () => toast }))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import MedicationOrders from "../components/ipd/MedicationOrders.jsx"
import { isPrnFrequency, prnLimitText } from "../utils/prnLimits.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const button = (label) => [...document.body.querySelectorAll("button")].find((b) => b.textContent.trim() === label)
const plain = (text, values = {}) => text.replace(/\{(\w+)\}/g, (_, k) => values[k])

function type(element, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  })
}

const inputLabelled = (text) => {
  const label = [...document.body.querySelectorAll("label")].find((l) => l.textContent.includes(text))
  return label && (document.getElementById(label.htmlFor) || label.parentElement.querySelector("input"))
}

async function render(props) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  const admission = { id: 5, patient: 12, patient_name: "Synthetic Patient" }
  act(() => root.render(
    <LanguageProvider>
      <MedicationOrders open admission={admission} hospitalId={4} onClose={() => {}} {...props} />
    </LanguageProvider>,
  ))
  await flush()
}

async function submitPrompt(text) {
  type(document.getElementById("hms-prompt-input"), text)
  await act(async () => {
    document.getElementById("hms-prompt-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }))
  })
  await flush()
}

const PRN_ORDER = {
  id: 7, medicine_name: "Synthetic Paracetamol", dose: "500 mg", route: "Oral", frequency: "PRN",
  start_date: "2026-11-21", end_date: null, is_active: true, ordered_by_name: "Dr Synthetic",
  prn_min_interval_minutes: 240, prn_max_doses_per_24h: 3,
}
const SCHEDULED_ORDER = { ...PRN_ORDER, id: 8, medicine_name: "Synthetic Amoxicillin", frequency: "TID",
  prn_min_interval_minutes: null, prn_max_doses_per_24h: null }

describe("PRN helpers", () => {
  it("reads the same as-needed words as the server", () => {
    expect(["PRN", "sos", "PRN Q6H", "as needed"].every(isPrnFrequency)).toBe(true)
    expect(["TID", "Q8H", "", null].some(isPrnFrequency)).toBe(false)
  })

  it("describes the limits in one line, or nothing", () => {
    expect(prnLimitText(PRN_ORDER, plain)).toBe("at least 4 h apart · max 3 in 24 h")
    expect(prnLimitText({ prn_min_interval_minutes: 90 }, plain)).toBe("at least 1.50 h apart")
    expect(prnLimitText(SCHEDULED_ORDER, plain)).toBe("")
  })
})

describe("PRN orders (H-10)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.nurses.mar.list.mockResolvedValue([PRN_ORDER, SCHEDULED_ORDER])
    api.prescriptions.list.mockResolvedValue([
      { id: 40, items: [{ id: 41, name: "Synthetic Ibuprofen", dosage: "400 mg", frequency: "SOS" }] },
    ])
    api.nurses.mar.create.mockResolvedValue({ id: 9 })
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("shows the limits and lets a nurse give a PRN dose, and only for PRN orders", async () => {
    api.nurses.mar.givePrn.mockResolvedValue({ id: 70 })
    await render({ canOrder: false, canGive: true })
    expect(document.body.textContent).toContain("at least 4 h apart · max 3 in 24 h")
    const giveButtons = [...document.body.querySelectorAll("button")].filter((b) => b.textContent.trim() === "Give dose")
    expect(giveButtons).toHaveLength(1)

    await act(async () => button("Give dose").click())
    await submitPrompt(" Pain 6/10 ")
    expect(api.nurses.mar.givePrn).toHaveBeenCalledWith(7, "Pain 6/10")
    expect(toast.success).toHaveBeenCalled()
  })

  it("shows the server's refusal when a dose is too soon", async () => {
    api.nurses.mar.givePrn.mockRejectedValue(new Error("Too soon: the last dose was given at 21 Nov 10:00."))
    await render({ canOrder: false, canGive: true })
    await act(async () => button("Give dose").click())
    await submitPrompt("")
    expect(toast.error).toHaveBeenCalledWith("Too soon: the last dose was given at 21 Nov 10:00.")
  })

  it("does not offer Give dose to a doctor", async () => {
    await render({ canOrder: true, canGive: false })
    expect(button("Give dose")).toBeUndefined()
  })

  it("lets a doctor set the limits on a PRN order and sends them in minutes", async () => {
    await render({ canOrder: true })
    type(document.body.querySelector("form select"), "41")
    type(inputLabelled("Minimum hours between doses"), "6")
    type(inputLabelled("Most doses in 24 hours"), "4")
    await act(async () => button("Order medicine").click())
    await flush()
    expect(api.nurses.mar.create).toHaveBeenCalledWith(expect.objectContaining({
      frequency: "SOS", prn_min_interval_minutes: 360, prn_max_doses_per_24h: 4,
    }))
  })

  it("sends no limits when they are left empty", async () => {
    await render({ canOrder: true })
    type(document.body.querySelector("form select"), "41")
    await act(async () => button("Order medicine").click())
    await flush()
    expect(api.nurses.mar.create).toHaveBeenCalledWith(expect.objectContaining({
      prn_min_interval_minutes: null, prn_max_doses_per_24h: null,
    }))
  })
})
