import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { describeAction, timeAgo } from "../utils/activityText.js"
import { withNodes } from "../utils/withNodes.jsx"

// Phase 5 Hindi gaps: times, audit actions and sentences around links go through t().
const hindi = { "just now": "अभी", "{count} min ago": "{count} मिनट पहले", Patient: "मरीज़", created: "बनाया गया" }
const t = (text, vars = {}) => (hindi[text] || text).replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m))

describe("activity text", () => {
  const now = Date.parse("2026-11-05T10:00:00Z")

  it("translates relative times", () => {
    expect(timeAgo("2026-11-05T09:59:50Z", t, now)).toBe("अभी")
    expect(timeAgo("2026-11-05T09:55:00Z", t, now)).toBe("5 मिनट पहले")
    expect(timeAgo("2026-11-05T07:00:00Z", undefined, now)).toBe("3 h ago")
  })

  it("names known audit actions in the reader's language and falls back to English words", () => {
    expect(describeAction("patients.patient.create", t)).toBe("मरीज़ बनाया गया")
    expect(describeAction("clinical.vitalsign.entered_in_error")).toBe("Vital signs removed (entered in error)")
    expect(describeAction("ipd.something_new.frobnicate")).toBe("Something new frobnicate")
  })

  it("keeps a link inside a translated sentence", () => {
    const html = renderToStaticMarkup(<p>{withNodes("सबकी भूमिकाएँ {link} पेज पर देखें।", { link: <a href="/u">Users</a> })}</p>)
    expect(html).toBe('<p>सबकी भूमिकाएँ <a href="/u">Users</a> पेज पर देखें।</p>')
  })
})
