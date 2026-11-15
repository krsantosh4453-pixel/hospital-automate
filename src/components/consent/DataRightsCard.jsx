import { useCallback, useEffect, useState } from "react"
import { ShieldCheck } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Alert, Button, Card, CardHeader, Field, Select, Textarea } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

const STATUS_LABELS = { received: "Received", in_progress: "In progress", completed: "Completed", refused: "Refused" }
const shortDate = (value) => (value ? new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "")

/**
 * P1-03 (DPDP Act 2023): the patient's privacy notice and data requests at one
 * hospital: who answers, how long it may take, a request form and past answers.
 *
 * @param {{ hospitalId: number|string }} props
 */
export default function DataRightsCard({ hospitalId }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [notice, setNotice] = useState(null)
  const [requests, setRequests] = useState([])
  const [form, setForm] = useState({ kind: "access", details: "" })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    try {
      const [noticeData, listData] = await Promise.all([api.consent.rights.notice(hospitalId), api.consent.rights.list()])
      setNotice(noticeData)
      setRequests((listData?.results || []).filter((row) => String(row.hospital ?? hospitalId) === String(hospitalId)))
      setError("")
    } catch (err) {
      setError(err.message || "Your data requests could not be loaded.")
    }
  }, [hospitalId])

  useEffect(() => {
    if (hospitalId) load()
  }, [hospitalId, load])

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const created = await api.consent.rights.create({ hospital: hospitalId, kind: form.kind, details: form.details.trim() })
      setRequests((current) => [created, ...current])
      setForm({ kind: form.kind, details: "" })
      toast.success(t("Request sent. The hospital will answer by {date}.", { date: shortDate(created.due_at) }))
    } catch (err) {
      setError(err.message || "The request was not sent.")
    } finally {
      setSaving(false)
    }
  }

  const officer = notice?.grievance_officer || {}
  return (
    <Card className="mt-6">
      <CardHeader icon={ShieldCheck} title="Your data rights"
        description="Ask for a summary of your data, a correction or erasure, or raise a complaint." />
      <div className="space-y-4 px-5 pb-5 text-sm">
        {error && <Alert tone="danger">{error}</Alert>}
        {notice && (
          <p className="text-ink-700">
            {officer.name
              ? t("Grievance officer: {name}", { name: officer.name })
              : t("This hospital has not named a grievance officer yet; ask at the front desk.")}
            {officer.email ? ` · ${officer.email}` : ""}{officer.phone ? ` · ${officer.phone}` : ""}
            <span className="block text-ink-500">{t("Answers within {days} days.", { days: notice.response_days })}</span>
          </p>
        )}
        <form onSubmit={submit} className="space-y-3">
          <Field label="What you are asking for" required>
            <Select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              {(notice?.kinds || []).map((kind) => <option key={kind.value} value={kind.value}>{kind.label}</option>)}
            </Select>
          </Field>
          <Field label="Details" hint="What should change, or what the complaint is about.">
            <Textarea rows={3} maxLength={2000} value={form.details}
              onChange={(e) => setForm({ ...form, details: e.target.value })} />
          </Field>
          <Button type="submit" loading={saving} disabled={!notice}>{t("Send request")}</Button>
        </form>
        {requests.length > 0 && (
          <ul className="divide-y divide-line rounded-lg border border-line">
            {requests.map((row) => (
              <li key={row.id} className="px-3 py-2">
                <span className="font-medium text-ink-900">{row.kind_label}</span>
                <span className="ml-2 text-xs text-ink-500">
                  {t(STATUS_LABELS[row.status] || row.status)} · {shortDate(row.created_at)}
                  {row.overdue ? ` · ${t("Overdue")}` : ""}
                </span>
                {row.response && <span className="block text-ink-700">{row.response}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}
