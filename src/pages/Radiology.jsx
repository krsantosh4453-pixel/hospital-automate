import { useCallback, useEffect, useState } from "react"
import { CalendarClock, FilePenLine, Plus, Printer, RefreshCw, ScanSearch, XCircle, Zap } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import api from "../services/api.js"
import { useToast } from "../components/Toast.jsx"
import {
  Alert,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  PageHeader,
  PrintSheet,
  Select,
  SkeletonRows,
  StatusBadge,
  TableWrap,
  Tabs,
  Textarea,
} from "../components/ui"
import { ImagingReportDocument } from "../components/documents/ClinicalDocuments.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"

// Radiology / imaging (requirement G4). A doctor orders, the technician
// (Lab Staff) schedules and performs, a doctor reports and signs. The server
// enforces every rule; the buttons only reflect them.

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const MODALITIES = ["X-ray", "Ultrasound", "CT", "MRI", "Mammography", "Fluoroscopy", "ECG", "Echo", "Other"]
const EMPTY_ORDER = { patient: "", modality: "X-ray", body_part: "", indication: "", priority: "Routine" }
const TABS = [
  { id: "todo", label: "To perform", statuses: ["Ordered", "Scheduled"] },
  { id: "report", label: "Awaiting report", statuses: ["Performed"] },
  { id: "done", label: "Reported", statuses: ["Reported"] },
  { id: "all", label: "All", statuses: null },
]

