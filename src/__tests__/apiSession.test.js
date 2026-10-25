import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import api, { CACHED_PATIENT_DATA_KEYS } from "../services/api.js"

const jsonResponse = (status, body = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })

// Answers /auth/csrf/ with a token and everything else with `handler`.
const stubServer = (handler) => {
  const fetchMock = vi.fn(async (url, init) =>
    String(url).endsWith("/auth/csrf/") ? jsonResponse(200, { csrfToken: "csrf-1" }) : handler(url, init),
  )
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}

const callsTo = (fetchMock, path) => fetchMock.mock.calls.filter(([url]) => String(url).includes(path))

describe("api session handling", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("clears cached patient data and signals logout when the session cannot be refreshed", async () => {
    localStorage.setItem("hms_session", "1")
    for (const key of CACHED_PATIENT_DATA_KEYS) localStorage.setItem(key, '[{"name":"Synthetic"}]')
    stubServer(async () => jsonResponse(401, { detail: "expired" }))
    const loggedOut = vi.fn()
    window.addEventListener("auth:logout", loggedOut)

    await expect(api.appointments.list(1)).rejects.toThrow("Session expired")

    for (const key of CACHED_PATIENT_DATA_KEYS) expect(localStorage.getItem(key)).toBeNull()
    expect(localStorage.getItem("hms_session")).toBeNull()
    expect(loggedOut).toHaveBeenCalledTimes(1)
    window.removeEventListener("auth:logout", loggedOut)
  })

  it("logout clears cached patient data", async () => {
    for (const key of CACHED_PATIENT_DATA_KEYS) localStorage.setItem(key, "[]")
    stubServer(async () => jsonResponse(200))

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

describe("cookie session", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("never stores tokens in localStorage, even when the server sends them", async () => {
    stubServer(async () => jsonResponse(200, { access: "secret-access", refresh: "secret-refresh", user: {} }))

    await api.auth.staffLogin("synthetic", "Synthetic-Pass-123")

    const stored = Object.keys(localStorage).map((key) => localStorage.getItem(key)).join(" ")
    expect(stored).not.toContain("secret-access")
    expect(stored).not.toContain("secret-refresh")
    expect(localStorage.getItem("hms_session")).toBe("1")
  })

  it("sends writes with cookies, the cookie mode header and a CSRF token, and no bearer header", async () => {
    const fetchMock = stubServer(async () => jsonResponse(201, { id: 1 }))

    await api.appointments.create({ patient: 1 })

    const [, init] = callsTo(fetchMock, "/appointments/")[0]
    expect(init.credentials).toBe("include")
    expect(init.headers["X-Auth-Mode"]).toBe("cookie")
    expect(init.headers["X-CSRFToken"]).toBe("csrf-1")
    expect(init.headers.Authorization).toBeUndefined()
  })

  it("renews a stale CSRF token once and retries the write", async () => {
    let attempts = 0
    const fetchMock = stubServer(async () => {
      attempts += 1
      return attempts === 1
        ? jsonResponse(403, { detail: "CSRF Failed: CSRF token incorrect." })
        : jsonResponse(201, { id: 2 })
    })

    await expect(api.appointments.create({ patient: 1 })).resolves.toEqual({ id: 2 })
    expect(callsTo(fetchMock, "/appointments/")).toHaveLength(2)
  })

  it("removes tokens left in localStorage by earlier builds on logout", async () => {
    localStorage.setItem("access_token", "old")
    localStorage.setItem("refresh_token", "old")
    stubServer(async () => jsonResponse(200))

    await api.auth.logout()

    expect(localStorage.getItem("access_token")).toBeNull()
    expect(localStorage.getItem("refresh_token")).toBeNull()
  })
})
