import { useEffect, useState } from "react"
import { Printer } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, Card, CardHeader, EmptyState, Field, Input, TableWrap } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// Today in the hospital's time zone (India), as YYYY-MM-DD.
const hospitalToday = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date())

/**
 * P1-10: the Schedule H1 register (Drugs and Cosmetics Rules, Rule 65(9)),
 * with Schedule X and NDPS sales: prescriber and registration, patient, drug,
 * batch and quantity of every sale. The server builds it from the sales.
 *
 * @param {{ hospitalId: number|string }} props
 */
export default function H1Register({ hospitalId }) {
  const { t } = useLanguage()
  const today = hospitalToday()
  const [range, setRange] = useState({ from: `${today.slice(0, 8)}01`, to: today })
  const [rows, setRows] = useState([])
  const [state, setState] = useState("loading") // loading | ready | error
  const [error, setError] = useState("")

  useEffect(() => {
    if (!hospitalId) return undefined
    let stale = false
    setState("loading")
    api.pharmacy.sales.h1Register(hospitalId, range)
      .then((data) => {
        if (stale) return
        setRows(data?.results || [])
        setState("ready")
      })
      .catch((err) => {
        if (stale) return
        setError(err.message || "The register could not be loaded.")
        setState("error")
      })
    return () => {
      stale = true
    }
  }, [hospitalId, range])

  const setDate = (name) => (event) => setRange((current) => ({ ...current, [name]: event.target.value }))

  return (
    <Card className="mt-6">
      <CardHeader
        title="Schedule H1 register"
        description="Schedule H1, X and NDPS sales with prescriber, patient, batch and quantity. Keep for three years."
        actions={<Button size="sm" variant="secondary" icon={Printer} onClick={() => window.print()}>{t("Print")}</Button>}
      />
      <div className="flex flex-wrap gap-4 px-5 pb-4">
        <Field label="From">
          <Input type="date" name="from" value={range.from} max={range.to} onChange={setDate("from")} />
        </Field>
        <Field label="To">
          <Input type="date" name="to" value={range.to} min={range.from} onChange={setDate("to")} />
        </Field>
      </div>
      {state === "error" && <Alert tone="danger" className="mx-5 mb-4">{error}</Alert>}
      {state === "loading" && <p className="px-5 pb-5 text-sm text-ink-500">{t("Loading…")}</p>}
      {state === "ready" && rows.length === 0 && (
        <EmptyState compact title={t("No scheduled sales in these dates")} />
      )}
      {state === "ready" && rows.length > 0 && (
        <TableWrap>
          <table className="hms-table">
            <thead>
              <tr>
                <th>{t("Date")}</th>
                <th>{t("Patient")}</th>
                <th>{t("Prescriber")}</th>
                <th>{t("Medicine")}</th>
                <th>{t("Batch")}</th>
                <th className="text-right">{t("Qty")}</th>
                <th>{t("Sale")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.sale}>
                  <td className="tabular-nums">{row.date}</td>
                  <td>{row.patient}{row.patient_uhid ? <span className="block text-xs text-ink-500">{row.patient_uhid}</span> : null}</td>
                  <td>{row.prescriber}{row.prescriber_registration
                    ? <span className="block text-xs text-ink-500">{row.prescriber_registration}</span> : null}</td>
                  <td>{row.medicine} <span className="text-xs text-ink-500">({row.schedule})</span></td>
                  <td>{row.batch}</td>
                  <td className="text-right tabular-nums">{row.quantity}</td>
                  <td className="tabular-nums">{row.sale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}
    </Card>
  )
}
