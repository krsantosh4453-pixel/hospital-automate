import { useEffect, useState } from "react"
import { BedDouble } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, Card, CardHeader, Field, Input } from "../ui"

// Final bills of inpatient stays being discharged (E12, H8). The server
// counts the bed days and allows one live final bill per stay; payment is
// then taken on the invoice like any other.

const emptyForm = { dailyRate: "", otherDescription: "", otherAmount: "" }

export default function DischargeBills({ hospitalId, refreshKey, onCreated }) {
  const [rows, setRows] = useState([])
  const [error, setError] = useState("")
  const [forms, setForms] = useState({})
  const [saving, setSaving] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    if (!hospitalId) return undefined
    let cancelled = false
    api.ipd.admissions
      .awaitingFinalBill(hospitalId)
      .then((data) => !cancelled && setRows(Array.isArray(data) ? data : []))
      .catch((err) => !cancelled && setError(err.message || "Could not load discharges awaiting a bill."))
    return () => {
      cancelled = true
    }
  }, [hospitalId, reloadToken, refreshKey])

  const formFor = (id) => forms[id] || emptyForm
  const setField = (id, field) => (event) =>
    setForms((prev) => ({ ...prev, [id]: { ...formFor(id), [field]: event.target.value } }))

  const create = async (event, row) => {
    event.preventDefault()
    const form = formFor(row.admission)
    const items = form.otherDescription.trim()
      ? [{ description: form.otherDescription.trim(), quantity: 1, unit_price: form.otherAmount || "0" }]
      : []
    setSaving(row.admission)
    setError("")
    try {
      await api.ipd.admissions.finalBill(row.admission, { daily_rate: form.dailyRate, items })
      setForms((prev) => ({ ...prev, [row.admission]: emptyForm }))
      setReloadToken((n) => n + 1)
      onCreated?.()
    } catch (err) {
      setError(err.message || "Could not create the final bill.")
    } finally {
      setSaving(null)
    }
  }

  if (!hospitalId || (rows.length === 0 && !error)) return null

  return (
    <Card className="mb-6">
      <CardHeader
        icon={BedDouble}
        title="Discharge bills"
        description="Inpatients being discharged. Their discharge completes only after the final bill is paid."
      />
      {error && <Alert tone="danger" className="m-4">{error}</Alert>}
      <ul className="divide-y divide-line">
        {rows.map((row) => {
          const bill = row.final_invoice
          const form = formFor(row.admission)
          return (
            <li key={row.admission} className="px-5 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-medium text-ink-900">{row.patient_name}</p>
                <p className="text-[13px] text-ink-500">
                  Admitted {new Date(row.admission_date).toLocaleDateString("en-IN")} · {row.days} day(s)
                </p>
              </div>
              {bill ? (
                <p className={`mt-1 text-sm ${Number(bill.balance_due) > 0 ? "text-amber-700" : "text-green-700"}`}>
                  Final bill {bill.invoice_number}: ₹{bill.total}
                  {Number(bill.balance_due) > 0 ? `, ₹${bill.balance_due} due. Take the payment on the invoice below.` : ", paid."}
                </p>
              ) : (
                <form onSubmit={(event) => create(event, row)} className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4 sm:items-end">
                  <Field label="Bed charge per day (₹)" required>
                    <Input type="number" min="0" step="0.01" inputMode="decimal" value={form.dailyRate} onChange={setField(row.admission, "dailyRate")} />
                  </Field>
                  <Field label="Other charges">
                    <Input value={form.otherDescription} onChange={setField(row.admission, "otherDescription")} placeholder="e.g. Medicines" maxLength={200} />
                  </Field>
                  <Field label="Amount (₹)">
                    <Input type="number" min="0" step="0.01" inputMode="decimal" value={form.otherAmount} onChange={setField(row.admission, "otherAmount")} />
                  </Field>
                  <Button type="submit" loading={saving === row.admission}>Create final bill</Button>
                </form>
              )}
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
