import { useEffect, useState } from "react"
import { AlertTriangle, BedDouble, Phone } from "lucide-react"
import api from "../../services/api.js"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { useRole } from "../../assets/context/RoleContext.jsx"
import { Button, ConfirmDialog, Field, Input, Modal, Select } from "../ui"
import { allergySummary, NO_KNOWN_ALLERGIES } from "./allergyStatus.js"

// Who the open record belongs to, kept in view while charting (A19):
// age, sex, phone, ward/bed when admitted and allergies, so the safety facts
// never scroll away, with the UHID at this hospital.

const readResults = (data) => (Array.isArray(data) ? data : data?.results || [])
// The backend lets these roles record allergy facts (patients allergy-status,
// clinical/allergies); it refuses everyone else whatever the page shows.
const ALLERGY_RECORDERS = ["Doctor", "Nurse"]
const LOADING = { state: "loading" }

export default function PatientContextStrip({ patientId }) {
  const { t } = useLanguage()
  const [patient, setPatient] = useState(LOADING)
  const [allergies, setAllergies] = useState(LOADING)
  const [bed, setBed] = useState(null)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    if (!patientId) return undefined
    let cancelled = false
    // Never show the previous patient's facts while this one loads (BUG-001).
    setPatient(LOADING)
    setAllergies(LOADING)
    setBed(null)
    api.patients
      .get(patientId)
      .then((data) => !cancelled && setPatient({ state: "loaded", data }))
      // A record that did not load cannot confirm "no known allergies".
      .catch(() => !cancelled && setPatient({ state: "failed" }))
    api.ipd.admissions
      .currentForPatient(patientId)
      .then((data) => !cancelled && setBed(readResults(data)[0]?.current_bed || null))
      .catch(() => {})
    api.clinical.allergies
      .list({ patientId })
      .then((data) => !cancelled && setAllergies({ state: "loaded", data: readResults(data) }))
      .catch(() => !cancelled && setAllergies({ state: "failed" }))
    return () => {
      cancelled = true
    }
  }, [patientId, refresh])

  const record = patient.data
  const facts = [
    record?.age != null && record.age !== "" ? `${record.age} y` : null,
    record?.gender || null,
  ].filter(Boolean)
  const summary = allergySummary({ patient, allergies })

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line px-5 py-2.5 text-[13px]" aria-label={t("Patient summary")}>
      {record?.uhid && <span className="font-semibold tabular-nums text-ink-900">{t("UHID")} {record.uhid}</span>}
      {facts.length > 0 && <span className="font-medium text-ink-800">{facts.join(" · ")}</span>}
      {record?.phone && (
        <span className="inline-flex items-center gap-1.5 text-ink-600 tabular-nums">
          <Phone aria-hidden="true" className="h-3.5 w-3.5" />
          {record.phone}
        </span>
      )}
      {bed && (
        <span className="inline-flex items-center gap-1.5 font-medium text-ink-800">
          <BedDouble aria-hidden="true" className="h-3.5 w-3.5" />
          {[bed.ward_name, bed.room_number && `Room ${bed.room_number}`, bed.bed_number && `Bed ${bed.bed_number}`].filter(Boolean).join(" · ")}
        </span>
      )}
      <AllergyStatus summary={summary} />
      <AllergyActions patientId={patientId} summary={summary} onRecorded={() => setRefresh((n) => n + 1)} />
    </div>
  )
}

const WARNING = "inline-flex items-center gap-1.5 font-medium text-amber-700"

