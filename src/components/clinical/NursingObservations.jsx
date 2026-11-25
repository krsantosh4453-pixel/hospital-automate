import { useEffect, useState } from "react"
import { ClipboardList } from "lucide-react"
import api from "../../services/api.js"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { Alert, Card, CardHeader, EmptyState, SkeletonRows } from "../ui"
import { formatTemperature } from "../../utils/temperature.js"

// Prompt 4 (INT-001): vitals the ward nurses record are nursing assessments
// (GET /api/nurses/assessments/?patient=), not visit vitals, so the doctor's
// Vitals tab never showed them. They are read here as they are, with who took
// them and when: nothing is copied, so nothing can be duplicated. The server
// decides who may see them (doctors and nurses of this hospital, patients in
// their care).

const readRows = (data) => (Array.isArray(data) ? data : data?.results || [])
const hasVitals = (row) => row?.vitals && Object.values(row.vitals).some((v) => v !== null && String(v).trim() !== "")
const when = (iso) =>
  iso ? new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"
const dash = (value) => (value === null || value === undefined || String(value).trim() === "" ? "—" : value)

export default function NursingObservations({ patientId }) {
  const { t } = useLanguage()
  const [rows, setRows] = useState(null)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!patientId) return undefined
    let cancelled = false
    setRows(null)
    setError("")
    api.nurses.assessments
      .list(undefined, patientId)
      .then((data) => !cancelled && setRows(readRows(data).filter(hasVitals)))
      .catch((err) => !cancelled && setError(err.message || ""))
    return () => {
      cancelled = true
    }
  }, [patientId])

  return (
    <Card>
      <CardHeader icon={ClipboardList} title={t("Nursing observations")} description="Vitals recorded by the ward nurses for this patient." />
      {error ? (
        <Alert tone="warning" className="mx-5 mb-4">{t("Nursing observations could not be loaded.")} {error}</Alert>
      ) : rows === null ? (
        <SkeletonRows rows={2} />
      ) : rows.length === 0 ? (
        <EmptyState compact icon={ClipboardList} title={t("No nursing observations for this patient")} />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-500">
                <th className="px-5 py-2">{t("Time")}</th>
                <th className="px-5 py-2">{t("Recorded by")}</th>
                <th className="px-5 py-2">{t("Temperature")}</th>
                <th className="px-5 py-2">{t("BP")}</th>
                <th className="px-5 py-2">{t("Pulse")}</th>
                <th className="px-5 py-2">{t("SpO₂")}</th>
                <th className="px-5 py-2">{t("Resp. rate")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-line">
                  <td className="px-5 py-2 tabular-nums">{when(row.assessed_at)}</td>
                  <td className="px-5 py-2">{dash(row.nurse_name)}</td>
                  <td className="px-5 py-2 tabular-nums">{formatTemperature(row.vitals.temperature, row.vitals.temperature_unit)}</td>
                  <td className="px-5 py-2 tabular-nums">{dash(row.vitals.bp)}</td>
                  <td className="px-5 py-2 tabular-nums">{dash(row.vitals.pulse)}</td>
                  <td className="px-5 py-2 tabular-nums">{row.vitals.spo2 ? `${row.vitals.spo2}%` : "—"}</td>
                  <td className="px-5 py-2 tabular-nums">{dash(row.vitals.respiratory_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
