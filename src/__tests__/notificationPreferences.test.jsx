import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// K7: the patient's contact choices are consent rows; the newest one wins.
vi.mock("../services/api.js", () => ({
  default: { notifications: { consent: { list: vi.fn(), grant: vi.fn(), revoke: vi.fn() } } },
}))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import NotificationPreferences from "../components/notifications/NotificationPreferences.jsx"
import { currentChoices } from "../utils/notificationChoices.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe("notification choices", () => {
  it("takes the newest answer per channel and ignores other purposes", () => {
    expect(currentChoices([
      { purpose: "notifications_sms", granted: false },
      { purpose: "notifications_sms", granted: true },
      { purpose: "notifications_voice", granted: true },
      { purpose: "research", granted: true },
    ])).toEqual({ sms: false, voice: true })
  })

  describe("card", () => {
    let host
    let root
    beforeEach(() => {
      vi.clearAllMocks()
      api.notifications.consent.list.mockResolvedValue([{ purpose: "notifications_sms", granted: true }])
      api.notifications.consent.grant.mockResolvedValue({})
      api.notifications.consent.revoke.mockResolvedValue({})
    })
    afterEach(() => {
      act(() => root.unmount())
      host.remove()
    })

    it("shows current choices and records a change as a new consent", async () => {
      host = document.createElement("div")
      document.body.appendChild(host)
      root = createRoot(host)
      act(() => root.render(<LanguageProvider><NotificationPreferences hospitalId={4} /></LanguageProvider>))
      await act(() => new Promise((resolve) => setTimeout(resolve, 0)))
      const boxes = [...host.querySelectorAll('input[type="checkbox"]')]
      expect(boxes.map((b) => b.checked)).toEqual([true, false, false, false])
      await act(async () => boxes[0].click())
      expect(api.notifications.consent.revoke).toHaveBeenCalledWith(4, null, "notifications_sms")
      await act(async () => boxes[1].click())
      expect(api.notifications.consent.grant).toHaveBeenCalledWith(4, null, "notifications_whatsapp")
    })
  })
})
