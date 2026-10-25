import { useState, useEffect, useCallback } from "react"
import { Activity, Ambulance, ClipboardPlus, HeartPulse, LogOut, Pill, Plus, RefreshCw, Send, Stethoscope } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api"
import { useToast } from "../components/Toast.jsx"
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  SkeletonRows,
  StatTile,
  StatusBadge,
  TableWrap,
  Tabs,
  Textarea,
} from "../components/ui"

const list = (data) => (Array.isArray(data) ? data : data?.results || [])

// Triage levels in priority order, with their target times.
const TRIAGE = [
  { level: "Critical", target: "Immediate", tone: "danger" },
  { level: "Emergency", target: "< 15 min", tone: "danger" },
  { level: "Urgent", target: "< 30 min", tone: "warning" },
  { level: "Semi-Urgent", target: "< 60 min", tone: "brand" },
  { level: "Non-Urgent", target: "< 120 min", tone: "success" },
]
const triageRank = (level) => {
  const i = TRIAGE.findIndex((t) => t.level === level)
  return i === -1 ? TRIAGE.length : i
}
const DONE = ["Discharged", "Admitted", "Referred", "Expired", "Left Against Advice"]
const IN_CARE = ["Under Consultation", "Investigations", "Treatment", "Observation"]

const toInt = (v) => (v === "" || v === undefined ? null : parseInt(v, 10))
const toFloat = (v) => (v === "" || v === undefined ? null : parseFloat(v))

const EMPTY = {
  registration: { patient: "", triage_level: "Non-Urgent", remarks: "", attending_doctor: "" },
  triage: { chief_complaint: "", pain_score: "", glasgow_coma_scale: "", triage_notes: "", triage_level: "Non-Urgent", triaged_by: "" },
  vitals: { temperature: "", systolic_bp: "", diastolic_bp: "", heart_rate: "", respiratory_rate: "", spo2: "", blood_sugar: "", recorded_by: "" },
  order: { order_type: "Lab", description: "", ordered_by: "" },
  medication: { name: "", dose: "", route: "IV", frequency: "", duration: "", prescribed_by: "" },
  discharge: { discharge_diagnosis: "", follow_up_instructions: "" },
  refer: { referred_to: "", discharge_diagnosis: "" },
}

function TriageBadge({ level }) {
  const t = TRIAGE.find((x) => x.level === level)
  return <Badge tone={t?.tone || "neutral"} dot>{level || "—"}</Badge>
}

