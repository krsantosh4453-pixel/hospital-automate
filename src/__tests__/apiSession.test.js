import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import api, { CACHED_PATIENT_DATA_KEYS } from "../services/api.js"

const jsonResponse = (status, body = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })

describe("api session handling", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("clears cached patient data and signals logout when the session cannot be refreshed", async () => {
    localStorage.setItem("access_token", "expired")
    localStorage.setItem("refresh_token", "also-expired")
    for (const key of CACHED_PATIENT_DATA_KEYS) localStorage.setItem(key, '[{"name":"Synthetic"}]')
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(401, { detail: "expired" })))
    const loggedOut = vi.fn()
    window.addEventListener("auth:logout", loggedOut)

    await expect(api.appointments.list(1)).rejects.toThrow("Session expired")

    for (const key of CACHED_PATIENT_DATA_KEYS) expect(localStorage.getItem(key)).toBeNull()
    expect(localStorage.getItem("access_token")).toBeNull()
    expect(loggedOut).toHaveBeenCalledTimes(1)
    window.removeEventListener("auth:logout", loggedOut)
  })

  it("logout clears cached patient data", async () => {
    for (const key of CACHED_PATIENT_DATA_KEYS) localStorage.setItem(key, "[]")
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200)))

    await api.auth.logout()

    for (const key of CACHED_PATIENT_DATA_KEYS) expect(localStorage.getItem(key)).toBeNull()
  })

  it("marks a timeout separately from an unreachable server", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new DOMException("timed out", "TimeoutError")
    }))
    const timeout = await api.appointments.list(1).catch((error) => error)
    expect(timeout.isNetworkError).toBe(true)
    expect(timeout.isTimeout).toBe(true)

    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch")
    }))
    const offline = await api.appointments.list(1).catch((error) => error)
    expect(offline.isNetworkError).toBe(true)
    expect(offline.isTimeout).toBe(false)
  })
})
