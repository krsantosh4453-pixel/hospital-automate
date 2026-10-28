import { useEffect, useMemo, useState } from "react"
import { History } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Badge, EmptyState, Select, SkeletonRows } from "../ui"

// Longitudinal record (requirements B9, D12): every event of one patient at
// this hospital (the patient's own view: all their hospitals), newest first.
// The server decides what each viewer may see and audits every read.

const TONES = {
  Visit: "brand", Emergency: "danger", Admission: "warning", Discharge: "warning",
  Diagnosis: "accent", Lab: "success", Imaging: "success", Prescription: "neutral",
}

const dayOf = (value) => new Date(value).toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })
const timeOf = (value) => new Date(value).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })

export default function PatientTimeline({ patientId }) {
  const [events, setEvents] = useState(null)
  const [error, setError] = useState("")
  const [kind, setKind] = useState("")

  useEffect(() => {
    if (!patientId) return undefined
    let cancelled = false
    setEvents(null)
    setError("")
    api.patients
      .timeline(patientId)
      .then((data) => !cancelled && setEvents(data?.events || []))
      .catch((err) => !cancelled && setError(err.status === 403 ? "You are not allowed to see this patient's history." : err.message))
    return () => {
      cancelled = true
    }
  }, [patientId])

  const kinds = useMemo(() => [...new Set((events || []).map((e) => e.kind))].sort(), [events])
  const days = useMemo(() => {
    const groups = []
    for (const event of (events || []).filter((e) => !kind || e.kind === kind)) {
      const day = dayOf(event.when)
      const last = groups[groups.length - 1]
      if (last?.day === day) last.items.push(event)
      else groups.push({ day, items: [event] })
    }
    return groups
  }, [events, kind])

  if (error) return <Alert tone="danger">{error}</Alert>
  if (events === null) return <SkeletonRows rows={5} />
  if (events.length === 0) {
    return <EmptyState icon={History} title="No history yet" description="Visits, results and treatment appear here as they are recorded." />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[13px] text-ink-500">{events.length} event(s), newest first</p>
        <Select aria-label="Show only" className="w-44" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">Everything</option>
          {kinds.map((k) => <option key={k}>{k}</option>)}
        </Select>
      </div>
      <ol className="space-y-5">
        {days.map((group) => (
          <li key={group.day}>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">{group.day}</h3>
            <ol className="space-y-2 border-l-2 border-line pl-4">
              {group.items.map((event, i) => (
                <li key={`${event.kind}-${event.ref}-${i}`} className="relative">
                  <span className="absolute -left-[1.4rem] top-1.5 h-2.5 w-2.5 rounded-full bg-brand-500" aria-hidden="true" />
                  <div className="flex flex-wrap items-baseline gap-x-2">
                    <span className="text-xs tabular-nums text-ink-500">{timeOf(event.when)}</span>
                    <Badge tone={TONES[event.kind] || "neutral"}>{event.kind}</Badge>
                    <span className="font-medium text-ink-900">{event.title}</span>
                    {event.hospital && <span className="text-xs text-ink-500">· {event.hospital}</span>}
                  </div>
                  {event.detail && <p className="mt-0.5 whitespace-pre-line text-sm text-ink-700">{event.detail}</p>}
                </li>
              ))}
            </ol>
          </li>
        ))}
      </ol>
    </div>
  )
}
