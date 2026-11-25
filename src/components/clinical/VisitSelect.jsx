import { useEffect, useState } from "react"
import api from "../../services/api.js"
import { Field, Select } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// Prompt 5 (INT-002): link an order to the visit it belongs to. Lists only
// this patient's visits at this hospital; the server also refuses a visit of
// another patient. Roles that may not list visits simply don't see the field.

const rows = (data) => (Array.isArray(data) ? data : data?.results || [])
const label = (visit) => {
  const day = visit.visit_date ? new Date(visit.visit_date).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : ""
  return [`#${visit.id}`, visit.visit_type, day, visit.doctor_name, visit.status].filter(Boolean).join(" · ")
}

export default function VisitSelect({ hospitalId, patientId, value, onChange, disabled = false }) {
  const { t } = useLanguage()
  const [visits, setVisits] = useState([])
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    if (!hospitalId || !patientId) {
      setVisits([])
      return undefined
    }
    let cancelled = false
    api.visits
      .forPatient(hospitalId, patientId)
      .then((data) => {
        if (cancelled) return
        const list = rows(data).filter((visit) => String(visit.patient) === String(patientId))
        setVisits(list)
        setHidden(false)
        // The open visit is the usual one; a doctor can still choose another or none.
        const open = list.find((visit) => !["Completed", "Cancelled"].includes(visit.status))
        if (!value && open) onChange(String(open.id))
      })
      .catch(() => !cancelled && setHidden(true))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload only when the patient or hospital changes
  }, [hospitalId, patientId])

  if (hidden || !patientId) return null
  return (
    <Field label="Visit" htmlFor="order-visit" hint={visits.length === 0 ? t("This patient has no visit here yet.") : undefined}>
      <Select id="order-visit" value={value || ""} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        <option value="">{t("Not linked to a visit")}</option>
        {visits.map((visit) => <option key={visit.id} value={visit.id}>{label(visit)}</option>)}
      </Select>
    </Field>
  )
}