function Emergency() {
  const toast = useToast()
  const { selectedHospital } = usePatient()

  const [visits, setVisits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState("active")
  const [dashboardStats, setDashboardStats] = useState({})
  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])
  const [nurses, setNurses] = useState([])

  const [dialog, setDialog] = useState(null)
  const [selectedVisit, setSelectedVisit] = useState(null)
  const [forms, setForms] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  const setForm = (name) => (field) => (e) => setForms((prev) => ({ ...prev, [name]: { ...prev[name], [field]: e.target.value } }))

  const fetchData = useCallback(async () => {
    if (!selectedHospital) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const [visitsRes, patientsRes, doctorsRes, nursesRes, dashboardRes] = await Promise.all([
        api.emergency.visits.list(selectedHospital.id),
        api.patients.list(selectedHospital.id),
        api.doctors.list(selectedHospital.id),
        api.nurses.nurses.list(selectedHospital.id),
        api.emergency.visits.dashboard(selectedHospital.id),
      ])
      setVisits(list(visitsRes))
      setPatients(list(patientsRes))
      setDoctors(list(doctorsRes))
      setNurses(list(nursesRes))
      setDashboardStats(dashboardRes || {})
    } catch (err) {
      setError(err.message || "Failed to load emergency data")
    } finally {
      setLoading(false)
    }
  }, [selectedHospital])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const open = (name, visit = null, preset = {}) => {
    setSelectedVisit(visit)
    setForms((prev) => ({ ...prev, [name]: { ...EMPTY[name], ...preset } }))
    setDialog(name)
  }
  const close = () => {
    setDialog(null)
    setSelectedVisit(null)
  }

  const submit = (fn, okMessage) => async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await fn()
      toast.success(okMessage)
      close()
      fetchData()
    } catch (err) {
      toast.error(err.message || "Not saved")
    } finally {
      setSaving(false)
    }
  }

  const f = forms

  const handleRegistration = submit(
    () =>
      api.emergency.visits.create({
        // Ids, not names: two patients can share a name.
        patient: toInt(f.registration.patient),
        hospital: selectedHospital.id,
        triage_level: f.registration.triage_level,
        remarks: f.registration.remarks,
        attending_doctor: toInt(f.registration.attending_doctor),
      }),
    "Emergency visit registered",
  )

  const handleCompleteTriage = submit(async () => {
    // A registered visit must enter triage before it can be completed.
    if (selectedVisit.status === "Registered") await api.emergency.visits.startTriage(selectedVisit.id)
    await api.emergency.visits.completeTriage(selectedVisit.id, {
      chief_complaint: f.triage.chief_complaint,
      pain_score: toInt(f.triage.pain_score),
      glasgow_coma_scale: toInt(f.triage.glasgow_coma_scale),
      triage_notes: f.triage.triage_notes,
      triage_level: f.triage.triage_level,
      triaged_by: toInt(f.triage.triaged_by),
    })
  }, "Triage completed")

  const handleStartConsultation = async (visit) => {
    try {
      await api.emergency.visits.startConsultation(visit.id, { doctor_id: visit.attending_doctor })
      toast.success(`Consultation started for ${visit.patient_name}`)
      fetchData()
    } catch (err) {
      toast.error(err.message || "Failed to start consultation")
    }
  }

  const handleAddVitals = submit(
    () =>
      api.emergency.visits.addVitals(selectedVisit.id, {
        temperature: toFloat(f.vitals.temperature),
        systolic_bp: toInt(f.vitals.systolic_bp),
        diastolic_bp: toInt(f.vitals.diastolic_bp),
        heart_rate: toInt(f.vitals.heart_rate),
        respiratory_rate: toInt(f.vitals.respiratory_rate),
        spo2: toInt(f.vitals.spo2),
        blood_sugar: toFloat(f.vitals.blood_sugar),
        recorded_by: toInt(f.vitals.recorded_by),
      }),
    "Vitals recorded",
  )

  const handleAddOrder = submit(
    () =>
      api.emergency.visits.addOrder(selectedVisit.id, {
        order_type: f.order.order_type,
        description: f.order.description,
        ordered_by: toInt(f.order.ordered_by),
      }),
    "Order added",
  )

  const handleAddMedication = submit(
    () =>
      api.emergency.visits.addMedication(selectedVisit.id, {
        name: f.medication.name,
        dose: f.medication.dose,
        route: f.medication.route,
        frequency: f.medication.frequency,
        duration: f.medication.duration,
        prescribed_by: toInt(f.medication.prescribed_by),
      }),
    "Medication prescribed",
  )

  const handleDischarge = submit(
    () => api.emergency.visits.discharge(selectedVisit.id, { discharge_diagnosis: f.discharge.discharge_diagnosis, follow_up_instructions: f.discharge.follow_up_instructions || "" }),
    "Patient discharged",
  )

  const handleRefer = submit(
    () => api.emergency.visits.refer(selectedVisit.id, { referred_to: f.refer.referred_to, discharge_diagnosis: f.refer.discharge_diagnosis || "" }),
    "Patient referred",
  )

  const doctorOptions = (
    <>
      <option value="">Not specified</option>
      {doctors.map((d) => <option key={d.id} value={d.id}>{d.name}{d.specialization ? ` — ${d.specialization}` : ""}</option>)}
    </>
  )
  const nurseOptions = (
    <>
      <option value="">Not specified</option>
      {nurses.map((n) => <option key={n.id} value={n.id}>{n.name}{n.department ? ` — ${n.department}` : ""}</option>)}
    </>
  )
  const triageOptions = TRIAGE.map((t) => <option key={t.level} value={t.level}>{t.level} ({t.target})</option>)

  const header = (
    <PageHeader
      title="Emergency"
      description={selectedHospital ? `ER board for ${selectedHospital.name}, sorted by triage priority.` : undefined}
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Emergency" }]}
      actions={
        selectedHospital && (
          <>
            <Button variant="secondary" icon={RefreshCw} onClick={fetchData} disabled={loading}>Refresh</Button>
            <Button variant="danger" icon={Plus} onClick={() => open("registration")}>New ER visit</Button>
          </>
        )
      }
    />
  )

  if (!selectedHospital) {
    return (
      <div className="space-y-5">
        {header}
        <Card><EmptyState icon={Ambulance} title="Select a hospital" description="Choose a hospital in the header to open its ER board." /></Card>
      </div>
    )
  }

  const activeVisits = visits.filter((v) => !DONE.includes(v.status)).sort((a, b) => triageRank(a.triage_level) - triageRank(b.triage_level) || new Date(a.arrival_time) - new Date(b.arrival_time))
  const completedVisits = visits.filter((v) => DONE.includes(v.status))
  const triaged = visits.filter((v) => v.triage)
  const counts = dashboardStats.triage_counts || {}

  const visitTitle = selectedVisit ? `${selectedVisit.visit_number || `Visit #${selectedVisit.id}`} · ${selectedVisit.patient_name}` : ""
  const footer = (form, label) => (
    <>
      <Button variant="secondary" onClick={close}>Cancel</Button>
      <Button type="submit" form={form} loading={saving}>{label}</Button>
    </>
  )

  return (
    <div className="space-y-5">
      {header}

      {error ? (
        <Card><ErrorState title="Emergency data could not be loaded" message={error} onRetry={fetchData} /></Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
            <StatTile icon={Activity} tone="danger" label="Active patients" value={loading ? null : activeVisits.length} />
            {TRIAGE.map((t) => (
              <div key={t.level} className="rounded-2xl border border-line bg-white p-4">
                <TriageBadge level={t.level} />
                <p className="mt-2 text-2xl font-semibold text-ink-900 tabular-nums">{loading ? "—" : counts[t.level] ?? 0}</p>
                <p className="text-xs text-ink-500">Target {t.target}</p>
              </div>
            ))}
          </div>

          <Tabs
            value={activeTab}
            onChange={setActiveTab}
            label="ER sections"
            tabs={[
              { id: "active", label: "Active", count: activeVisits.length },
              { id: "completed", label: "Completed", count: completedVisits.length },
              { id: "triage", label: "Triage log", count: triaged.length },
            ]}
          />

          {loading ? (
            <Card><SkeletonRows rows={5} /></Card>
          ) : activeTab === "active" ? (
            <Card className="overflow-hidden">
              {activeVisits.length === 0 ? (
                <EmptyState icon={Ambulance} title="No active emergency visits" />
              ) : (
                <TableWrap>
                  <table className="hms-table">
                    <caption className="sr-only">Active emergency visits, highest triage priority first</caption>
                    <thead>
                      <tr>
                        <th scope="col">Triage</th>
                        <th scope="col">Patient</th>
                        <th scope="col">Arrived</th>
                        <th scope="col">Status</th>
                        <th scope="col">Doctor</th>
                        <th scope="col"><span className="sr-only">Actions</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeVisits.map((visit) => (
                        <tr key={visit.id} className={triageRank(visit.triage_level) <= 1 ? "[&>td:first-child]:border-l-4 [&>td:first-child]:border-l-red-500" : ""}>
                          <td><TriageBadge level={visit.triage_level} /></td>
                          <td>
                            <span className="block font-medium text-ink-900">{visit.patient_name}</span>
                            <span className="block text-xs text-ink-500 tabular-nums">
                              {visit.visit_number}
                              {visit.patient?.age ? ` · ${visit.patient.age} y` : ""}
                              {visit.patient?.gender ? ` · ${visit.patient.gender}` : ""}
                            </span>
                          </td>
                          <td className="whitespace-nowrap tabular-nums text-ink-600">{new Date(visit.arrival_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</td>
                          <td><StatusBadge status={visit.status} /></td>
                          <td className="whitespace-nowrap">{visit.attending_doctor_name || <span className="text-ink-400">—</span>}</td>
                          <td>
                            <div className="flex flex-wrap justify-end gap-1.5">
                              {(visit.status === "Registered" || visit.status === "Triage") && (
                                <Button size="sm" variant="subtle" icon={ClipboardPlus} onClick={() => open("triage", visit, { triage_level: visit.triage_level })}>Triage</Button>
                              )}
                              {visit.status === "Waiting" && (
                                <Button size="sm" variant="subtle" icon={Stethoscope} onClick={() => handleStartConsultation(visit)}>Start consult</Button>
                              )}
                              {IN_CARE.includes(visit.status) && (
                                <>
                                  <Button size="sm" variant="ghost" icon={HeartPulse} onClick={() => open("vitals", visit)}>Vitals</Button>
                                  <Button size="sm" variant="ghost" icon={ClipboardPlus} onClick={() => open("order", visit)}>Order</Button>
                                  <Button size="sm" variant="ghost" icon={Pill} onClick={() => open("medication", visit)}>Medicine</Button>
                                  <Button size="sm" variant="secondary" icon={Send} onClick={() => open("refer", visit)}>Refer</Button>
                                  <Button size="sm" variant="secondary" icon={LogOut} onClick={() => open("discharge", visit)}>Discharge</Button>
                                </>
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
          ) : activeTab === "completed" ? (
            <Card className="overflow-hidden">
              {completedVisits.length === 0 ? (
                <EmptyState icon={Ambulance} title="No completed visits yet" />
              ) : (
                <TableWrap>
                  <table className="hms-table">
                    <thead>
                      <tr>
                        <th scope="col">Visit</th>
                        <th scope="col">Patient</th>
                        <th scope="col">Outcome</th>
                        <th scope="col">Disposition</th>
                        <th scope="col">Arrived</th>
                        <th scope="col">Left</th>
                      </tr>
                    </thead>
                    <tbody>
                      {completedVisits.map((visit) => (
                        <tr key={visit.id}>
                          <td className="tabular-nums">{visit.visit_number}</td>
                          <td className="font-medium text-ink-900">{visit.patient_name}</td>
                          <td><StatusBadge status={visit.status} /></td>
                          <td className="text-ink-600">{visit.disposition || "—"}</td>
                          <td className="whitespace-nowrap tabular-nums text-ink-600">{new Date(visit.arrival_time).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</td>
                          <td className="whitespace-nowrap tabular-nums text-ink-600">{visit.discharge_time ? new Date(visit.discharge_time).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TableWrap>
              )}
            </Card>
          ) : (
            <Card className="overflow-hidden">
              {triaged.length === 0 ? (
                <EmptyState icon={ClipboardPlus} title="No triage records yet" />
              ) : (
                <TableWrap>
                  <table className="hms-table">
                    <thead>
                      <tr>
                        <th scope="col">Visit</th>
                        <th scope="col">Patient</th>
                        <th scope="col">Level</th>
                        <th scope="col">Chief complaint</th>
                        <th scope="col">Triaged</th>
                      </tr>
                    </thead>
                    <tbody>
                      {triaged.map((visit) => (
                        <tr key={visit.id}>
                          <td className="tabular-nums">{visit.visit_number}</td>
                          <td className="font-medium text-ink-900">{visit.patient_name}</td>
                          <td><TriageBadge level={visit.triage_level} /></td>
                          <td className="max-w-sm text-ink-700">{visit.triage?.chief_complaint || "—"}</td>
                          <td className="whitespace-nowrap tabular-nums text-ink-600">{visit.triage_time ? new Date(visit.triage_time).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TableWrap>
              )}
            </Card>
          )}
        </>
      )}

      <Modal open={dialog === "registration"} onClose={close} title="New emergency visit" footer={footer("er-reg", "Register visit")}>
        <form id="er-reg" onSubmit={handleRegistration} className="space-y-4">
          <Field label="Patient" required>
            <Select value={f.registration.patient} onChange={setForm("registration")("patient")}>
              <option value="">Select patient</option>
              {patients.map((p) => <option key={p.id} value={p.id}>{p.name}{p.age ? ` (${p.age} y` : ""}{p.gender ? `, ${p.gender})` : p.age ? ")" : ""}{p.phone ? ` · ${p.phone}` : ""}</option>)}
            </Select>
          </Field>
          <Field label="Initial triage level" required>
            <Select value={f.registration.triage_level} onChange={setForm("registration")("triage_level")}>{triageOptions}</Select>
          </Field>
          <Field label="Attending doctor">
            <Select value={f.registration.attending_doctor} onChange={setForm("registration")("attending_doctor")}>{doctorOptions}</Select>
          </Field>
          <Field label="Remarks"><Textarea rows={2} value={f.registration.remarks} onChange={setForm("registration")("remarks")} /></Field>
        </form>
      </Modal>

      <Modal open={dialog === "triage"} onClose={close} title="Triage" description={visitTitle} footer={footer("er-triage", "Complete triage")}>
        <form id="er-triage" onSubmit={handleCompleteTriage} className="space-y-4">
          <Field label="Chief complaint" required><Textarea value={f.triage.chief_complaint} onChange={setForm("triage")("chief_complaint")} /></Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Pain score" hint="0–10"><Input type="number" min="0" max="10" inputMode="numeric" value={f.triage.pain_score} onChange={setForm("triage")("pain_score")} /></Field>
            <Field label="Glasgow Coma Scale" hint="3–15"><Input type="number" min="3" max="15" inputMode="numeric" value={f.triage.glasgow_coma_scale} onChange={setForm("triage")("glasgow_coma_scale")} /></Field>
          </div>
          <Field label="Triage level" required><Select value={f.triage.triage_level} onChange={setForm("triage")("triage_level")}>{triageOptions}</Select></Field>
          <Field label="Triaged by"><Select value={f.triage.triaged_by} onChange={setForm("triage")("triaged_by")}>{nurseOptions}</Select></Field>
          <Field label="Triage notes"><Textarea value={f.triage.triage_notes} onChange={setForm("triage")("triage_notes")} /></Field>
        </form>
      </Modal>

      <Modal open={dialog === "vitals"} onClose={close} title="Record vitals" description={visitTitle} footer={footer("er-vitals", "Save vitals")}>
        <form id="er-vitals" onSubmit={handleAddVitals} className="grid grid-cols-2 gap-4">
          <Field label="Systolic BP (mmHg)"><Input type="number" inputMode="numeric" value={f.vitals.systolic_bp} onChange={setForm("vitals")("systolic_bp")} /></Field>
          <Field label="Diastolic BP (mmHg)"><Input type="number" inputMode="numeric" value={f.vitals.diastolic_bp} onChange={setForm("vitals")("diastolic_bp")} /></Field>
          <Field label="Heart rate (bpm)"><Input type="number" inputMode="numeric" value={f.vitals.heart_rate} onChange={setForm("vitals")("heart_rate")} /></Field>
          <Field label="SpO₂ (%)"><Input type="number" min="0" max="100" inputMode="numeric" value={f.vitals.spo2} onChange={setForm("vitals")("spo2")} /></Field>
          <Field label="Resp. rate (/min)"><Input type="number" inputMode="numeric" value={f.vitals.respiratory_rate} onChange={setForm("vitals")("respiratory_rate")} /></Field>
          <Field label="Temperature (°C)"><Input type="number" step="0.1" inputMode="decimal" value={f.vitals.temperature} onChange={setForm("vitals")("temperature")} /></Field>
          <Field label="Blood sugar (mg/dL)"><Input type="number" step="0.1" inputMode="decimal" value={f.vitals.blood_sugar} onChange={setForm("vitals")("blood_sugar")} /></Field>
          <Field label="Recorded by"><Select value={f.vitals.recorded_by} onChange={setForm("vitals")("recorded_by")}>{nurseOptions}</Select></Field>
        </form>
      </Modal>

      <Modal open={dialog === "order"} onClose={close} title="Add order" description={visitTitle} footer={footer("er-order", "Add order")}>
        <form id="er-order" onSubmit={handleAddOrder} className="space-y-4">
          <Field label="Order type" required>
            <Select value={f.order.order_type} onChange={setForm("order")("order_type")}>
              <option value="Lab">Lab investigation</option>
              <option value="Imaging">Imaging</option>
              <option value="Medication">Medication</option>
              <option value="Procedure">Procedure</option>
              <option value="Consultation">Specialist consultation</option>
            </Select>
          </Field>
          <Field label="Description" required><Textarea value={f.order.description} onChange={setForm("order")("description")} /></Field>
          <Field label="Ordered by"><Select value={f.order.ordered_by} onChange={setForm("order")("ordered_by")}>{doctorOptions}</Select></Field>
        </form>
      </Modal>

      <Modal open={dialog === "medication"} onClose={close} title="Prescribe medicine" description={visitTitle} footer={footer("er-med", "Prescribe")}>
        <form id="er-med" onSubmit={handleAddMedication} className="grid grid-cols-2 gap-4">
          <Field label="Medicine" required className="col-span-2"><Input value={f.medication.name} onChange={setForm("medication")("name")} /></Field>
          <Field label="Dose" required><Input value={f.medication.dose} onChange={setForm("medication")("dose")} /></Field>
          <Field label="Route" required>
            <Select value={f.medication.route} onChange={setForm("medication")("route")}>
              {["IV", "IM", "PO", "SC", "PR"].map((r) => <option key={r}>{r}</option>)}
            </Select>
          </Field>
          <Field label="Frequency" required hint="e.g. Q8H, BID"><Input value={f.medication.frequency} onChange={setForm("medication")("frequency")} /></Field>
          <Field label="Duration" hint="e.g. 5 days"><Input value={f.medication.duration} onChange={setForm("medication")("duration")} /></Field>
          <Field label="Prescribed by" className="col-span-2"><Select value={f.medication.prescribed_by} onChange={setForm("medication")("prescribed_by")}>{doctorOptions}</Select></Field>
        </form>
      </Modal>

      <Modal open={dialog === "discharge"} onClose={close} title="Discharge from ER" description={visitTitle} footer={footer("er-discharge", "Discharge patient")}>
        <form id="er-discharge" onSubmit={handleDischarge} className="space-y-4">
          <Field label="Discharge diagnosis" required><Textarea value={f.discharge.discharge_diagnosis} onChange={setForm("discharge")("discharge_diagnosis")} /></Field>
          <Field label="Follow-up instructions"><Textarea value={f.discharge.follow_up_instructions} onChange={setForm("discharge")("follow_up_instructions")} /></Field>
        </form>
      </Modal>

      <Modal open={dialog === "refer"} onClose={close} title="Refer to another facility" description={visitTitle} footer={footer("er-refer", "Refer patient")}>
        <form id="er-refer" onSubmit={handleRefer} className="space-y-4">
          <Field label="Referred to (facility)" required><Input value={f.refer.referred_to} onChange={setForm("refer")("referred_to")} /></Field>
          <Field label="Diagnosis at referral"><Textarea value={f.refer.discharge_diagnosis} onChange={setForm("refer")("discharge_diagnosis")} /></Field>
        </form>
      </Modal>
    </div>
  )
}

export default Emergency
