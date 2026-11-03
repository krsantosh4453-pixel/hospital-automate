import { afterEach, describe, expect, it, vi } from "vitest"
import api from "../services/api.js"
import { hospitalToday } from "../utils/hospitalDate.js"

// The Queue page issues tokens from today's booked appointments, all pages of
// them, earliest first; it used to read only the first page, newest first.
const page = (results, next) => new Response(JSON.stringify({ results, next }), {
  status: 200, headers: { "Content-Type": "application/json" },
})

describe("today's appointments for the queue", () => {
  afterEach(() => vi.unstubAllGlobals())

  it("reads every page, filtered to the day and status", async () => {
    const urls = []
    vi.stubGlobal("fetch", vi.fn(async (url) => {
      urls.push(String(url))
      if (String(url).endsWith("/auth/csrf/")) return page([], null)
      return String(url).includes("page=1")
        ? page([{ id: 1, appointment_time: "10:30:00" }], "next")
        : page([{ id: 2, appointment_time: "09:00:00" }], null)
    }))

    const rows = await api.appointments.listForDay(4, "2026-11-03", { status: "Scheduled" })

    expect(rows.map((r) => r.id)).toEqual([2, 1])
    const calls = urls.filter((u) => u.includes("/appointments/"))
    expect(calls).toHaveLength(2)
    for (const url of calls) {
      expect(url).toContain("hospital=4")
      expect(url).toContain("appointment_date=2026-11-03")
      expect(url).toContain("status=Scheduled")
    }
  })

  it("counts the day in India, not UTC", () => {
    // 23:00 UTC on 2 Nov is 04:30 on 3 Nov in India.
    expect(hospitalToday(new Date("2026-11-02T23:00:00Z"))).toBe("2026-11-03")
  })
})