const when = (value) => (value ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—")

function Radiology() {
  const { t } = useLanguage()
  const { selectedHospital } = usePatient()
  const { activeRoleName } = useRole()
  const toast = useToast()
  const isDoctor = activeRoleName === "Doctor" || activeRoleName === "Admin"
  const isTechnician = activeRoleName === "Lab Staff" || activeRoleName === "Admin"

  const [studies, setStudies] = useState([])
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [tab, setTab] = useState(isDoctor && !isTechnician ? "report" : "todo")
  const [dialog, setDialog] = useState(null) // { kind, study }
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [printing, setPrinting] = useState(null)

  const load = useCallback(async () => {
    if (!selectedHospital) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError("")
    try {
      const [studyData, patientData] = await Promise.all([
        api.imaging.list({ hospital: selectedHospital.id }),
        // Only the order form needs patients; not every role may list them.
        isDoctor ? api.patients.list(selectedHospital.id).catch(() => []) : Promise.resolve([]),
      ])
      setStudies(list(studyData))
      setPatients(list(patientData))
    } catch (err) {
      setError(err.message || "Imaging studies could not be loaded.")
    } finally {
      setLoading(false)
    }
  }, [selectedHospital, isDoctor])

  useEffect(() => {
    load()
  }, [load])

  const open = (kind, study = null, initial = {}) => {
    setForm(initial)
    setDialog({ kind, study })
  }
  const close = () => setDialog(null)
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  const submit = async (event, action, success) => {
    event?.preventDefault()
    setSaving(true)
    try {
      await action()
      toast.success(success)
      close()
      await load()
    } catch (err) {
      toast.error(err.message || "Not saved.")
    } finally {
      setSaving(false)
    }
  }

  const study = dialog?.study
  const shown = studies.filter((s) => {
    const statuses = TABS.find((t) => t.id === tab)?.statuses
    return !statuses || statuses.includes(s.status)
  })
  const counts = Object.fromEntries(
    TABS.map((t) => [t.id, t.statuses ? studies.filter((s) => t.statuses.includes(s.status)).length : studies.length]),
  )

  const footer = (label) => (
    <>
      <Button variant="secondary" onClick={close}>{t("Cancel")}</Button>
      <Button type="submit" form="radiology-form" loading={saving}>{label}</Button>
    </>
  )

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("Radiology")}
        description={selectedHospital ? `Imaging orders, scans and reports at ${selectedHospital.name}.` : "Select a hospital to see imaging."}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Radiology" }]}
        actions={selectedHospital && (
          <>
            <Button variant="secondary" icon={RefreshCw} onClick={load} disabled={loading}>{t("Refresh")}</Button>
            {isDoctor && <Button icon={Plus} onClick={() => open("order", null, EMPTY_ORDER)}>{t("New imaging order")}</Button>}
          </>
        )}
      />

      {!selectedHospital ? (
        <Card><EmptyState icon={ScanSearch} title={t("Select a hospital")} /></Card>
      ) : error ? (
        <Card><ErrorState title={t("Imaging could not be loaded")} message={error} onRetry={load} /></Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="px-4 pt-3">
            <Tabs tabs={TABS.map((t) => ({ id: t.id, label: t.label, count: counts[t.id] }))} value={tab} onChange={setTab} label="Imaging worklist" />
          </div>
          {loading ? (
            <SkeletonRows rows={4} />
          ) : shown.length === 0 ? (
            <EmptyState icon={ScanSearch} title={t("Nothing here")} />
          ) : (
            <TableWrap>
              <table className="hms-table">
                <thead>
                  <tr>
                    <th scope="col">{t("Accession")}</th>
                    <th scope="col">{t("Patient")}</th>
                    <th scope="col">{t("Examination")}</th>
                    <th scope="col">{t("Priority")}</th>
                    <th scope="col">{t("Status")}</th>
                    <th scope="col">{t("When")}</th>
                    <th scope="col"><span className="sr-only">{t("Actions")}</span></th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((s) => (
                    <tr key={s.id}>
                      <td className="tabular-nums">{s.accession_number}</td>
                      <td className="font-medium text-ink-900">{s.patient_name}</td>
                      <td>
                        <span className="block">{s.modality} · {s.body_part}</span>
                        <span className="block max-w-xs truncate text-xs text-ink-500" title={s.indication}>{s.indication}</span>
                      </td>
                      <td>{s.priority === "Routine" ? s.priority : <span className="font-semibold text-red-700">{s.priority}</span>}</td>
                      <td><StatusBadge status={s.status} /></td>
                      <td className="whitespace-nowrap text-ink-600">
                        {s.status === "Scheduled" ? when(s.scheduled_for)
                          : s.status === "Reported" ? when(s.reported_at)
                            : s.status === "Performed" ? when(s.performed_at)
                              : when(s.ordered_at)}
                      </td>
                      <td>
                        <div className="flex flex-wrap justify-end gap-1.5">
                          {isTechnician && ["Ordered", "Scheduled"].includes(s.status) && (
                            <>
                              <Button size="sm" variant="ghost" icon={CalendarClock} onClick={() => open("schedule", s, { scheduled_for: "" })}>{t("Schedule")}</Button>
                              <Button size="sm" variant="subtle" icon={Zap} onClick={() => open("perform", s, { technician_notes: "" })}>{t("Performed")}</Button>
                            </>
                          )}
                          {isDoctor && s.status === "Performed" && (
                            <Button size="sm" icon={FilePenLine} onClick={() => open("report", s, { findings: "", impression: "" })}>{t("Report")}</Button>
                          )}
                          {isDoctor && ["Ordered", "Scheduled"].includes(s.status) && (
                            <Button size="sm" variant="danger-ghost" icon={XCircle} onClick={() => open("cancel", s)}>{t("Cancel")}</Button>
                          )}
                          {s.status === "Reported" && (
                            <Button size="sm" variant="secondary" icon={Printer} onClick={() => setPrinting(s)}>{t("Print")}</Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}
        </Card>
      )}

      <Modal open={dialog?.kind === "order"} onClose={close} title={t("New imaging order")} footer={footer("Place order")}>
        <form id="radiology-form" className="space-y-3" onSubmit={(e) => submit(e, () => api.imaging.create({ ...form, patient: Number(form.patient) }), "Imaging ordered.")}>
          <Field label="Patient" required>
            <Select value={form.patient || ""} onChange={set("patient")}>
              <option value="">Choose a patient</option>
              {patients.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.phone}</option>)}
            </Select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Modality" required>
              <Select value={form.modality || "X-ray"} onChange={set("modality")}>{MODALITIES.map((m) => <option key={m}>{m}</option>)}</Select>
            </Field>
            <Field label="Priority">
              <Select value={form.priority || "Routine"} onChange={set("priority")}>{["Routine", "Urgent", "STAT"].map((p) => <option key={p}>{p}</option>)}</Select>
            </Field>
          </div>
          <Field label="Body part / region" required><Input value={form.body_part || ""} onChange={set("body_part")} placeholder={t("e.g. Chest PA")} maxLength={120} /></Field>
          <Field label="Clinical question" required><Textarea rows={3} value={form.indication || ""} onChange={set("indication")} /></Field>
        </form>
      </Modal>

      <Modal open={dialog?.kind === "schedule"} onClose={close} title={t("Schedule scan")} description={study && `${study.patient_name} · ${study.modality} ${study.body_part}`} footer={footer("Schedule")}>
        <form id="radiology-form" onSubmit={(e) => submit(e, () => api.imaging.schedule(study.id, { scheduled_for: new Date(form.scheduled_for).toISOString() }), "Scan scheduled.")}>
          <Field label="Date and time" required><Input type="datetime-local" value={form.scheduled_for || ""} onChange={set("scheduled_for")} /></Field>
        </form>
      </Modal>

      <Modal open={dialog?.kind === "perform"} onClose={close} title={t("Mark scan performed")} description={study && `${study.patient_name} · ${study.modality} ${study.body_part}`} footer={footer("Mark performed")}>
        <form id="radiology-form" onSubmit={(e) => submit(e, () => api.imaging.perform(study.id, form), "Scan performed; awaiting report.")}>
          <Field label="Technician notes"><Textarea rows={3} value={form.technician_notes || ""} onChange={set("technician_notes")} /></Field>
        </form>
      </Modal>

      <Modal open={dialog?.kind === "report"} onClose={close} size="lg" title={t("Report and sign")} description={study && `${study.patient_name} · ${study.modality} ${study.body_part} · ${study.accession_number}`} footer={footer("Sign report")}>
        <form id="radiology-form" className="space-y-3" onSubmit={(e) => submit(e, () => api.imaging.report(study.id, form), "Report signed.")}>
          {study && <Alert tone="info" title={t("Clinical question")}>{study.indication}{study.technician_notes ? ` · Technician: ${study.technician_notes}` : ""}</Alert>}
          <Field label="Findings" required><Textarea rows={5} value={form.findings || ""} onChange={set("findings")} /></Field>
          <Field label="Impression" required><Textarea rows={2} value={form.impression || ""} onChange={set("impression")} /></Field>
          <p className="text-xs text-ink-500">{t("Signing locks the report; it cannot be edited afterwards.")}</p>
        </form>
      </Modal>

      <Modal open={dialog?.kind === "cancel"} onClose={close} title={t("Cancel imaging order?")} description={study && `${study.patient_name} · ${study.modality} ${study.body_part}`} footer={footer("Cancel order")}>
        <form id="radiology-form" onSubmit={(e) => submit(e, () => api.imaging.cancel(study.id), "Order cancelled.")}>
          <p className="text-sm text-ink-700">{t("The order stays on record as cancelled.")}</p>
        </form>
      </Modal>

      <PrintSheet open={Boolean(printing)} onClose={() => setPrinting(null)} title={t("Radiology report")}>
        {printing && <ImagingReportDocument study={printing} />}
      </PrintSheet>
    </div>
  )
}

export default Radiology
