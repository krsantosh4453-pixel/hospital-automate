import React, { act, useState } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it, vi } from "vitest"
import DischargeDraftAssist from "../components/ipd/DischargeDraftAssist.jsx"
import api from "../services/api.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const DRAFT = {
  draft_id: 7, text: "Diagnoses:\n- Pneumonia", source: "records", warnings: ["No AI model is configured."],
  notice: "AI-assisted draft. Check every line.",
}

function SummaryForm({ onSave }) {
  const [text, setText] = useState("")
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSave(text) }}>
      <DischargeDraftAssist admission={{ id: 3 }} text={text} onText={setText} />
      <textarea aria-label="Summary" value={text} onChange={(e) => setText(e.target.value)} />
    </form>
  )
}

describe("DischargeDraftAssist", () => {
  let root
  let host

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
    vi.restoreAllMocks()
  })

  it("fills the draft, requires review, and records an edited outcome on save", async () => {
    vi.spyOn(api.ai.dischargeDrafts, "generate").mockResolvedValue(DRAFT)
    const review = vi.spyOn(api.ai.dischargeDrafts, "review").mockResolvedValue({})
    const onSave = vi.fn()
    host = document.createElement("div")
    document.body.appendChild(host)
    root = createRoot(host)
    act(() => root.render(<SummaryForm onSave={onSave} />))

    const button = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Draft with AI"))
    await act(async () => button.click())
    const textarea = document.querySelector('textarea[aria-label="Summary"]')
    expect(textarea.value).toBe(DRAFT.text)

    const form = document.querySelector("form")
    const checkbox = document.querySelector('input[type="checkbox"]')
    expect(checkbox.required).toBe(true)
    expect(form.checkValidity()).toBe(false)

    const setValue = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set
    act(() => {
      setValue.call(textarea, `${DRAFT.text}\nFollow-up: 1 week`)
      textarea.dispatchEvent(new Event("input", { bubbles: true }))
    })
    act(() => checkbox.click())
    expect(form.checkValidity()).toBe(true)
    act(() => form.requestSubmit())

    expect(onSave).toHaveBeenCalledWith(`${DRAFT.text}\nFollow-up: 1 week`)
    expect(review).toHaveBeenCalledWith(3, { draft_id: 7, outcome: "edited" })
  })
})
