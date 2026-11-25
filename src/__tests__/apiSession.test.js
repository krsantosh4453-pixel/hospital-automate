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

const textResponse = (status, text = "") => new Response(text, { status, headers: { "Content-Type": "text/plain" } })
const REGISTRATION = { role: "Patient", full_name: "Synthetic Person", phone: "9000000001", email: "s@example.test" }

describe("api error kinds", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // A fresh module has no cached CSRF token, so the first write fetches one.
  const freshApi = async () => {
    vi.resetModules()
    return (await import("../services/api.js")).default
  }

  it("reports the backend as unavailable when the proxy answers 502 for the CSRF token", async () => {
    // The Vite dev proxy answers 502 when nothing listens on the Django port.
    const fetchMock = vi.fn(async () => textResponse(502))
    vi.stubGlobal("fetch", fetchMock)

    const error = await (await freshApi()).auth.register(REGISTRATION).catch((e) => e)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/auth\/csrf\/$/)

    expect(error.isNetworkError).toBe(true)
    expect(error.isBackendUnavailable).toBe(true)
    expect(error.status).toBe(502)
    expect(error.message).toMatch(/server is unavailable/i)
  })

  it("does not call a server error while fetching the CSRF token 'cannot reach the server'", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url) =>
      String(url).endsWith("/auth/csrf/") ? textResponse(500, "<html>Traceback</html>") : jsonResponse(201, {}),
    ))

    const error = await (await freshApi()).auth.register(REGISTRATION).catch((e) => e)

    expect(error.isNetworkError).toBeFalsy()
    expect(error.status).toBe(500)
    expect(error.message).not.toMatch(/cannot reach/i)
    expect(error.message).toMatch(/internal error/i)
  })

  it("says 'cannot reach the server' only when no HTTP response arrives", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch")
    }))

    const error = await api.auth.register(REGISTRATION).catch((e) => e)

    expect(error.isNetworkError).toBe(true)
    expect(error.status).toBeUndefined()
    expect(error.message).toMatch(/cannot reach the server/i)
  })

  it("explains an HTML 500 page as an internal server error", async () => {
    stubServer(async () => textResponse(500, "<html>Traceback</html>"))

    const error = await api.auth.register(REGISTRATION).catch((e) => e)

    expect(error.isNetworkError).toBeFalsy()
    expect(error.status).toBe(500)
    expect(error.message).toMatch(/internal error/i)
    expect(error.message).not.toMatch(/Traceback/)
  })

  it("flags an HTML answer to the CSRF request as a routing problem, not a down server", async () => {
    // What a wrong VITE_API_BASE_URL looks like: the SPA's index.html comes back.
    vi.stubGlobal("fetch", vi.fn(async () =>
      new Response("<!doctype html><div id=root>", { status: 200, headers: { "Content-Type": "text/html" } }),
    ))

    const error = await (await freshApi()).auth.register(REGISTRATION).catch((e) => e)

    expect(error.isMisrouted).toBe(true)
    expect(error.isNetworkError).toBeFalsy()
    expect(error.message).toMatch(/unexpected format/i)
  })

  it.each([
    [404, /not found on the server \(HTTP 404\)/i],
    [401, /sign in again \(HTTP 401\)/i],
    [403, /not allowed \(HTTP 403\)/i],
  ])("explains a bare HTTP %i without calling it a network failure", async (status, pattern) => {
    stubServer(async () => textResponse(status, "<html>Page not found</html>"))

    const error = await api.auth.register(REGISTRATION).catch((e) => e)

    expect(error.status).toBe(status)
    expect(error.isNetworkError).toBeFalsy()
    expect(error.message).toMatch(pattern)
  })

  it("keeps the server's own text for a 409 conflict", async () => {
    stubServer(async () => jsonResponse(409, { error: "This booking conflicts with another one." }))

    const error = await api.auth.register(REGISTRATION).catch((e) => e)

    expect(error.status).toBe(409)
    expect(error.message).toBe("This booking conflicts with another one.")
  })

  it("shows the rate limiter's message without its error code", async () => {
    stubServer(async () => jsonResponse(429, {
      error: { code: "RATE_LIMITED", message: "Rate limit exceeded. Maximum 5 requests per 300 seconds.", retry_after: 300 },
    }))

    const error = await api.auth.register(REGISTRATION).catch((e) => e)

    expect(error.status).toBe(429)
    expect(error.message).toBe("Rate limit exceeded. Maximum 5 requests per 300 seconds.")
  })

  it("passes the server's validation message through for a 400", async () => {
    stubServer(async () => jsonResponse(400, { error: "Password and confirm password do not match." }))

    const error = await api.auth.register(REGISTRATION).catch((e) => e)

    expect(error.isNetworkError).toBeFalsy()
    expect(error.status).toBe(400)
    expect(error.message).toBe("Password and confirm password do not match.")
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

// Prompt 5 (SEC-001): no staff profile in browser storage on a shared PC,
// and nothing of one person's session left for the next.
describe("browser storage on shared computers", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  const PROFILE = {
    user: { username: "synthetic.desk", email: "desk@example.test", phone: "9000000000", employee_id: "EMP-1" },
    roles: ["Receptionist"],
    hospitals: [{ id: 1, name: "Synthetic One" }],
  }

  it("keeps the staff profile out of localStorage after sign-in (TEST 16)", async () => {
    stubServer(async () => jsonResponse(200, PROFILE))

    await api.auth.staffLogin("synthetic.desk", "Synthetic-Pass-123")

    expect(localStorage.getItem("user")).toBeNull()
    expect(localStorage.getItem("roles")).toBeNull()
    expect(localStorage.getItem("hospitals")).toBeNull()
    const stored = Object.keys(localStorage).map((key) => localStorage.getItem(key)).join(" ")
    expect(stored).not.toContain("desk@example.test")
    expect(stored).not.toContain("EMP-1")
  })

  it("forgets the previous person's hospital when someone else signs in (TEST 16)", async () => {
    localStorage.setItem("selectedHospital", JSON.stringify({ id: 9, name: "Previous user's hospital" }))
    stubServer(async () => jsonResponse(200, PROFILE))

    await api.auth.staffLogin("synthetic.desk", "Synthetic-Pass-123")

    expect(localStorage.getItem("selectedHospital")).toBeNull()
  })

  it("keeps the chosen hospital when the same person signs in again", async () => {
    localStorage.setItem("selectedHospital", JSON.stringify({ id: 1, name: "Synthetic One" }))
    stubServer(async () => jsonResponse(200, PROFILE))

    await api.auth.staffLogin("synthetic.desk", "Synthetic-Pass-123")

    expect(JSON.parse(localStorage.getItem("selectedHospital")).id).toBe(1)
  })

  it("clears every user-specific key on logout (TEST 16)", async () => {
    for (const key of ["user", "roles", "hospitals", "selectedHospital", "patient", "patientLoggedIn", "hospitalPatients"]) {
      localStorage.setItem(key, "left by an earlier session")
    }
    stubServer(async () => jsonResponse(200))

    await api.auth.logout()

    for (const key of ["user", "roles", "hospitals", "selectedHospital", "patient", "patientLoggedIn", "hospitalPatients"]) {
      expect(localStorage.getItem(key)).toBeNull()
    }
  })
})

describe("error messages from field-error bodies", () => {
  it("shows the server's sentences instead of raw JSON", async () => {
    const { parseErrorDetail } = await import("../services/api.js")
    const body = {
      first_dose: ["This hospital has no medication rounds configured. Choose Start now or a specific time."],
      first_dose_required: true,
    }
    expect(parseErrorDetail(body, 400)).toBe(
      "This hospital has no medication rounds configured. Choose Start now or a specific time.",
    )
    expect(parseErrorDetail({ message: "Wrapped message" }, 400)).toBe("Wrapped message")
    expect(parseErrorDetail({ details: { a: ["One"], b: { c: "Two" } } }, 400)).toBe("One Two")
    expect(parseErrorDetail({ ok: false }, 409)).toBe("Request failed (409)")
  })
})
