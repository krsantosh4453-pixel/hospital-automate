import React, { act, useState } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it, vi } from "vitest"
import Icd10Typeahead from "../components/clinical/Icd10Typeahead.jsx"
import api from "../services/api.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

function DiagnosisForm() {
  const [form, setForm] = useState({ name: "", icd10Code: "" })
  return (
    <>
      <Icd10Typeahead
        aria-label="Diagnosis"
        value={form.name}
        onChange={(name) => setForm((prev) => ({ ...prev, name }))}
        onSelect={({ code, description }) => setForm({ name: description, icd10Code: code })}
      />
      <output>{form.icd10Code}</output>
    </>
  )
}

const typeInto = (input, text) => {
  const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set
  act(() => {
    setValue.call(input, text)
    input.dispatchEvent(new Event("input", { bubbles: true }))
  })
}

describe("Icd10Typeahead", () => {
  let root
  let host

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it("suggests ICD-10 codes and fills code and description on pick", async () => {
    vi.useFakeTimers()
    const search = vi.spyOn(api.terminology, "icd10Search").mockResolvedValue({
      results: [{ code: "E11.9", description: "Type 2 diabetes mellitus without complications" }],
    })
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    act(() => root.render(<DiagnosisForm />))
    const input = document.querySelector('input[aria-label="Diagnosis"]')

    typeInto(input, "d")
    await act(async () => vi.advanceTimersByTimeAsync(300))
    expect(search).not.toHaveBeenCalled()

    typeInto(input, "diab")
    await act(async () => vi.advanceTimersByTimeAsync(300))
    expect(search).toHaveBeenCalledWith("diab")
    const option = document.querySelector('[role="option"]')
    expect(option.textContent).toContain("E11.9")

    act(() => option.dispatchEvent(new MouseEvent("mousedown", { bubbles: true })))
    expect(input.value).toBe("Type 2 diabetes mellitus without complications")
    expect(document.querySelector("output").textContent).toBe("E11.9")
    // Picking does not search again for the filled-in description.
    await act(async () => vi.advanceTimersByTimeAsync(300))
    expect(search).toHaveBeenCalledTimes(1)
  })
})
