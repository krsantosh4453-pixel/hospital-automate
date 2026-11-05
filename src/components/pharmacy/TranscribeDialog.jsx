import { useEffect, useState } from "react"
import { Plus, Trash2 } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, Field, Input, Modal, Select } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { hospitalToday } from "../../utils/hospitalDate.js"
import { mapPrescriptionFromApi } from "../../utils/prescriptionRecord.js"

// F13: the pharmacy copies a signed paper prescription into the system. It
// records who signed it and when; the server saves it Pending Verification
// and only someone else (another pharmacist or an Admin) can release it.

const LOOKUP_MIN_CHARS = 3
const emptyLine = () => ({ name: "", dosage: "", frequency: "", duration: "", quantity: "1", instructions: "" })
const EMPTY = { doctorId: "", outside: true, prescriberName: "", registration: "", paperDate: "", lines: [emptyLine()] }
const readList = (data) => (Array.isArray(data) ? data : data?.results || [])

const LINE_FIELDS = [
  ["name", "Medicine", "e.g. Paracetamol 500mg"],
  ["dosage", "Dose", "e.g. 1 tablet"],
  ["frequency", "Frequency", "e.g. 1-0-1"],
  ["duration", "Duration", "e.g. 5 days"],
  ["instructions", "Instructions", "As written on the paper"],
]

