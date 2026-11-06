import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// RL-03: patients are chosen by server search (any patient, not the newest 50), by id, with the UHID shown.
vi.mock("../services/api.js", () => ({
  default: { patients: { list: vi.fn(), lookup: vi.fn() } },
}))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import PatientPicker from "../components/patients/PatientPicker.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const RAVI_A = { id: 10, name: "Ravi Sharma", uhid: "DCH-2026-000010", age: 41, gender: "Male", phone: "9811100001" }
const RAVI_B = { id: 11, name: "Ravi Sharma", uhid: "DCH-2026-000011", age: 67, gender: "Male", phone: "9811100002" }

let host
let root
let onChange
const flush = (ms = 0) => act(() => new Promise((resolve) => setTimeout(resolve, ms)))

function type(element, value) {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set
  act(() => {
    setter.call(element, value)
    element.dispatchEvent(new Event("input", { bubbles: true }))
  })
}

function render(props = {}) {
  act(() => root.render(
    <LanguageProvider>
      <PatientPicker hospitalId={4} value="" onChange={onChange} {...props} />
    </LanguageProvider>,
  ))
}

const input = () => host.querySelector("input")
const results = () => [...host.querySelectorAll("li button")]

describe("PatientPicker", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    onChange = vi.fn()
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    api.patients.list.mockResolvedValue({ results: [RAVI_A, RAVI_B] })
    api.patients.lookup.mockResolvedValue([RAVI_A])
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("searches the server, so any registered patient can be found", async () => {
    render()
    type(input(), "Ravi")
    await flush(300)

    expect(api.patients.list).toHaveBeenCalledWith(4, 1, "Ravi")
  })

  it("tells same-name patients apart by UHID, age and masked phone", async () => {
    render()
    type(input(), "Ravi")
    await flush(300)

    const [first, second] = results()
    expect(first.textContent).toContain("DCH-2026-000010")
    expect(second.textContent).toContain("DCH-2026-000011")
    expect(second.textContent).toContain("67")
    expect(second.textContent).toContain("••••0002")
    expect(second.textContent).not.toContain("9811100002")
  })

  it("selects by id only when a result is clicked, never by a matching name", async () => {
    render()
    type(input(), "Ravi Sharma")
    await flush(300)
    expect(onChange).not.toHaveBeenCalled()

    act(() => results()[1].click())

    expect(onChange).toHaveBeenCalledWith("11", RAVI_B)
  })

  it("shows the chosen patient with UHID and lets the user change it", async () => {
    render({ value: "11", selected: RAVI_B })

    expect(host.textContent).toContain("DCH-2026-000011")
    act(() => [...host.querySelectorAll("button")].find((b) => b.textContent.trim() === "Change").click())

    expect(onChange).toHaveBeenCalledWith("", null)
  })

  it("waits for two characters before searching", async () => {
    render()
    type(input(), "R")
    await flush(300)

    expect(api.patients.list).not.toHaveBeenCalled()
  })

  it("says so when nothing matches", async () => {
    api.patients.list.mockResolvedValue({ results: [] })
    render()
    type(input(), "Nobody")
    await flush(300)

    expect(host.textContent).toContain("No patient matches")
  })

  it("uses the minimal lookup, from three characters, for roles that may not list patients", async () => {
    render({ source: "lookup" })
    type(input(), "Ra")
    await flush(300)
    expect(api.patients.lookup).not.toHaveBeenCalled()

    type(input(), "Rav")
    await flush(300)

    expect(api.patients.lookup).toHaveBeenCalledWith(4, "Rav")
    expect(api.patients.list).not.toHaveBeenCalled()
  })
})
