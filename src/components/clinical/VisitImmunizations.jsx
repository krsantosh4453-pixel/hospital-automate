import { useEffect, useState } from "react"
import { Pencil, Syringe } from "lucide-react"
import api from "../../services/api.js"
import {
  Alert,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  Input,
  Select,
  SkeletonRows,
  StatusBadge,
  TableWrap,
  Textarea,
} from "../ui"
import { formatPrintDate } from "../../utils/printDate.js"

// Vaccination register (D15) for the patient of the selected visit.
// Doses can be corrected (audited on the server) but not deleted.

const readResults = (data) => (Array.isArray(data) ? data : data?.results || [])

const today = () => new Date().toISOString().slice(0, 10)

const ROUTES = [
  ["", "—"],
  ["IM", "Intramuscular"],
  ["SC", "Subcutaneous"],
  ["ID", "Intradermal"],
  ["Oral", "Oral"],
  ["Nasal", "Intranasal"],
]

const emptyDose = () => ({
  vaccine: "",
  doseNumber: "1",
  administeredOn: today(),
  batchNumber: "",
  manufacturer: "",
  route: "",
  site: "",
  nextDueOn: "",
  notes: "",
})

const formFromDose = (dose) => ({
  vaccine: dose.vaccine,
  doseNumber: String(dose.dose_number),
  administeredOn: dose.administered_on,
  batchNumber: dose.batch_number,
  manufacturer: dose.manufacturer,
  route: dose.route,
  site: dose.site,
  nextDueOn: dose.next_due_on || "",
  notes: dose.notes,
})

const payloadFromForm = (form) => ({
  vaccine: form.vaccine.trim(),
  dose_number: Number(form.doseNumber) || 1,
  administered_on: form.administeredOn,
  batch_number: form.batchNumber.trim(),
  manufacturer: form.manufacturer.trim(),
  route: form.route,
  site: form.site.trim(),
  next_due_on: form.nextDueOn || null,
  notes: form.notes.trim(),
})

const dueStatus = (nextDueOn) => {
  if (!nextDueOn) return null
  return nextDueOn < today() ? "Overdue" : "Due"
}

export default function VisitImmunizations({ visit }) {
  const patientId = visit.patientApiId
  const [doses, setDoses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [form, setForm] = useState(emptyDose)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!patientId) return undefined
    let cancelled = false
    setLoading(true)
    setError("")
    api.clinical.immunizations
      .list({ patientId })
      .then((data) => !cancelled && setDoses(readResults(data)))
      .catch((err) => !cancelled && setError(err.message || "Could not load the vaccination record."))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [patientId])

  const set = (field) => (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))

  const reset = () => {
    setForm(emptyDose())
    setEditingId(null)
  }

  const save = async (event) => {
    event.preventDefault()
    if (!form.vaccine.trim()) {
      setError("Name the vaccine.")
      return
    }
    if (form.nextDueOn && form.nextDueOn <= form.administeredOn) {
      setError("The next dose must be due after this one.")
      return
    }
    setSaving(true)
    setError("")
    setNotice("")
    try {
      if (editingId) {
        const updated = await api.clinical.immunizations.update(editingId, payloadFromForm(form))
        setDoses((prev) => prev.map((dose) => (dose.id === editingId ? updated : dose)))
        setNotice("Dose corrected.")
      } else {
        const created = await api.clinical.immunizations.create({ patient: patientId, ...payloadFromForm(form) })
        setDoses((prev) => [created, ...prev])
        setNotice("Dose recorded.")
      }
      reset()
    } catch (err) {
      setError(err.message || "Could not save the dose.")
    } finally {
      setSaving(false)
    }
  }

  const edit = (dose) => {
    setEditingId(dose.id)
    setForm(formFromDose(dose))
    setError("")
    setNotice("")
  }

  return (
    <div className="space-y-5">
      {error && <Alert tone="danger" onDismiss={() => setError("")}>{error}</Alert>}
      {notice && <Alert tone="success" onDismiss={() => setNotice("")}>{notice}</Alert>}

      <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[22rem_minmax(0,1fr)]">
        <Card as="form" onSubmit={save}>
          <CardHeader
            title={editingId ? "Correct dose" : "Record vaccination"}
            description={editingId ? "Corrections are kept in the audit log." : `For ${visit.patientName}.`}
          />
          <div className="space-y-4 px-5 py-4">
            <Field label="Vaccine" required><Input value={form.vaccine} onChange={set("vaccine")} maxLength={150} placeholder="e.g. Hepatitis B" /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Dose no." required><Input type="number" min="1" inputMode="numeric" value={form.doseNumber} onChange={set("doseNumber")} /></Field>
              <Field label="Given on" required><Input type="date" max={today()} value={form.administeredOn} onChange={set("administeredOn")} /></Field>
              <Field label="Route">
                <Select value={form.route} onChange={set("route")}>
                  {ROUTES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </Select>
              </Field>
              <Field label="Site"><Input value={form.site} onChange={set("site")} maxLength={60} placeholder="e.g. Left deltoid" /></Field>
              <Field label="Batch no."><Input value={form.batchNumber} onChange={set("batchNumber")} maxLength={60} /></Field>
              <Field label="Manufacturer"><Input value={form.manufacturer} onChange={set("manufacturer")} maxLength={120} /></Field>
            </div>
            <Field label="Next dose due"><Input type="date" min={form.administeredOn} value={form.nextDueOn} onChange={set("nextDueOn")} /></Field>
            <Field label="Notes"><Textarea rows={2} value={form.notes} onChange={set("notes")} /></Field>
            <div className="flex gap-2">
              <Button type="submit" icon={Syringe} loading={saving} className="flex-1 justify-center">
                {editingId ? "Save correction" : "Record dose"}
              </Button>
              {editingId && <Button type="button" variant="secondary" onClick={reset}>Cancel</Button>}
            </div>
          </div>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader title="Vaccination history" description={`All of ${visit.patientName}'s doses, newest first`} />
          {loading ? (
            <div className="px-5 py-4"><SkeletonRows rows={3} /></div>
          ) : doses.length === 0 ? (
            <EmptyState compact icon={Syringe} title="No vaccinations recorded yet" />
          ) : (
            <TableWrap>
              <table className="hms-table">
                <thead>
                  <tr>
                    <th scope="col">Given</th>
                    <th scope="col">Vaccine</th>
                    <th scope="col" className="num">Dose</th>
                    <th scope="col">Route / site</th>
                    <th scope="col">Batch</th>
                    <th scope="col">Next due</th>
                    <th scope="col"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {doses.map((dose) => (
                    <tr key={dose.id}>
                      <td className="whitespace-nowrap tabular-nums text-ink-600">{formatPrintDate(dose.administered_on)}</td>
                      <td className="font-medium">{dose.vaccine}</td>
                      <td className="num">{dose.dose_number}</td>
                      <td>{[dose.route, dose.site].filter(Boolean).join(" · ") || "—"}</td>
                      <td>{dose.batch_number || "—"}</td>
                      <td className="whitespace-nowrap">
                        {dose.next_due_on ? (
                          <span className="inline-flex items-center gap-2 tabular-nums">
                            {formatPrintDate(dose.next_due_on)}
                            <StatusBadge status={dueStatus(dose.next_due_on)} />
                          </span>
                        ) : "—"}
                      </td>
                      <td className="text-right">
                        <Button variant="ghost" size="icon-sm" icon={Pencil} onClick={() => edit(dose)} aria-label={`Correct ${dose.vaccine} dose ${dose.dose_number}`} title="Correct" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}
        </Card>
      </div>
    </div>
  )
}
