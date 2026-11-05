import { useEffect, useState } from "react"
import api from "../../services/api.js"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { displayPatientId, maskedPhone } from "../../utils/patientIdentity.js"
import { Button, Input } from "../ui"

const MAX_RESULTS = 8
const DEBOUNCE_MS = 250
// The lookup endpoint refuses fewer than three characters (patients/views.py).
const MIN_CHARS = { list: 2, lookup: 3 }

const toList = (data) => (Array.isArray(data) ? data : data?.results || [])

function describe(patient) {
  const parts = [displayPatientId(patient)]
  const ageSex = [patient.age ? `${patient.age} y` : "", patient.gender || ""].filter(Boolean).join(", ")
  if (ageSex) parts.push(ageSex)
  const phone = String(patient.phone || "").includes("*") ? patient.phone : maskedPhone(patient.phone)
  if (phone) parts.push(phone)
  return parts.join(" · ")
}

/**
 * Choose a patient by searching the server (name, phone or UHID), so every
 * registered patient can be found, not only the first page (RL-03). The
 * result is chosen by id and shown with its UHID, so two patients with the
 * same name are never confused; nothing is ever matched by name.
 *
 * @param {object} props
 * @param {number|string} props.hospitalId
 * @param {string|number} props.value selected patient id, or ""
 * @param {(id: string, patient: object|null) => void} props.onChange
 * @param {object} [props.selected] the selected patient, when the page already knows it
 * @param {"list"|"lookup"} [props.source] "lookup" for roles that may not list patients
 * @param {string} [props.id] id for the search box; <Field> sets it to pair its label
 * @param {boolean} [props.required] blocks the form while no patient is chosen
 */
export default function PatientPicker({
  hospitalId, value, onChange, selected = null, source = "list", id, required = false, disabled = false,
  "aria-describedby": describedBy,
}) {
  const { t } = useLanguage()
  const [query, setQuery] = useState("")
  const [matches, setMatches] = useState([])
  const [status, setStatus] = useState("idle") // idle | searching | done | error
  const [picked, setPicked] = useState(selected)

  useEffect(() => {
    setPicked((current) => (selected && String(selected.id) === String(value) ? selected : current))
  }, [selected, value])

  const term = query.trim()
  const minChars = MIN_CHARS[source] || MIN_CHARS.list

  useEffect(() => {
    if (term.length < minChars || !hospitalId) {
      setMatches([])
      setStatus("idle")
      return undefined
    }
    let stale = false
    setStatus("searching")
    const timer = setTimeout(() => {
      const request = source === "lookup" ? api.patients.lookup(hospitalId, term) : api.patients.list(hospitalId, 1, term)
      request
        .then((data) => {
          if (stale) return
          setMatches(toList(data).slice(0, MAX_RESULTS))
          setStatus("done")
        })
        .catch(() => {
          if (stale) return
          setMatches([])
          setStatus("error")
        })
    }, DEBOUNCE_MS)
    return () => {
      stale = true
      clearTimeout(timer)
    }
  }, [term, minChars, hospitalId, source])

  const choose = (patient) => {
    setPicked(patient)
    setQuery("")
    setMatches([])
    onChange(String(patient.id), patient)
  }

  const clear = () => {
    setPicked(null)
    onChange("", null)
  }

  if (value) {
    const shown = picked && String(picked.id) === String(value) ? picked : null
    return (
      <div id={id} className="flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2 text-sm">
        <span className="min-w-0">
          <span className="font-medium text-ink-900">{shown ? shown.name : `${t("Patient")} #${value}`}</span>
          {shown && <span className="block text-xs text-ink-500 tabular-nums">{describe(shown)}</span>}
        </span>
        {!disabled && <Button size="sm" variant="ghost" onClick={clear}>{t("Change")}</Button>}
      </div>
    )
  }

  return (
    <div>
      <Input
        id={id}
        value={query}
        required={required}
        aria-describedby={describedBy}
        disabled={disabled}
        autoComplete="off"
        onChange={(e) => setQuery(e.target.value)}
        placeholder={t("Search by name, phone or UHID")}
      />
      {term.length > 0 && term.length < minChars && (
        <p className="mt-1 text-xs text-ink-500">{t("Type at least {n} characters.", { n: minChars })}</p>
      )}
      {status === "done" && matches.length === 0 && (
        <p className="mt-1 text-xs text-ink-500">{t("No patient matches. Check the spelling, phone or UHID.")}</p>
      )}
      {status === "error" && (
        <p role="alert" className="mt-1 text-xs text-red-700">{t("Could not search patients. Try again.")}</p>
      )}
      {matches.length > 0 && (
        <ul className="mt-1 max-h-64 divide-y divide-ink-100 overflow-y-auto rounded-lg border border-line">
          {matches.map((patient) => (
            <li key={patient.id}>
              <button type="button" className="w-full px-3 py-2 text-left text-sm hover:bg-ink-50" onClick={() => choose(patient)}>
                <span className="font-medium text-ink-900">{patient.name}</span>
                <span className="block text-xs text-ink-500 tabular-nums">{describe(patient)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
