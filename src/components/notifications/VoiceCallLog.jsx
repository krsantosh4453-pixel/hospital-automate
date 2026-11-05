import { useEffect, useState } from "react"
import { PhoneCall } from "lucide-react"
import api from "../../services/api.js"
import { Card, CardHeader, EmptyState, StatusBadge, TableWrap } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

const formatTime = (value) => (value ? new Date(value).toLocaleString("en-IN") : "—")

/**
 * Voice calls queued after SMS/WhatsApp delivery failed, for front-desk and
 * admin follow-up. "Skipped" usually means voice calls are not configured or
 * the patient has not consented to them.
 */
export default function VoiceCallLog({ hospitalId }) {
  const { t } = useLanguage()
  const [rows, setRows] = useState([])
  const [state, setState] = useState("loading")

  useEffect(() => {
    if (!hospitalId) return undefined
    let cancelled = false
    setState("loading")
    api.notifications.voiceCalls
      .list(hospitalId)
      .then((data) => {
        if (cancelled) return
        setRows(Array.isArray(data) ? data : data?.results || [])
        setState("ready")
      })
      .catch((err) => !cancelled && setState(err?.status === 403 ? "forbidden" : "error"))
    return () => {
      cancelled = true
    }
  }, [hospitalId])

  return (
    <Card>
      <CardHeader
        icon={PhoneCall}
        title="Voice call fallback"
        description="Automated calls queued when a text message could not be delivered."
      />
      {state === "loading" ? (
        <p className="px-5 py-6 text-sm text-ink-500">Loading…</p>
      ) : state === "forbidden" ? (
        <EmptyState compact icon={PhoneCall} title="Not available for your role" />
      ) : state === "error" ? (
        <EmptyState compact icon={PhoneCall} title="Could not load voice calls" />
      ) : rows.length === 0 ? (
        <EmptyState compact icon={PhoneCall} title="No voice calls queued" />
      ) : (
        <TableWrap maxHeight="22rem">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-ink-500">
              <tr>
                <th className="px-5 py-2 font-medium">{t("Patient")}</th>
                <th className="px-3 py-2 font-medium">{t("Why")}</th>
                <th className="px-3 py-2 font-medium">{t("Status")}</th>
                <th className="px-5 py-2 font-medium">{t("Queued")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {rows.slice(0, 25).map((row) => (
                <tr key={row.id}>
                  <td className="px-5 py-2 text-ink-900">{row.patient_name}</td>
                  <td className="px-3 py-2 text-ink-600">{row.reason || row.event}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={row.status} />
                    {row.error && <p className="mt-0.5 text-xs text-ink-500">{row.error}</p>}
                  </td>
                  <td className="px-5 py-2 text-ink-600">{formatTime(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}
    </Card>
  )
}
