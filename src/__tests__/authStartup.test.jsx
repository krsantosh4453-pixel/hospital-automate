import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// BUG-012: a patient's page load asked staff-only endpoints first
// (GET /auth/staff/me/ 403, GET /hospital/hospitals/ 403) on every load.
vi.mock("../services/api.js", async () => {
  const kind = { value: "" }
  return {
    accountKind: () => kind.value,
    rememberAccountKind: (k) => { kind.value = k },
    __kind: kind,
    default: {
      auth: {
        getTokens: vi.fn(() => ({ accessToken: "cookie", refreshToken: "cookie" })),
        getMe: vi.fn(), patientMe: vi.fn(), clearTokens: vi.fn(), applySession: vi.fn(), logout: vi.fn(),
      },
      hospitals: { list: vi.fn(), directory: vi.fn() },
    },
  }
})

import api, * as apiModule from "../services/api.js"
import { AuthProvider } from "../assets/context/AuthProvider.jsx"
import { HospitalsProvider } from "../assets/context/HospitalsContext.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root
async function mount(node) {
  await act(async () => root.render(node))
  await act(() => new Promise((resolve) => setTimeout(resolve, 0)))
}

beforeEach(() => {
  vi.clearAllMocks()
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
  api.auth.getMe.mockRejectedValue(Object.assign(new Error("Forbidden"), { status: 403 }))
  api.auth.patientMe.mockResolvedValue({ patient: { id: 3, name: "Synthetic" } })
  api.hospitals.list.mockRejectedValue(Object.assign(new Error("Forbidden"), { status: 403 }))
  api.hospitals.directory.mockResolvedValue([{ id: 1, name: "Synthetic One" }])
})
afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

describe("start-up for a patient session", () => {
  it("asks the patient endpoint and the public directory only", async () => {
    apiModule.__kind.value = "patient"
    await mount(<AuthProvider><HospitalsProvider><span /></HospitalsProvider></AuthProvider>)

    expect(api.auth.patientMe).toHaveBeenCalled()
    expect(api.auth.getMe).not.toHaveBeenCalled()
    expect(api.hospitals.list).not.toHaveBeenCalled()
    expect(api.hospitals.directory).toHaveBeenCalled()
  })

  it("still finds a patient session from before the kind was remembered", async () => {
    apiModule.__kind.value = ""
    await mount(<AuthProvider><span /></AuthProvider>)
    expect(api.auth.getMe).toHaveBeenCalled()
    expect(api.auth.patientMe).toHaveBeenCalled()
    expect(apiModule.__kind.value).toBe("patient")
  })
})

describe("start-up for a staff session", () => {
  it("asks the staff endpoint and the hospital list as before", async () => {
    apiModule.__kind.value = "staff"
    api.auth.getMe.mockResolvedValue({ user: { username: "desk" }, roles: ["Receptionist"] })
    api.hospitals.list.mockResolvedValue([{ id: 1, name: "Synthetic One" }])
    await mount(<AuthProvider><HospitalsProvider><span /></HospitalsProvider></AuthProvider>)

    expect(api.auth.getMe).toHaveBeenCalled()
    expect(api.auth.patientMe).not.toHaveBeenCalled()
    expect(api.hospitals.list).toHaveBeenCalled()
  })
})