export default function TranscribeDialog({ open, hospitalId, onClose, onSaved }) {
  const { t } = useLanguage()
  const [form, setForm] = useState(EMPTY)
  const [doctors, setDoctors] = useState([])
  const [patientQuery, setPatientQuery] = useState("")
  const [matches, setMatches] = useState([])
  const [patient, setPatient] = useState(null)
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open || !hospitalId) return
    setForm({ ...EMPTY, paperDate: hospitalToday() })
    setPatient(null)
    setPatientQuery("")
    setError("")
    api.doctors.list(hospitalId).then((data) => setDoctors(readList(data))).catch(() => setDoctors([]))
  }, [open, hospitalId])

  const findPatient = async () => {
    setError("")
    if (patientQuery.trim().length < LOOKUP_MIN_CHARS) {
      setError(t("Type at least {count} characters of a name, phone or UHID.", { count: LOOKUP_MIN_CHARS }))
      return
    }
    try {
      setMatches(await api.patients.lookup(hospitalId, patientQuery.trim()))
    } catch (err) {
      setError(err.message || "Could not look the patient up.")
    }
  }

  const set = (field) => (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))
  const setLine = (index, field) => (event) => setForm((prev) => ({
    ...prev,
    lines: prev.lines.map((line, i) => (i === index ? { ...line, [field]: event.target.value } : line)),
  }))

  const submit = async (event) => {
    event.preventDefault()
    setError("")
    if (!patient) return setError(t("Choose the patient named on the paper prescription."))
    const lines = form.lines.filter((line) => line.name.trim())
    if (lines.length === 0) return setError(t("Add at least one medicine."))
    setSaving(true)
    try {
      const saved = await api.prescriptions.transcribe({
        hospital: hospitalId,
        patient: patient.id,
        doctor: form.outside ? null : Number(form.doctorId) || null,
        original_prescriber_name: form.outside ? form.prescriberName.trim() : "",
        original_prescriber_registration: form.outside ? form.registration.trim() : "",
        original_prescription_date: form.paperDate || null,
        items: lines.map((line) => ({ ...line, name: line.name.trim(), quantity: Number(line.quantity) || 1 })),
      })
      onSaved(mapPrescriptionFromApi(saved))
    } catch (err) {
      setError(t("Not saved: {reason}", { reason: err.message }))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} size="xl" title={t("Transcribe paper prescription")}
      description="Copy the signed paper exactly. Another pharmacist or an Admin must verify it before it is dispensed."
      footer={<><Button variant="secondary" onClick={onClose}>{t("Cancel")}</Button>
        <Button type="submit" form="transcribe-rx" loading={saving}>{t("Save for verification")}</Button></>}>
      <form id="transcribe-rx" onSubmit={submit} className="space-y-5">
        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold text-ink-900">{t("Patient")}</legend>
          {patient ? (
            <p className="flex items-center justify-between rounded-lg border border-line px-3 py-2 text-sm">
              <span>{patient.name} · {patient.age} y · {patient.gender} · {patient.phone}</span>
              <Button size="sm" variant="ghost" onClick={() => setPatient(null)}>{t("Change")}</Button>
            </p>
          ) : (
            <>
              <div className="flex gap-2">
                <Input aria-label={t("Find patient")} value={patientQuery} onChange={(e) => setPatientQuery(e.target.value)}
                  placeholder={t("Name, phone or UHID (3+ characters)")} className="flex-1" />
                <Button variant="secondary" onClick={findPatient}>{t("Find")}</Button>
              </div>
              <ul className="space-y-1">
                {matches.map((match) => (
                  <li key={match.id}>
                    <Button size="sm" variant="ghost" onClick={() => setPatient(match)}>
                      {match.name} · {match.age} y · {match.gender} · {match.phone}
                    </Button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </fieldset>

        <fieldset className="grid gap-3 md:grid-cols-2">
          <legend className="mb-2 text-sm font-semibold text-ink-900">{t("Signed by")}</legend>
          <Field label="Prescriber">
            <Select value={form.outside ? "outside" : "staff"}
              onChange={(e) => setForm((prev) => ({ ...prev, outside: e.target.value === "outside" }))}>
              <option value="outside">{t("Outside doctor")}</option>
              <option value="staff">{t("Doctor of this hospital")}</option>
            </Select>
          </Field>
          <Field label="Date on the paper" required>
            <Input type="date" max={hospitalToday()} value={form.paperDate} onChange={set("paperDate")} />
          </Field>
          {form.outside ? (
            <>
              <Field label="Doctor's name" required><Input value={form.prescriberName} onChange={set("prescriberName")} /></Field>
              <Field label="Registration number" required><Input value={form.registration} onChange={set("registration")} /></Field>
            </>
          ) : (
            <Field label="Doctor" required>
              <Select value={form.doctorId} onChange={set("doctorId")}>
                <option value="">{t("Choose a doctor")}</option>
                {doctors.map((doctor) => <option key={doctor.id} value={doctor.id}>{doctor.name}</option>)}
              </Select>
            </Field>
          )}
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-ink-900">{t("Medicines")}</legend>
          {form.lines.map((line, index) => (
            <div key={index} className="grid gap-2 rounded-lg border border-line p-3 md:grid-cols-6">
              {LINE_FIELDS.map(([field, label, placeholder]) => (
                <Field key={field} label={label} required={field === "name"}
                  className={field === "name" || field === "instructions" ? "md:col-span-2" : ""}>
                  <Input value={line[field]} onChange={setLine(index, field)} placeholder={t(placeholder)} />
                </Field>
              ))}
              <Field label="Qty" required><Input type="number" min="1" value={line.quantity} onChange={setLine(index, "quantity")} /></Field>
              {form.lines.length > 1 && (
                <div className="flex items-end">
                  <Button size="sm" variant="danger-ghost" icon={Trash2}
                    onClick={() => setForm((prev) => ({ ...prev, lines: prev.lines.filter((_, i) => i !== index) }))}>
                    {t("Remove")}
                  </Button>
                </div>
              )}
            </div>
          ))}
          <Button size="sm" variant="secondary" icon={Plus}
            onClick={() => setForm((prev) => ({ ...prev, lines: [...prev.lines, emptyLine()] }))}>
            {t("Add medicine")}
          </Button>
        </fieldset>

        {error && <Alert tone="danger">{error}</Alert>}
      </form>
    </Modal>
  )
}
