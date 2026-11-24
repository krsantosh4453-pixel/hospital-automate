import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Sign-in and Create Account share one dialog over the page the visitor is on.
vi.mock("../services/api.js", () => ({
  default: { auth: { register: vi.fn(), verifyEmailOtp: vi.fn(), requestEmailOtp: vi.fn() } },
}))

import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import { AuthLink, SignInDialog } from "../components/auth/SignInDialog.jsx"
import Register from "../pages/Register.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root
const flush = (ms = 0) => act(() => new Promise((resolve) => setTimeout(resolve, ms)))
const dialog = () => document.body.querySelector('[role="dialog"]')
const link = (label) => [...document.body.querySelectorAll("a")].find((a) => a.textContent.trim() === label)
const click = (element) => act(() => element.dispatchEvent(new MouseEvent("click", { bubbles: true, button: 0 })))

// Stands in for PatientLogin: the real page needs every auth provider.
function SignInStub() {
  const { search } = useLocation()
  return (
    <div>
      <p data-testid="signin-search">{search}</p>
      <AuthLink to={`/register?role=Patient${search.includes("next=book") ? "&next=book" : ""}`}>Create Account</AuthLink>
    </div>
  )
}

// Mirrors App's RoutesWithSignInDialog.
function Harness() {
  const location = useLocation()
  const background = location.state?.backgroundLocation
  return (
    <>
      <Routes location={background || location}>
        <Route path="/" element={<p data-testid="dashboard">Hospital dashboard</p>} />
        <Route path="/patient-login" element={<SignInStub />} />
        <Route path="/register" element={<Register />} />
      </Routes>
      {background && (
        <Routes>
          <Route path="/patient-login" element={<SignInDialog title="Sign in"><SignInStub /></SignInDialog>} />
          <Route path="/register" element={<SignInDialog title="Create an account"><Register /></SignInDialog>} />
          <Route path="*" element={null} />
        </Routes>
      )}
    </>
  )
}

async function render(entry) {
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  await act(async () => {
    root.render(
      <LanguageProvider>
        <MemoryRouter initialEntries={[entry]}>
          <Harness />
        </MemoryRouter>
      </LanguageProvider>,
    )
  })
  await flush()
}

const overDashboard = (pathname, search = "") => ({ pathname, search, state: { backgroundLocation: { pathname: "/" } } })

describe("sign-in and create account dialog", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    act(() => root.unmount())
    host.remove()
  })

  it("opens Create Account in the same dialog over the dashboard", async () => {
    await render(overDashboard("/patient-login"))
    expect(dialog().textContent).toContain("Sign in")

    await click(link("Create Account"))
    await flush()

    expect(dialog()).not.toBeNull()
    expect(dialog().querySelector("h2").textContent).toBe("Create an account")
    expect(document.body.querySelector('[data-testid="dashboard"]')).not.toBeNull()
    for (const id of ["reg-field-1", "reg-field-phone", "reg-field-2", "reg-field-3", "reg-field-4", "reg-field-5", "reg-field-14", "reg-field-15"]) {
      expect(dialog().querySelector(`#${id}`)).not.toBeNull()
    }
    expect(dialog().textContent).toContain("+91")
  })

  it("moves focus into the Create Account form when the dialog switches", async () => {
    await render(overDashboard("/patient-login"))
    await click(link("Create Account"))
    await flush()

    expect(dialog().contains(document.activeElement)).toBe(true)
    expect(document.activeElement.id).toBe("reg-field-1")
  })

  it("goes back to Sign in inside the dialog and keeps next=book", async () => {
    await render(overDashboard("/patient-login", "?next=book"))
    await click(link("Create Account"))
    await flush()

    await click(link("Sign in"))
    await flush()

    expect(dialog().querySelector("h2").textContent).toBe("Sign in")
    expect(dialog().querySelector('[data-testid="signin-search"]').textContent).toContain("next=book")
    expect(document.body.querySelector('[data-testid="dashboard"]')).not.toBeNull()
  })

  it("clears a stale error as soon as a field is edited", async () => {
    await render(overDashboard("/register"))
    const field = (id) => dialog().querySelector(`#${id}`)
    const type = (id, value) => act(() => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(field(id), value)
      field(id).dispatchEvent(new Event("input", { bubbles: true }))
    })
    type("reg-field-14", "Synth-Pass-1")
    type("reg-field-15", "Other-Pass-1")
    await act(() => dialog().querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })))
    expect(dialog().textContent).toContain("Password and confirm password do not match.")

    type("reg-field-15", "Synth-Pass-1")

    expect(dialog().textContent).not.toContain("Password and confirm password do not match.")
  })

  it("closes back to the dashboard", async () => {
    await render(overDashboard("/register"))

    await act(() => dialog().querySelector('button[aria-label="Close dialog"]').click())
    await flush()

    expect(dialog()).toBeNull()
    expect(document.body.querySelector('[data-testid="dashboard"]')).not.toBeNull()
  })

  it("still renders /register as a full page when opened directly", async () => {
    await render({ pathname: "/register" })

    expect(dialog()).toBeNull()
    expect(document.body.querySelector("h1").textContent).toBe("Create an account")
    await click(link("Sign in"))
    await flush()
    expect(dialog()).toBeNull()
    expect(document.body.querySelector('[data-testid="signin-search"]')).not.toBeNull()
  })
})
