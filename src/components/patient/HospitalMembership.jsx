import { useEffect, useState } from "react"
import { Building2 } from "lucide-react"
import api from "../../services/api.js"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { Alert, Button, Card, CardHeader, Field, Select, SkeletonRows } from "../ui"

// Prompt 3: a patient's hospital registrations (one UHID per hospital) and a
// way to join an open hospital from the app. The server decides which
// hospitals may be joined and issues the UHID; nothing here is trusted.

const hospitalLabel = (h) => (h.city ? `${h.name} (${h.city})` : h.name)

/**
 * Pick an open hospital and register there. Calls `onJoined` with the
 * server's answer ({ hospital, uhid, created, hospitals }).
 */
export function JoinHospitalForm({ onJoined }) {
  const { t } = useLanguage()
  const [hospitals, setHospitals] = useState(null) // null while loading
  const [loadFailed, setLoadFailed] = useState(false)
  const [choice, setChoice] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let cancelled = false
    setHospitals(null)
    setLoadFailed(false)
    api.auth
      .selfRegistrationHospitals()
      .then((data) => !cancelled && setHospitals(Array.isArray(data) ? data : data?.results || []))
      .catch(() => !cancelled && setLoadFailed(true))
    return () => {
      cancelled = true
    }
  }, [reload])

  const join = async () => {
    if (!choice) {
      setError(t("Choose a hospital."))
      return
    }
    setSaving(true)
    setError("")
    try {
      onJoined?.(await api.auth.joinHospital(choice))
    } catch (err) {
      setError(err.message || t("Not registered. Please try again."))
    } finally {
      setSaving(false)
    }
  }

  if (loadFailed) {
    return (
      <Alert tone="danger">
        {t("Hospitals could not be loaded.")}{" "}
        <Button size="sm" variant="secondary" onClick={() => setReload((n) => n + 1)}>{t("Try again")}</Button>
      </Alert>
    )
  }
  if (hospitals === null) return <p className="text-sm text-ink-500">{t("Loading hospitals…")}</p>
  if (hospitals.length === 0) {
    return <Alert tone="info">{t("No hospital accepts registration in the app at the moment. Please register at the hospital's reception.")}</Alert>
  }
  return (
    <div className="space-y-3">
      <Field label="Hospital" required>
        <Select id="join-hospital" value={choice} onChange={(e) => setChoice(e.target.value)}>
          <option value="">{t("Select hospital")}</option>
          {hospitals.map((h) => <option key={h.id} value={h.id}>{hospitalLabel(h)}</option>)}
        </Select>
      </Field>
      {error && <Alert tone="danger">{error}</Alert>}
      <Button onClick={join} loading={saving} disabled={saving}>{t("Register at this hospital")}</Button>
    </div>
  )
}

/** The hospitals the signed-in patient is registered at, each with its UHID. */
export function MyHospitalsCard() {
  const { t } = useLanguage()
  const [memberships, setMemberships] = useState(null)
  const [error, setError] = useState("")
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let cancelled = false
    api.auth
      .patientMe()
      .then((data) => !cancelled && setMemberships(data?.hospitals || data?.patient?.hospitals || []))
      .catch((err) => !cancelled && setError(err.message || t("Could not load your hospitals.")))
    return () => {
      cancelled = true
    }
  }, [reload, t])

  return (
    <Card>
      <CardHeader icon={Building2} title={t("Your hospitals")} description="Your patient ID (UHID) at each hospital you are registered with." />
      <div className="px-5 pb-5">
        {error ? (
          <Alert tone="danger">{error}</Alert>
        ) : memberships === null ? (
          <SkeletonRows rows={1} />
        ) : memberships.length === 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-ink-600">{t("You are not registered at any hospital yet. Register at one to book appointments.")}</p>
            <JoinHospitalForm onJoined={() => setReload((n) => n + 1)} />
          </div>
        ) : (
          <ul className="divide-y divide-line">
            {memberships.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                <span className="font-medium text-ink-900">{m.name}</span>
                <span className="tabular-nums text-ink-700">{t("UHID")} <span className="font-semibold">{m.uhid || "—"}</span></span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}
