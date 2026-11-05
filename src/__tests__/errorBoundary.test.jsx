import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import ErrorBoundary from "../components/ErrorBoundary.jsx"

// RL-08: one page that throws while rendering must not blank the whole app.
globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root

beforeEach(() => {
  // React reports the caught render error on the console; keep the test output readable.
  vi.spyOn(console, "error").mockImplementation(() => {})
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
})

afterEach(() => {
  act(() => root.unmount())
  host.remove()
  vi.restoreAllMocks()
})

let shouldThrow = true
function Page() {
  if (shouldThrow) throw new Error("patient.name is undefined")
  return <p>Page content</p>
}

function render(resetKey = "/billing") {
  act(() => root.render(
    <LanguageProvider>
      <ErrorBoundary resetKey={resetKey}><Page /></ErrorBoundary>
    </LanguageProvider>,
  ))
}

const button = (label) => [...host.querySelectorAll("button")].find((b) => b.textContent.trim() === label)

describe("ErrorBoundary", () => {
  beforeEach(() => { shouldThrow = true })

  it("shows a recovery screen instead of a blank page", () => {
    render()

    expect(host.textContent).toContain("This page could not be shown")
    expect(button("Try again")).toBeTruthy()
    expect(button("Reload page")).toBeTruthy()
  })

  it("Try again renders the page again once it works", () => {
    render()
    shouldThrow = false

    act(() => button("Try again").click())

    expect(host.textContent).toContain("Page content")
  })

  it("going to another page clears the error", () => {
    render("/billing")
    shouldThrow = false

    render("/patients")

    expect(host.textContent).toContain("Page content")
  })

  it("Reload page reloads the browser", () => {
    const reload = vi.fn()
    vi.spyOn(window, "location", "get").mockReturnValue({ ...window.location, reload })
    render()

    act(() => button("Reload page").click())

    expect(reload).toHaveBeenCalled()
  })
})
