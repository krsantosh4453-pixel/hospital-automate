import { useState } from "react"
import { CheckCircle2 } from "lucide-react"
import api from "../../services/api.js"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { Alert, Button, Field, Input, Modal } from "../ui"

// Prompt 3: the front desk registers an EXISTING patient (for example one who
// signed up in the patient app) at this hospital, using POST /api/patients/link/.
// The server finds the patient only when the mobile number AND the date of
// birth both match, never creates a patient, and issues this hospital's UHID
// once; asking again returns the same registration (created: false).

const EMPTY = { phone: "", dob: "" }
const todayIso = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)

export default function EnrolExistingPatientDialog({ open, hospital, onClose, onEnrolled }) {
  const { t } = useLanguage()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState("")
  const [result, setResult] = useState(null)
  const [saving, setSaving] = useState(false)

  const close = () => {
    setForm(EMPTY)
    setError("")
    setResult(null)
    onClose()
  }

  const enrol = async () => {
    const phone = form.phone.replace(/\D/g, "")
    if (phone.length !== 10) {
      setError(t("Enter the patient's 10-digit mobile number."))
      return
    }
    if (!form.dob) {
      setError(t("Enter the patient's date of birth."))
      return
    }
    setSaving(true)
    setError("")
    setResult(null)
    try {
      const patient = await api.patients.link(hospital.id, { phone, date_of_birth: form.dob })
      setResult(patient)
      onEnrolled?.(patient)
    } catch (err) {
      setError(err.message || t("The patient could not be registered. Please try again."))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Enrol existing patient"
      description={hospital?.name}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={close} disabled={saving}>{t(result ? "Close" : "Cancel")}</Button>
          {!result && <Button onClick={enrol} loading={saving} disabled={saving}>{t("Find and enrol")}</Button>}
        </>
      }
    >
      {result ? (
        <Alert tone="success" title={result.created === false ? t("Already registered") : t("Patient registered")}>
          <span className="inline-flex items-start gap-2">
            <CheckCircle2 aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {result.created === false
                ? t("{name} is already registered at {hospital}.", { name: result.name, hospital: hospital?.name })
                : t("{name} is now registered at {hospital}.", { name: result.name, hospital: hospital?.name })}{" "}
              {t("UHID")} <strong className="tabular-nums">{result.uhid || "—"}</strong>
            </span>
          </span>
        </Alert>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-ink-600">
            {t("For a patient who already has an account (for example from the patient app). Both details must match the patient's record; nobody is found by the number alone.")}
          </p>
          <Field label="Mobile number" required>
            <Input
              id="enrol-phone"
              type="tel"
              inputMode="numeric"
              maxLength={10}
              value={form.phone}
              onChange={(e) => setForm((prev) => ({ ...prev, phone: e.target.value.replace(/\D/g, "").slice(0, 10) }))}
            />
          </Field>
          <Field label="Date of birth" required>
            <Input
              id="enrol-dob"
              type="date"
              max={todayIso()}
              value={form.dob}
              onChange={(e) => setForm((prev) => ({ ...prev, dob: e.target.value }))}
            />
          </Field>
          {error && <Alert tone="danger">{error}</Alert>}
        </div>
      )}
    </Modal>
  )
}
