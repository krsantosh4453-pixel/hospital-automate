import { useEffect, useState } from "react"
import { AlertTriangle, BedDouble, Phone } from "lucide-react"
import api from "../../services/api.js"

// Who the open record belongs to, kept in view while charting (A19):
// age, sex, phone, ward/bed when admitted and allergies, so the safety facts
// never scroll away. UHID is not shown: doctors cannot read it yet.

const readResults = (data) => (Array.isArray(data) ? data : data?.results || [])

export default function PatientContextStrip({ patientId }) {
  const [patient, setPatient] = useState(null)
  const [bed, setBed] = useState(null)
  const [allergies, setAllergies] = useState([])
  // "loading" | "loaded" | "failed": a failed check must not read as "none".
  const [allergyState, setAllergyState] = useState("loading")

  useEffect(() => {
    if (!patientId) return undefined
    let cancelled = false
    setPatient(null)
    setBed(null)
    setAllergies([])
    setAllergyState("loading")
    api.patients
      .get(patientId)
      .then((data) => !cancelled && setPatient(data))
      // Name and visit are already shown above; the extra facts are optional.
      .catch(() => {})
    api.ipd.admissions
      .currentForPatient(patientId)
      .then((data) => !cancelled && setBed(readResults(data)[0]?.current_bed || null))
      .catch(() => {})
    api.clinical.allergies
      .list({ patientId })
      .then((data) => {
        if (cancelled) return
        setAllergies(readResults(data))
        setAllergyState("loaded")
      })
      .catch(() => !cancelled && setAllergyState("failed"))
    return () => {
      cancelled = true
    }
  }, [patientId])

  const facts = [
    patient?.age != null && patient.age !== "" ? `${patient.age} y` : null,
    patient?.gender || null,
  ].filter(Boolean)

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line px-5 py-2.5 text-[13px]" aria-label="Patient summary">
      {facts.length > 0 && <span className="font-medium text-ink-800">{facts.join(" · ")}</span>}
      {patient?.phone && (
        <span className="inline-flex items-center gap-1.5 text-ink-600 tabular-nums">
          <Phone aria-hidden="true" className="h-3.5 w-3.5" />
          {patient.phone}
        </span>
      )}
      {bed && (
        <span className="inline-flex items-center gap-1.5 font-medium text-ink-800">
          <BedDouble aria-hidden="true" className="h-3.5 w-3.5" />
          {[bed.ward_name, bed.room_number && `Room ${bed.room_number}`, bed.bed_number && `Bed ${bed.bed_number}`].filter(Boolean).join(" · ")}
        </span>
      )}
      {allergyState === "loading" ? (
        <span className="text-ink-500">Checking allergies…</span>
      ) : allergyState === "failed" ? (
        <span className="inline-flex items-center gap-1.5 font-medium text-amber-700">
          <AlertTriangle aria-hidden="true" className="h-4 w-4" />
          Allergies could not be checked — confirm with the patient
        </span>
      ) : allergies.length === 0 ? (
        <span className="text-ink-600">No known allergies</span>
      ) : (
        <span className="inline-flex flex-wrap items-center gap-1.5" role="note">
          <AlertTriangle aria-hidden="true" className="h-4 w-4" />
          <span className="font-semibold">Allergies:</span>
          {allergies.map((allergy) => (
            <span key={allergy.id} className="rounded-full bg-red-700 px-2 py-0.5 font-medium text-white">
              {allergy.name}
              {allergy.severity ? ` (${allergy.severity})` : ""}
            </span>
          ))}
        </span>
      )}
    </div>
  )
}
