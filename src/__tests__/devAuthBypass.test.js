import { describe, expect, it } from "vitest"
import { isDevelopmentAuthBypassEnabled } from "../utils/devAuthBypass.js"

// R-14: the fake-Admin bypass is opt-in and impossible in a production build.
describe("development auth bypass", () => {
  it("is off in development unless explicitly enabled", () => {
    expect(isDevelopmentAuthBypassEnabled({ DEV: true, PROD: false })).toBe(false)
    expect(isDevelopmentAuthBypassEnabled({ DEV: true, PROD: false, VITE_DEV_AUTH_BYPASS: "" })).toBe(false)
    expect(isDevelopmentAuthBypassEnabled({ DEV: true, PROD: false, VITE_DEV_AUTH_BYPASS: "false" })).toBe(false)
    expect(isDevelopmentAuthBypassEnabled({ DEV: true, PROD: false, VITE_DEV_AUTH_BYPASS: "1" })).toBe(false)
  })

  it("turns on in development when set to true", () => {
    expect(isDevelopmentAuthBypassEnabled({ DEV: true, PROD: false, VITE_DEV_AUTH_BYPASS: "true" })).toBe(true)
    expect(isDevelopmentAuthBypassEnabled({ DEV: true, PROD: false, VITE_DEV_AUTH_BYPASS: " TRUE " })).toBe(true)
  })

  it("can never turn on in a production build", () => {
    expect(isDevelopmentAuthBypassEnabled({ DEV: false, PROD: true, VITE_DEV_AUTH_BYPASS: "true" })).toBe(false)
  })
})
