import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowLeft, ChevronRight, Printer } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, EmptyState, Field, Input, Modal, PrintSheet, PrintedDocument, PrintedFacts, Select, Textarea } from "../ui"
import { formatPrintDate } from "../../utils/printDate.js"
import { EMERGENCY_FORM_CODES, ER_ACTIONS, GENERIC_FORM_CODES, patientLink } from "./erActionList.js"

// The 24 emergency row actions of requirement J3 (spec Part 4 §13). The ER is
// a hub: actions that belong to the ER visit run here, the existing ER
// dialogs are reused, and actions owned by another module open that module
// with the patient already chosen (?patient=<id>&q=<name>).

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const IN_CARE = ["Under Consultation", "Investigations", "Treatment", "Observation"]


export default function ErActions({ visit, open, onClose, onOpenDialog, onChanged }) {
  const navigate = useNavigate()
  const [panel, setPanel] = useState(null)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  useEffect(() => {
    if (!open) {
      setPanel(null)
      setError("")
      setNotice("")
    }
  }, [open])

  if (!visit) return null
  const inCare = IN_CARE.includes(visit.status)

  const choose = (action) => {
    setError("")
    setNotice("")
    if (action.kind === "dialog") {
      onClose()
      onOpenDialog(action.id, visit)
    } else if (action.kind === "link") {
      onClose()
      navigate(patientLink(action, visit))
    } else {
      setPanel(action.id)
    }
  }

  const done = (message) => {
    setNotice(message)
    onChanged?.()
  }

  const current = ER_ACTIONS.find((action) => action.id === panel)
  const groups = [...new Set(ER_ACTIONS.map((action) => action.group))]

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={current ? current.label : "Emergency actions"}
      description={`${visit.patient_name} · ${visit.visit_number} · ${visit.status}`}
    >
      {error && <Alert tone="danger" className="mb-3" onDismiss={() => setError("")}>{error}</Alert>}
      {notice && <Alert tone="success" className="mb-3" onDismiss={() => setNotice("")}>{notice}</Alert>}
      {!current ? (
        <div className="space-y-4">
          {groups.map((group) => (
            <section key={group}>
              <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">{group}</h3>
              <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                {ER_ACTIONS.filter((action) => action.group === group).map((action) => {
                  const blocked = action.needsCare && !inCare
                  return (
                    <li key={action.id}>
                      <button
                        type="button"
                        disabled={blocked}
                        title={blocked ? "Available while the patient is under ER care" : undefined}
                        onClick={() => choose(action)}
                        className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-ink-800 hover:bg-ink-100 disabled:cursor-not-allowed disabled:text-ink-400"
                      >
                        {action.label}
                        <ChevronRight size={15} aria-hidden="true" />
                      </button>
                    </li>
                  )
                })}
              </ul>
            </section>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={() => setPanel(null)}>All actions</Button>
          <ActionPanel id={panel} visit={visit} onDone={done} onError={setError} />
        </div>
      )}
    </Modal>
  )
}

function ActionPanel({ id, visit, onDone, onError }) {
  switch (id) {
    case "notes":
      return <NotesPanel visit={visit} onDone={onDone} onError={onError} />
    case "allergy":
      return <AllergyPanel visit={visit} onDone={onDone} onError={onError} />
    case "results":
      return <ResultsPanel visit={visit} onError={onError} />
    case "emergency-forms":
      return <ConsentPanel visit={visit} codes={EMERGENCY_FORM_CODES} onDone={onDone} onError={onError} />
    case "consent":
      return <ConsentPanel visit={visit} onDone={onDone} onError={onError} />
    case "generic-consent":
      return <ConsentPanel visit={visit} codes={GENERIC_FORM_CODES} onDone={onDone} onError={onError} />
    case "drug-receive":
      return <DrugReceivePanel visit={visit} onDone={onDone} onError={onError} />
    case "admit":
      return <AdmitPanel visit={visit} onDone={onDone} onError={onError} />
    case "charge-slip":
      return <ChargeSlipPanel visit={visit} onError={onError} />
    case "bill-preview":
      return <ChargeSlipPanel visit={visit} onError={onError} startPrinting />
    case "discharge-summary":
      return <DischargeSummaryPanel visit={visit} />
    case "certificate":
      return <CertificatePanel visit={visit} onDone={onDone} onError={onError} />
    default:
      return null
  }
}

function useSubmit(onError) {
  const [saving, setSaving] = useState(false)
  const run = async (action) => {
    setSaving(true)
    onError("")
    try {
      await action()
    } catch (err) {
      onError(err.message || "Could not save.")
    } finally {
      setSaving(false)
    }
  }
  return [saving, run]
}

function NotesPanel({ visit, onDone, onError }) {
  const [note, setNote] = useState("")
  const [notes, setNotes] = useState(visit.notes || [])
  const [saving, run] = useSubmit(onError)
  const save = (event) => {
    event.preventDefault()
    run(async () => {
      const created = await api.emergency.visits.addNote(visit.id, note)
      setNotes((prev) => [created, ...prev])
      setNote("")
      onDone("Note added.")
    })
  }
  return (
    <div className="space-y-3">
      <form onSubmit={save} className="space-y-2">
        <Field label="New note" required><Textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        <Button type="submit" loading={saving}>Add note</Button>
      </form>
      {notes.length === 0 ? (
        <EmptyState compact title="No notes yet" />
      ) : (
        <ul className="divide-y divide-line text-sm">
          {notes.map((n) => (
            <li key={n.id} className="py-2">
              <p className="whitespace-pre-line text-ink-900">{n.note}</p>
              <p className="text-xs text-ink-500">{n.written_by_name || n.written_by_username} · {new Date(n.written_at).toLocaleString("en-IN")}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function AllergyPanel({ visit, onDone, onError }) {
  const [form, setForm] = useState({ name: "", reaction: "", severity: "Moderate" })
  const [allergies, setAllergies] = useState([])
  const [saving, run] = useSubmit(onError)
  useEffect(() => {
    api.clinical.allergies.list({ patientId: visit.patient }).then((d) => setAllergies(list(d))).catch(() => {})
  }, [visit.patient])
  const save = (event) => {
    event.preventDefault()
    run(async () => {
      const created = await api.clinical.allergies.create({ patient: visit.patient, ...form })
      setAllergies((prev) => [created, ...prev])
      setForm({ name: "", reaction: "", severity: "Moderate" })
      onDone("Allergy recorded.")
    })
  }
  return (
    <div className="space-y-3">
      {allergies.length > 0 && (
        <Alert tone="warning" title="Known allergies">{allergies.map((a) => `${a.name}${a.severity ? ` (${a.severity})` : ""}`).join(", ")}</Alert>
      )}
      <form onSubmit={save} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Field label="Allergen" required><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} maxLength={150} /></Field>
        <Field label="Reaction"><Input value={form.reaction} onChange={(e) => setForm({ ...form, reaction: e.target.value })} /></Field>
        <Field label="Severity">
          <Select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
            {["Mild", "Moderate", "Severe"].map((s) => <option key={s}>{s}</option>)}
          </Select>
        </Field>
        <Button type="submit" loading={saving} className="sm:col-span-3 sm:justify-self-start">Record allergy</Button>
      </form>
    </div>
  )
}

function ResultsPanel({ visit, onError }) {
  const [labTests, setLabTests] = useState(null)
  useEffect(() => {
    api.laboratory.tests
      .list(visit.hospital, visit.patient)
      .then((d) => setLabTests(list(d)))
      .catch((err) => onError(err.message))
  }, [visit.hospital, visit.patient, onError])
  const erResults = (visit.orders || []).filter((order) => order.result || order.status === "Completed")
  return (
    <div className="space-y-3 text-sm">
      <section>
        <h4 className="font-medium text-ink-800">ER orders</h4>
        {erResults.length === 0 ? <p className="text-ink-500">No ER order has a result yet.</p> : (
          <ul className="divide-y divide-line">
            {erResults.map((o) => <li key={o.id} className="py-1.5"><span className="font-medium">{o.description}</span>: {o.result || "Completed"}</li>)}
          </ul>
        )}
      </section>
      <section>
        <h4 className="font-medium text-ink-800">Laboratory</h4>
        {labTests === null ? <p className="text-ink-500">Loading…</p> : labTests.length === 0 ? <p className="text-ink-500">No lab tests.</p> : (
          <ul className="divide-y divide-line">
            {labTests.map((t) => (
              <li key={t.id} className="py-1.5">
                <span className="font-medium">{t.name}</span>: {t.status === "Released" ? (t.result || "Released") : `${t.status} (result not released yet)`}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function ConsentPanel({ visit, codes, onDone, onError }) {
  const [forms, setForms] = useState([])
  const [records, setRecords] = useState([])
  const [form, setForm] = useState({ code: "", signedName: visit.patient_name || "", proxy: false, relationship: "" })
  const [saving, run] = useSubmit(onError)
  useEffect(() => {
    api.consent.forms
      .list()
      .then((d) => {
        const all = (d?.forms || []).filter((f) => !codes || codes.includes(f.id))
        setForms(all)
        setForm((prev) => ({ ...prev, code: prev.code || all[0]?.id || "" }))
      })
      .catch((err) => onError(err.message))
    api.consent.records.list({ patient: visit.patient }).then((d) => setRecords(list(d))).catch(() => {})
  }, [visit.patient, codes, onError])
  const sign = (event) => {
    event.preventDefault()
    run(async () => {
      const created = await api.consent.records.sign({
        form: form.code,
        patient: visit.patient,
        signed_name: form.signedName,
        signed_by_proxy: form.proxy,
        proxy_relationship: form.proxy ? form.relationship : "",
        confirm: true,
      })
      setRecords((prev) => [created, ...prev])
      onDone("Consent recorded.")
    })
  }
  const active = records.filter((r) => !r.revoked_at && (!codes || codes.includes(r.form)))
  return (
    <div className="space-y-3">
      {active.length > 0 && (
        <p className="text-sm text-green-700">Signed: {active.map((r) => `${r.form_name} (${formatPrintDate(r.signed_at)})`).join(", ")}</p>
      )}
      <form onSubmit={sign} className="space-y-3">
        <Field label="Form" required>
          <Select value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })}>
            {forms.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
          </Select>
        </Field>
        <Field label="Signed by (full name)" required><Input value={form.signedName} onChange={(e) => setForm({ ...form, signedName: e.target.value })} /></Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.proxy} onChange={(e) => setForm({ ...form, proxy: e.target.checked })} />
          Signed by a relative or guardian (patient unable to sign)
        </label>
        {form.proxy && <Field label="Relationship to patient" required><Input value={form.relationship} onChange={(e) => setForm({ ...form, relationship: e.target.value })} /></Field>}
        <Button type="submit" loading={saving} disabled={!form.code}>Record signed consent</Button>
      </form>
    </div>
  )
}

function DrugReceivePanel({ visit, onDone, onError }) {
  const [meds, setMeds] = useState(visit.medications || [])
  const [saving, run] = useSubmit(onError)
  const pending = meds.filter((m) => !m.administered)
  const give = (med) =>
    run(async () => {
      const updated = await api.emergency.visits.administerMedication(visit.id, { medication_id: med.id })
      setMeds((prev) => prev.map((m) => (m.id === updated.id ? updated : m)))
      onDone(`${med.name} marked as received and given.`)
    })
  return pending.length === 0 ? (
    <EmptyState compact title="Nothing waiting" description="Every prescribed ER medicine has been given." />
  ) : (
    <ul className="divide-y divide-line text-sm">
      {pending.map((m) => (
        <li key={m.id} className="flex items-center justify-between gap-3 py-2">
          <span>{m.name} · {m.dose} · {m.route} · {m.frequency}</span>
          <Button size="sm" loading={saving} onClick={() => give(m)}>Received and given</Button>
        </li>
      ))}
    </ul>
  )
}

function AdmitPanel({ visit, onDone, onError }) {
  const [beds, setBeds] = useState(null)
  const [bedId, setBedId] = useState("")
  const [saving, run] = useSubmit(onError)
  useEffect(() => {
    api.ipd.bedAllocations.availableBeds(visit.hospital).then((d) => setBeds(list(d))).catch((err) => onError(err.message))
  }, [visit.hospital, onError])
  const admit = (event) => {
    event.preventDefault()
    run(async () => {
      const result = await api.emergency.visits.admitToIpd(visit.id, Number(bedId))
      onDone(`Admitted to ${result.admission?.bed || "the ward"}.`)
    })
  }
  if (beds === null) return <p className="text-sm text-ink-500">Loading free beds…</p>
  if (beds.length === 0) return <EmptyState compact title="No free bed" description="Free a bed in IPD first." />
  return (
    <form onSubmit={admit} className="space-y-3">
      <Field label="Bed" required>
        <Select value={bedId} onChange={(e) => setBedId(e.target.value)}>
          <option value="">Choose a bed</option>
          {beds.map((b) => <option key={b.id} value={b.id}>{b.ward} · Room {b.room} · Bed {b.bed_number}</option>)}
        </Select>
      </Field>
      <Button type="submit" loading={saving} disabled={!bedId}>Admit to this bed</Button>
    </form>
  )
}

function ChargeSlipPanel({ visit, onError, startPrinting = false }) {
  const [slip, setSlip] = useState(null)
  const [printing, setPrinting] = useState(false)
  useEffect(() => {
    api.emergency.visits
      .chargeSlip(visit.id)
      .then((d) => {
        setSlip(d)
        setPrinting(startPrinting)
      })
      .catch((err) => onError(err.message))
  }, [visit.id, startPrinting, onError])
  if (!slip) return <p className="text-sm text-ink-500">Loading charge slip…</p>
  return (
    <div className="space-y-3">
      {slip.lines.length === 0 ? <EmptyState compact title="Nothing charged yet" /> : (
        <ul className="divide-y divide-line text-sm">
          {slip.lines.map((line, i) => (
            <li key={i} className="flex justify-between gap-3 py-1.5"><span>{line.kind}: {line.description}</span><span className="text-ink-500">{line.status}</span></li>
          ))}
        </ul>
      )}
      <Button variant="secondary" icon={Printer} onClick={() => setPrinting(true)}>Bill preview / print</Button>
      <PrintSheet open={printing} onClose={() => setPrinting(false)} title="ER charge slip">
        <PrintedDocument hospitalName={slip.hospital_name} title="ER charge slip" reference={slip.visit_number} date={formatPrintDate(slip.arrival_time)}>
          <PrintedFacts rows={[["Patient", slip.patient_name], ["Visit status", slip.status]]} />
          <table className="w-full border-collapse text-left">
            <thead><tr className="border-b border-black"><th className="py-1">Date</th><th className="py-1">Type</th><th className="py-1">Item</th><th className="py-1">Status</th></tr></thead>
            <tbody>
              {slip.lines.map((line, i) => (
                <tr key={i} className="border-b border-gray-300">
                  <td className="py-1">{formatPrintDate(line.date)}</td><td className="py-1">{line.kind}</td><td className="py-1">{line.description}</td><td className="py-1">{line.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs">Prices are applied when the bill is made in Billing.</p>
        </PrintedDocument>
      </PrintSheet>
    </div>
  )
}

function DischargeSummaryPanel({ visit }) {
  const [printing, setPrinting] = useState(false)
  const finished = ["Discharged", "Referred", "Admitted"].includes(visit.status)
  return (
    <div className="space-y-3 text-sm">
      {!finished && <Alert tone="info">Use Discharge first; the summary prints the diagnosis and follow-up written there.</Alert>}
      <Button icon={Printer} disabled={!finished} onClick={() => setPrinting(true)}>Print ER discharge summary</Button>
      <PrintSheet open={printing} onClose={() => setPrinting(false)} title="ER discharge summary">
        <PrintedDocument
          hospitalName={visit.hospital_name}
          title="Emergency discharge summary"
          reference={visit.visit_number}
          date={formatPrintDate(visit.discharge_time)}
          signature={visit.attending_doctor_name}
        >
          <PrintedFacts rows={[
            ["Patient", visit.patient_name],
            ["Arrived", formatPrintDate(visit.arrival_time)],
            ["Triage", visit.triage_level],
            ["Chief complaint", visit.triage?.chief_complaint],
            ["Outcome", visit.disposition || visit.status],
            ["Diagnosis", visit.discharge_diagnosis],
          ]} />
          {(visit.medications || []).length > 0 && (
            <section>
              <p className="font-semibold">Medicines in the ER</p>
              <ul>{visit.medications.map((m) => <li key={m.id}>{m.name} {m.dose} {m.route}{m.administered ? "" : " (not given)"}</li>)}</ul>
            </section>
          )}
          {visit.follow_up_instructions && (
            <section><p className="font-semibold">Follow-up</p><p className="whitespace-pre-line">{visit.follow_up_instructions}</p></section>
          )}
        </PrintedDocument>
      </PrintSheet>
    </div>
  )
}

function CertificatePanel({ visit, onDone, onError }) {
  const today = new Date().toISOString().slice(0, 10)
  const [form, setForm] = useState({ kind: "Sick leave", diagnosis: visit.discharge_diagnosis || "", start: today, end: "" })
  const [saving, run] = useSubmit(onError)
  const issue = (event) => {
    event.preventDefault()
    run(async () => {
      await api.clinical.certificates.create({
        patient: visit.patient, kind: form.kind, diagnosis: form.diagnosis, start_date: form.start, end_date: form.end || null,
      })
      onDone("Certificate issued. Print it from Consultation → Certificates & referrals.")
    })
  }
  return (
    <form onSubmit={issue} className="space-y-3">
      <Field label="Type">
        <Select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
          {["Sick leave", "Fitness", "Other"].map((k) => <option key={k}>{k}</option>)}
        </Select>
      </Field>
      <Field label="Diagnosis"><Input value={form.diagnosis} onChange={(e) => setForm({ ...form, diagnosis: e.target.value })} maxLength={255} /></Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="From" required><Input type="date" value={form.start} onChange={(e) => setForm({ ...form, start: e.target.value })} /></Field>
        <Field label="To" required={form.kind === "Sick leave"}><Input type="date" min={form.start} value={form.end} onChange={(e) => setForm({ ...form, end: e.target.value })} /></Field>
      </div>
      <Button type="submit" loading={saving}>Issue certificate</Button>
    </form>
  )
}
