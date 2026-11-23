import { useCallback, useEffect, useState } from "react"
import { AlertTriangle } from "lucide-react"
import api from "../../services/api.js"
import { Badge, Button, Card } from "../ui"
import { useToast } from "../Toast.jsx"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// H-14: verified results with a critical value that no doctor has
// acknowledged yet. A doctor records what was done; the server audits it.

const rowsOf = (data) => (Array.isArray(data) ? data : data?.results || [])

const criticalParameters =(labResult) =>
  (labResult?.flag_details || []).filter((d) => d.flag === "LL" || d.flag === "HH")

export default function CriticalResults({ hospitalId, canAcknowledge, promptText, onChange }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [rows, setRows] = useState([])
  const [error, setError] = useState("")
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    if (!hospitalId) return
    try {
      setRows(rowsOf(await api.laboratory.tests.criticalResults(hospitalId)))
      setError("")
    } catch (err) {
      setError(err.message)
    }
  }, [hospitalId])

  useEffect(() => {
    load()
  }, [load])

  const acknowledge = async (test) => {
    const note = await promptText(t("What was done about this critical value?"))
    if (!note || !note.trim()) return
    setBusyId(test.id)
    try {
      await api.laboratory.tests.acknowledgeCritical(test.id, note.trim())
      toast.success(t("Critical value acknowledged."))
      await load()
      onChange?.()
    } catch (err) {
      toast.error(t("Not acknowledged: {reason}", { reason: err.message }))
    } finally {
      setBusyId(null)
    }
  }

  if (error) {
    return (
      <Card className="border-red-200 p-4 text-sm text-red-700" role="alert">
        {t("Critical results could not be loaded: {reason}", { reason: error })}
      </Card>
    )
  }
  if (rows.length === 0) return null

  return (
    <Card className="border-red-300 p-4" role="region" aria-label={t("Critical results awaiting a doctor")}>
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-red-700">
        <AlertTriangle size={16} aria-hidden="true" />
        {t("Critical results awaiting a doctor")} ({rows.length})
      </h2>
      <ul className="divide-y divide-ink-100">
        {rows.map((test) => (
          <li key={test.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <div className="min-w-0">
              <p className="text-sm font-medium text-ink-900">
                {test.patient_name} · {test.name}
              </p>
              <p className="mt-1 flex flex-wrap gap-1">
                {criticalParameters(test.lab_result).map((d) => (
                  <Badge key={d.parameter} tone="danger">
                    {d.parameter} {d.value} {d.unit} ({d.flag})
                  </Badge>
                ))}
              </p>
              {test.doctor_name && <p className="mt-1 text-xs text-ink-500">{t("Ordered by")} {test.doctor_name}</p>}
            </div>
            {canAcknowledge && (
              <Button size="sm" variant="danger" loading={busyId === test.id} onClick={() => acknowledge(test)}>
                {t("Acknowledge")}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </Card>
  )
}
