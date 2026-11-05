import { useCallback, useEffect, useRef, useState } from "react"
import { BellRing } from "lucide-react"
import api from "../../services/api.js"
import { currentChoices } from "../../utils/notificationChoices.js"
import { Alert, Card, CardHeader } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// K7: a patient chooses how this hospital may contact them. Each change is a
// consent row (notifications_<channel>); the newest answer is the one the
// notification engine honours. In-app notices are always shown.

const CHANNELS = [
  { id: "sms", label: "Text message (SMS)" },
  { id: "whatsapp", label: "WhatsApp" },
  { id: "voice", label: "Automated voice call" },
  { id: "email", label: "Email" },
]
const list = (data) => (Array.isArray(data) ? data : data?.results || [])

export default function NotificationPreferences({ hospitalId }) {
  const { t } = useLanguage()
  const [choices, setChoices] = useState({})
  // Choices cannot be changed until the saved ones have loaded, so a late
  // load never overwrites a change the patient just made.
  const [loaded, setLoaded] = useState(false)
  // Bumped on every change, so a load that started earlier cannot undo it.
  const version = useRef(0)
  const [saving, setSaving] = useState("")
  const [error, setError] = useState("")

  const load = useCallback(() => {
    if (!hospitalId) return undefined
    let cancelled = false
    const started = version.current
    setLoaded(false)
    api.notifications.consent.list(hospitalId)
      .then((data) => {
        if (cancelled) return
        if (version.current === started) setChoices(currentChoices(list(data)))
        setLoaded(true)
      })
      .catch((err) => !cancelled && setError(err.message || "Could not load your contact choices."))
    return () => {
      cancelled = true
    }
  }, [hospitalId])
  useEffect(() => load(), [load])

  const toggle = async (channel, allow) => {
    setSaving(channel)
    setError("")
    // Shown at once; put back if the server does not record it.
    version.current += 1
    setChoices((prev) => ({ ...prev, [channel]: allow }))
    try {
      const purpose = `notifications_${channel}`
      await (allow ? api.notifications.consent.grant : api.notifications.consent.revoke)(hospitalId, null, purpose)
    } catch (err) {
      setChoices((prev) => ({ ...prev, [channel]: !allow }))
      setError(err.message || "Could not save your choice.")
    } finally {
      setSaving("")
    }
  }

  return (
    <Card>
      <CardHeader icon={BellRing} title="How we may contact you"
        description="Reminders and updates from this hospital. You can change this at any time." />
      <div className="space-y-3 px-5 py-4">
        {error && <Alert tone="danger">{error}</Alert>}
        {CHANNELS.map((channel) => (
          <label key={channel.id} className="flex items-center justify-between gap-3 text-sm">
            <span className="text-ink-800">{t(channel.label)}</span>
            <input type="checkbox" checked={Boolean(choices[channel.id])} disabled={!loaded || saving === channel.id}
              onChange={(e) => toggle(channel.id, e.target.checked)} aria-label={t(channel.label)} />
          </label>
        ))}
        <p className="text-xs text-ink-500">{t("Messages inside this portal are always shown. Text, WhatsApp and calls are sent only once the hospital has them set up.")}</p>
      </div>
    </Card>
  )
}
