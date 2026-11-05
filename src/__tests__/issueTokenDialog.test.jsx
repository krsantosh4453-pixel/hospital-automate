import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it, vi } from "vitest"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import IssueTokenDialog from "../components/queue/IssueTokenDialog.jsx"

// The desk sees who each booked appointment is for and chooses which one
// checks in; it used to issue the earliest appointment with one click.
globalThis.IS_REACT_ACT_ENVIRONMENT = true

const APPOINTMENTS = [
  { apiId: 3, patient: "Synthetic Early", time: "09:30:00", doctor: "Dr Mehta", contact: "9000000001", reason: "Fever" },
  { apiId: 4, patient: "Synthetic Late", time: "11:15:00", doctor: "Dr Verma", contact: "9000000002" },
]

let host
let root

function render(onIssue) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  act(() => root.render(
    <LanguageProvider>
      <IssueTokenDialog open appointments={APPOINTMENTS} busy={false} onClose={() => {}} onIssue={onIssue} />
    </LanguageProvider>,
  ))
}

const button = (start) => [...document.body.querySelectorAll("button")].find((b) => b.textContent.trim().startsWith(start))

describe("Issue token dialog", () => {
  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("shows patient, time, doctor and contact before check-in", () => {
    render(() => {})
    const text = document.body.textContent
    expect(text).toContain("Synthetic Early")
    expect(text).toContain("09:30 · Dr Mehta · 9000000001")
    expect(text).toContain("Fever")
    expect(text).toContain("11:15 · Dr Verma")
  })

  it("issues the appointment the desk chose, not just the earliest", () => {
    const onIssue = vi.fn()
    render(onIssue)
    expect(button("Issue token for").textContent).toContain("Synthetic Early")
    act(() => document.body.querySelector("#issue-appointment-4").click())
    expect(button("Issue token for").textContent).toContain("Synthetic Late")
    act(() => button("Issue token for").click())
    expect(onIssue).toHaveBeenCalledWith(expect.objectContaining({ apiId: 4 }))
  })
})