function AllergyStatus({ summary }) {
  const { t } = useLanguage()
  switch (summary.kind) {
    case "loading":
      return <span className="text-ink-500">{t("Checking allergies…")}</span>
    case "failed":
      return (
        <span className={WARNING} role="note">
          <AlertTriangle aria-hidden="true" className="h-4 w-4" />
          {t("Allergies could not be checked — confirm with the patient")}
        </span>
      )
    case "nka":
      return <span className="text-ink-600">{t("No known allergies")}</span>
    case "review":
      return (
        <span className={WARNING} role="note">
          <AlertTriangle aria-hidden="true" className="h-4 w-4" />
          {t("Allergies are on record elsewhere — review with the patient")}
        </span>
      )
    case "known":
      return (
        <span className="inline-flex flex-wrap items-center gap-1.5" role="note">
          <AlertTriangle aria-hidden="true" className="h-4 w-4" />
          <span className="font-semibold">{t("Allergies:")}</span>
          {summary.allergies.map((allergy) => (
            <span key={allergy.id} className="rounded-full bg-red-700 px-2 py-0.5 font-medium text-white">
              {allergy.name}
              {allergy.severity ? ` (${allergy.severity})` : ""}
            </span>
          ))}
        </span>
      )
    default:
      // "unknown": nobody has asked. Never shown as "No known allergies".
      return (
        <span className={WARNING} role="note">
          <AlertTriangle aria-hidden="true" className="h-4 w-4" />
          {t("Allergy status unknown — ask the patient")}
        </span>
      )
  }
}

function AllergyActions({ patientId, summary, onRecorded }) {
  const { t } = useLanguage()
  const { activeRoleName } = useRole()
  const [dialog, setDialog] = useState(null) // "nka" | "add" | null
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  if (!ALLERGY_RECORDERS.includes(activeRoleName) || ["loading", "failed"].includes(summary.kind)) return null

  const close = () => {
    setDialog(null)
    setError("")
  }
  const save = async (write) => {
    setSaving(true)
    setError("")
    try {
      await write()
      close()
      onRecorded()
    } catch (err) {
      setError(err.message || t("Not saved."))
    } finally {
      setSaving(false)
    }
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      {summary.kind === "unknown" && (
        <Button size="sm" variant="secondary" onClick={() => setDialog("nka")}>{t("Record no known allergies")}</Button>
      )}
      <Button size="sm" variant="secondary" onClick={() => setDialog("add")}>{t("Add allergy")}</Button>
      <ConfirmDialog
        open={dialog === "nka"}
        onCancel={close}
        onConfirm={() => save(() => api.patients.setAllergyStatus(patientId, NO_KNOWN_ALLERGIES))}
        title="Record no known allergies"
        message="Record this only after asking the patient (or their carer) and confirming they have no known allergies. It is saved in your name."
        confirmLabel="Patient has no known allergies"
        loading={saving}
      >
        {error && <p className="mt-2 text-sm text-red-700" role="alert">{error}</p>}
      </ConfirmDialog>
      {/* Mounted only while open: each opening starts empty; a failed save keeps the entry. */}
      {dialog === "add" && (
        <AddAllergyDialog
          saving={saving}
          error={error}
          onCancel={close}
          onSave={(form) => save(() => api.clinical.allergies.create({ patient: patientId, ...form }))}
        />
      )}
    </span>
  )
}

const EMPTY_ALLERGY = { name: "", reaction: "", severity: "Moderate", category: "Drug" }

function AddAllergyDialog({ saving, error, onCancel, onSave }) {
  const { t } = useLanguage()
  const [form, setForm] = useState(EMPTY_ALLERGY)
  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))
  const submit = (event) => {
    event.preventDefault()
    if (!form.name.trim()) return
    onSave({ ...form, name: form.name.trim() })
  }

  return (
    <Modal
      open
      onClose={onCancel}
      title="Add allergy"
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onCancel} disabled={saving}>{t("Cancel")}</Button>
          <Button type="submit" form="add-allergy-form" loading={saving}>{t("Record allergy")}</Button>
        </>
      }
    >
      <form id="add-allergy-form" onSubmit={submit} className="space-y-3">
        <Field label="Allergen" required><Input value={form.name} onChange={set("name")} maxLength={150} required /></Field>
        <Field label="Reaction"><Input value={form.reaction} onChange={set("reaction")} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Severity">
            <Select value={form.severity} onChange={set("severity")}>
              {["Mild", "Moderate", "Severe"].map((s) => <option value={s} key={s}>{t(s)}</option>)}
            </Select>
          </Field>
          <Field label="Type">
            <Select value={form.category} onChange={set("category")}>
              {["Drug", "Food", "Environmental", "Other"].map((c) => <option value={c} key={c}>{t(c)}</option>)}
            </Select>
          </Field>
        </div>
        {error && <p className="text-sm text-red-700" role="alert">{error}</p>}
      </form>
    </Modal>
  )
}
