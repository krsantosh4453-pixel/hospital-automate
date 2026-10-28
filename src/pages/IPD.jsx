import { useState, useEffect, useCallback } from "react"
import { BedDouble, BedSingle, ClipboardCheck, FileSignature, Hospital, LogOut, Plus, RefreshCw, UserRoundCheck } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import api from "../services/api"
import { useToast } from "../components/Toast.jsx"
import AddBedDialog from "../components/ipd/AddBedDialog.jsx"
import BedsTable from "../components/ipd/BedsTable.jsx"
import DischargeReadiness from "../components/ipd/DischargeReadiness.jsx"
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  Field,
  Modal,
  PageHeader,
  Select,
  SkeletonRows,
  StatTile,
  StatusBadge,
  TableWrap,
  Tabs,
  Textarea,
  useConfirm,
} from "../components/ui"

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
// Wards, rooms and beds are set up by the hospital's Admin or Manager.
const BED_MANAGER_ROLES = ["Admin", "Hospital Manager"]
const bedLabel = (bed) => (bed ? [bed.ward_name, bed.room_number, bed.bed_number].filter(Boolean).join(" · ") : "")

function IPD() {
  // Doctors admit; a Hospital Manager only views admissions.
  const { canAdd, activeRoleName } = useRole()
  const canManageBeds = BED_MANAGER_ROLES.includes(activeRoleName)
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()
  const { selectedHospital } = usePatient()

  const [admissions, setAdmissions] = useState([])
  const [summaries, setSummaries] = useState([])
  // Server-side discharge readiness per admission id (checklist + final bill).
  const [readiness, setReadiness] = useState({})
  const [readinessToken, setReadinessToken] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState("admissions")
  const [availableBeds, setAvailableBeds] = useState([])
  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])
  const [busy, setBusy] = useState("")
  // Bumped after IPD data reloads so the All beds tab reloads too.
  const [bedsVersion, setBedsVersion] = useState(0)

  const [dialog, setDialog] = useState(null) // "admission" | "bed" | "add-bed" | "plan" | "summary"
  const [selectedAdmission, setSelectedAdmission] = useState(null)
  const [admissionForm, setAdmissionForm] = useState({ patient: "", reason: "", admitting_doctor: "" })
  const [bedId, setBedId] = useState("")
  const [planForm, setPlanForm] = useState({ instructions: "", pending_tasks: "" })
  const [summaryText, setSummaryText] = useState("")

  const fetchData = useCallback(async () => {
    if (!selectedHospital) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const [admissionsRes, patientsRes, doctorsRes] = await Promise.all([
        api.ipd.admissions.list(selectedHospital.id),
        api.patients.list(selectedHospital.id),
        api.doctors.list(selectedHospital.id),
      ])
      setAdmissions(list(admissionsRes))
      setPatients(list(patientsRes))
      setDoctors(list(doctorsRes))

      const [bedsRes, summariesRes] = await Promise.allSettled([
        api.ipd.bedAllocations.availableBeds(selectedHospital.id),
        api.ipd.dischargeSummaries.list(selectedHospital.id),
      ])
      setAvailableBeds(bedsRes.status === "fulfilled" ? list(bedsRes.value) : [])
      // Only doctors may read summaries; other roles simply see no summary data.
      setSummaries(summariesRes.status === "fulfilled" ? list(summariesRes.value) : [])
    } catch (err) {
      setError(err.message || "Failed to load IPD data")
    } finally {
      setLoading(false)
      // Payments and checklist changes happen elsewhere; re-read readiness too.
      setReadinessToken((n) => n + 1)
    }
  }, [selectedHospital])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const closeDialog = () => {
    setDialog(null)
    setSelectedAdmission(null)
    setAdmissionForm({ patient: "", reason: "", admitting_doctor: "" })
    setBedId("")
    setPlanForm({ instructions: "", pending_tasks: "" })
    setSummaryText("")
  }

  const run = async (key, fn) => {
    setBusy(key)
    try {
      await fn()
    } finally {
      setBusy("")
    }
  }

  const handleAdmissionSubmit = (e) => {
    e.preventDefault()
    if (!selectedHospital) return toast.warning("Please select a hospital first.")
    return run("admission", async () => {
      try {
        const data = await api.ipd.admissions.create({
          // Ids, not names: two patients can share a name.
          patient: Number(admissionForm.patient),
          hospital: selectedHospital.id,
          reason: admissionForm.reason,
          admitting_doctor: admissionForm.admitting_doctor ? Number(admissionForm.admitting_doctor) : null,
        })
        setAdmissions((prev) => [data, ...prev])
        closeDialog()
        toast.success("Admission created")
      } catch (err) {
        toast.error(err.message || "Failed to create admission")
      }
    })
  }

  const handleBedAllocation = (e) => {
    e.preventDefault()
    if (!selectedAdmission) return undefined
    return run("bed", async () => {
      try {
        await api.ipd.admissions.allocateBed(selectedAdmission.id, bedId)
        toast.success("Bed allocated")
        closeDialog()
        fetchData()
      } catch (err) {
        toast.error(err.message || "Failed to allocate bed")
      }
    })
  }

  const handleReleaseBed = async (admission) => {
    if (!(await confirm({ title: "Release bed?", message: `Release ${bedLabel(admission.current_bed)} held by ${admission.patient_name}?`, confirmLabel: "Release bed" }))) return
    await run(`release-${admission.id}`, async () => {
      try {
        await api.ipd.admissions.releaseBed(admission.id)
        toast.success("Bed released")
        fetchData()
      } catch (err) {
        toast.error(err.message || "Failed to release bed")
      }
    })
  }

  const handleDischargePlanSubmit = (e) => {
    e.preventDefault()
    return run("plan", async () => {
      try {
        await api.ipd.dischargePlans.create({
          admission: selectedAdmission.id,
          instructions: planForm.instructions,
          pending_tasks: planForm.pending_tasks,
        })
        await api.ipd.admissions.initiateDischarge(selectedAdmission.id)
        toast.success("Discharge started. Write and finalize the discharge summary next.")
        closeDialog()
        setActiveTab("discharges")
        fetchData()
      } catch (err) {
        toast.error(err.message || "Failed to initiate discharge")
      }
    })
  }

  const summaryFor = (admission) => summaries.find((s) => String(s.admission) === String(admission.id))

  const handleSummarySubmit = (e) => {
    e.preventDefault()
    const existing = summaryFor(selectedAdmission)
    return run("summary", async () => {
      try {
        if (existing) await api.ipd.dischargeSummaries.update(existing.id, { summary: summaryText })
        else await api.ipd.dischargeSummaries.create({ admission: selectedAdmission.id, summary: summaryText })
        toast.success("Discharge summary saved as a draft")
        closeDialog()
        fetchData()
      } catch (err) {
        toast.error(err.message || "Failed to save discharge summary")
      }
    })
  }

  const handleFinalize = async (admission, summary) => {
    const ok = await confirm({
      title: "Finalize discharge summary?",
      message: `You are signing the discharge summary for ${admission.patient_name}. After finalizing it cannot be edited; later information is added as discharge notes.`,
      confirmLabel: "Finalize and sign",
      destructive: false,
    })
    if (!ok) return
    await run(`finalize-${admission.id}`, async () => {
      try {
        await api.ipd.dischargeSummaries.finalize(summary.id)
        toast.success("Discharge summary finalized")
        fetchData()
      } catch (err) {
        toast.error(err.message || "Failed to finalize the summary")
      }
    })
  }

  const handleCompleteDischarge = async (admission) => {
    if (!(await confirm({ title: "Complete discharge?", message: `Complete the discharge of ${admission.patient_name}? This releases their bed.`, confirmLabel: "Complete discharge" }))) return
    await run(`complete-${admission.id}`, async () => {
      try {
        await api.ipd.admissions.completeDischarge(admission.id)
        toast.success("Discharge completed and bed released")
        fetchData()
      } catch (err) {
        toast.error(err.message || "Failed to complete discharge")
        setReadinessToken((n) => n + 1)
      }
    })
  }

  const header = (
    <PageHeader
      title="Inpatients (IPD)"
      description={selectedHospital ? `Admissions, beds and discharges at ${selectedHospital.name}.` : undefined}
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "IPD" }]}
      actions={
        selectedHospital && (
          <>
            <Button variant="secondary" icon={RefreshCw} onClick={fetchData} disabled={loading}>Refresh</Button>
            {canManageBeds && <Button variant="secondary" icon={BedSingle} onClick={() => { closeDialog(); setDialog("add-bed") }}>Add bed</Button>}
            {canAdd("IPD") && <Button icon={Plus} onClick={() => { closeDialog(); setDialog("admission") }}>New admission</Button>}
          </>
        )
      }
    />
  )

  if (!selectedHospital) {
    return (
      <>{confirmDialog}<div className="space-y-5">
        {header}
        <Card><EmptyState icon={Hospital} title="Select a hospital" description="Choose a hospital in the header to manage inpatients." /></Card>
      </div></>
    )
  }

  const admitted = admissions.filter((a) => a.status === "Admitted")
  const discharging = admissions.filter((a) => a.status === "Discharge Initiated")

  return (
    <>{confirmDialog}<div className="space-y-5">
      {header}

      {error ? (
        <Card><ErrorState title="IPD data could not be loaded" message={error} onRetry={fetchData} /></Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatTile icon={UserRoundCheck} label="Currently admitted" value={loading ? null : admitted.length} onClick={() => setActiveTab("admissions")} />
            <StatTile icon={LogOut} tone="warning" label="Discharge in progress" value={loading ? null : discharging.length} onClick={() => setActiveTab("discharges")} />
            <StatTile icon={BedDouble} tone="success" label="Beds available" value={loading ? null : availableBeds.length} onClick={() => setActiveTab("beds")} />
          </div>

          <Tabs
            value={activeTab}
            onChange={setActiveTab}
            label="IPD sections"
            tabs={[
              { id: "admissions", label: "Admissions", icon: UserRoundCheck, count: admissions.length },
              { id: "beds", label: "Available beds", icon: BedSingle, count: availableBeds.length },
              { id: "all-beds", label: "All beds", icon: BedDouble },
              { id: "discharges", label: "Discharges", icon: ClipboardCheck, count: discharging.length },
            ]}
          />

          {activeTab === "all-beds" ? (
            <Card className="overflow-hidden">
              <BedsTable hospitalId={selectedHospital?.id} canManage={canManageBeds} refreshKey={bedsVersion} onChanged={fetchData} />
            </Card>
          ) : loading ? (
            <Card><SkeletonRows rows={5} /></Card>
          ) : activeTab === "admissions" ? (
            <Card className="overflow-hidden">
              {admissions.length === 0 ? (
                <EmptyState icon={BedDouble} title="No admissions yet" action={canAdd("IPD") && <Button icon={Plus} onClick={() => setDialog("admission")}>New admission</Button>} />
              ) : (
                <TableWrap>
                  <table className="hms-table">
                    <caption className="sr-only">Admissions</caption>
                    <thead>
                      <tr>
                        <th scope="col">Patient</th>
                        <th scope="col">Admitted</th>
                        <th scope="col">Doctor</th>
                        <th scope="col">Reason</th>
                        <th scope="col">Bed</th>
                        <th scope="col">Status</th>
                        <th scope="col"><span className="sr-only">Actions</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {admissions.map((admission) => (
                        <tr key={admission.id}>
                          <td>
                            <span className="block font-medium text-ink-900">{admission.patient_name}</span>
                            <span className="block text-xs text-ink-500 tabular-nums">Admission #{admission.id}</span>
                          </td>
                          <td className="whitespace-nowrap text-ink-600 tabular-nums">{new Date(admission.admission_date).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</td>
                          <td className="whitespace-nowrap">{admission.admitting_doctor_name || <span className="text-ink-400">—</span>}</td>
                          <td className="max-w-[14rem] truncate text-ink-600">{admission.reason || "—"}</td>
                          <td className="whitespace-nowrap">{admission.current_bed ? bedLabel(admission.current_bed) : <Badge tone="warning">No bed</Badge>}</td>
                          <td><StatusBadge status={admission.status} /></td>
                          <td>
                            <div className="flex flex-wrap justify-end gap-1.5">
                              {!admission.current_bed && admission.status === "Admitted" && (
                                <Button size="sm" variant="subtle" icon={BedSingle} onClick={() => { setSelectedAdmission(admission); setBedId(""); setDialog("bed") }}>Allocate bed</Button>
                              )}
                              {admission.current_bed && (
                                <Button size="sm" variant="ghost" loading={busy === `release-${admission.id}`} onClick={() => handleReleaseBed(admission)}>Release bed</Button>
                              )}
                              {admission.status === "Admitted" && (
                                <Button size="sm" variant="secondary" icon={LogOut} onClick={() => { setSelectedAdmission(admission); setDialog("plan") }}>Start discharge</Button>
                              )}
                              {admission.status === "Discharge Initiated" && (
                                <Button size="sm" variant="secondary" onClick={() => setActiveTab("discharges")}>Discharge steps</Button>
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
          ) : activeTab === "beds" ? (
            <Card className="overflow-hidden">
              {availableBeds.length === 0 ? (
                <EmptyState
                  icon={BedSingle}
                  title="No beds available"
                  description="Every bed is occupied or under maintenance."
                  action={canManageBeds && <Button icon={Plus} onClick={() => setDialog("add-bed")}>Add bed</Button>}
                />
              ) : (
                <TableWrap>
                  <table className="hms-table">
                    <caption className="sr-only">Available beds</caption>
                    <thead>
                      <tr>
                        <th scope="col">Ward</th>
                        <th scope="col">Room</th>
                        <th scope="col">Bed</th>
                        <th scope="col">Room type</th>
                        <th scope="col">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {availableBeds.map((bed) => (
                        <tr key={bed.id}>
                          <td>{bed.ward}</td>
                          <td>{bed.room}</td>
                          <td className="font-semibold text-ink-900 tabular-nums">{bed.bed_number}</td>
                          <td className="text-ink-600">{bed.room_type || "—"}</td>
                          <td><StatusBadge status="Available" /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TableWrap>
              )}
            </Card>
          ) : (
            <Card>
              <CardHeader
                title="Discharges in progress"
                description="A discharge completes once the checklist is ticked, the doctor has signed the summary and the final bill is paid."
              />
              {discharging.length === 0 ? (
                <EmptyState compact icon={ClipboardCheck} title="No discharges in progress" />
              ) : (
                <ul className="divide-y divide-line">
                  {discharging.map((admission) => {
                    const summary = summaryFor(admission)
                    const steps = [
                      { label: "Discharge started", done: true },
                      { label: summary ? "Summary written" : "Write summary", done: Boolean(summary) },
                      { label: summary?.finalized ? `Signed by ${summary.authorized_doctor_name || "doctor"}` : "Doctor signs summary", done: Boolean(summary?.finalized) },
                      { label: "Complete discharge", done: false },
                    ]
                    return (
                      <li key={admission.id} className="flex flex-col gap-4 px-5 py-4 lg:flex-row lg:flex-wrap lg:items-center">
                        <div className="min-w-0 lg:w-64">
                          <p className="font-medium text-ink-900">{admission.patient_name}</p>
                          <p className="text-xs text-ink-500">{admission.current_bed ? bedLabel(admission.current_bed) : "No bed"} · admitted {new Date(admission.admission_date).toLocaleDateString("en-IN")}</p>
                        </div>
                        <ol className="flex flex-1 flex-wrap items-center gap-x-4 gap-y-2 text-[13px]" aria-label="Discharge steps">
                          {steps.map((step, i) => (
                            <li key={step.label} className={`flex items-center gap-1.5 ${step.done ? "text-green-700" : "text-ink-500"}`}>
                              <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold ${step.done ? "bg-green-100" : "bg-ink-100"}`} aria-hidden="true">{i + 1}</span>
                              {step.label}
                              <span className="sr-only">{step.done ? "(done)" : "(to do)"}</span>
                            </li>
                          ))}
                        </ol>
                        <div className="flex flex-wrap gap-1.5">
                          {!summary?.finalized && (
                            <Button size="sm" variant="secondary" icon={FileSignature} onClick={() => { setSelectedAdmission(admission); setSummaryText(summary?.summary || ""); setDialog("summary") }}>
                              {summary ? "Edit summary" : "Write summary"}
                            </Button>
                          )}
                          {summary && !summary.finalized && (
                            <Button size="sm" variant="subtle" loading={busy === `finalize-${admission.id}`} onClick={() => handleFinalize(admission, summary)}>Finalize</Button>
                          )}
                          <Button
                            size="sm"
                            loading={busy === `complete-${admission.id}`}
                            disabled={!readiness[admission.id]?.ready}
                            title={readiness[admission.id]?.ready ? undefined : (readiness[admission.id]?.blockers || []).join(" ")}
                            onClick={() => handleCompleteDischarge(admission)}
                          >
                            Complete discharge
                          </Button>
                        </div>
                        <div className="w-full border-t border-line pt-3">
                          <DischargeReadiness
                            admissionId={admission.id}
                            reloadToken={`${readinessToken}-${summary?.finalized}`}
                            canTick={activeRoleName === "Doctor" || activeRoleName === "Nurse" || activeRoleName === "Admin"}
                            onChange={(state) => setReadiness((prev) => ({ ...prev, [admission.id]: state }))}
                          />
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </Card>
          )}
        </>
      )}

      {/* New admission */}
      <AddBedDialog
        open={dialog === "add-bed"}
        onClose={closeDialog}
        hospitalId={selectedHospital?.id}
        onAdded={(bed) => {
          toast.success(bed.status === "Available" ? `Bed ${bed.bed_number} added` : `Bed ${bed.bed_number} added as ${bed.status}`)
          setActiveTab("all-beds")
          setBedsVersion((v) => v + 1)
          fetchData()
        }}
      />

      <Modal
        open={dialog === "admission"}
        onClose={closeDialog}
        title="New admission"
        footer={<><Button variant="secondary" onClick={closeDialog}>Cancel</Button><Button type="submit" form="ipd-admission" loading={busy === "admission"}>Admit patient</Button></>}
      >
        <form id="ipd-admission" onSubmit={handleAdmissionSubmit} className="space-y-4">
          <Field label="Patient" required>
            <Select value={admissionForm.patient} onChange={(e) => setAdmissionForm({ ...admissionForm, patient: e.target.value })}>
              <option value="">Select patient</option>
              {patients.map((p) => <option key={p.id} value={p.id}>{p.name}{p.age ? ` (${p.age} y)` : ""}{p.phone ? ` · ${p.phone}` : ""}</option>)}
            </Select>
          </Field>
          <Field label="Admitting doctor">
            <Select value={admissionForm.admitting_doctor} onChange={(e) => setAdmissionForm({ ...admissionForm, admitting_doctor: e.target.value })}>
              <option value="">Not specified</option>
              {doctors.map((d) => <option key={d.id} value={d.id}>{d.name}{d.specialization ? ` — ${d.specialization}` : ""}</option>)}
            </Select>
          </Field>
          <Field label="Reason for admission">
            <Textarea value={admissionForm.reason} onChange={(e) => setAdmissionForm({ ...admissionForm, reason: e.target.value })} />
          </Field>
        </form>
      </Modal>

      {/* Allocate bed */}
      <Modal
        open={dialog === "bed"}
        onClose={closeDialog}
        size="sm"
        title="Allocate bed"
        description={selectedAdmission?.patient_name}
        footer={<><Button variant="secondary" onClick={closeDialog}>Cancel</Button><Button type="submit" form="ipd-bed" loading={busy === "bed"} disabled={availableBeds.length === 0}>Allocate</Button></>}
      >
        <form id="ipd-bed" onSubmit={handleBedAllocation} className="space-y-4">
          {availableBeds.length === 0 ? (
            <Alert tone="warning">No beds are available right now.</Alert>
          ) : (
            <Field label="Available bed" required>
              <Select value={bedId} onChange={(e) => setBedId(e.target.value)}>
                <option value="">Select bed</option>
                {availableBeds.map((bed) => <option key={bed.id} value={bed.id}>{bed.ward} · {bed.room} · Bed {bed.bed_number}{bed.room_type ? ` (${bed.room_type})` : ""}</option>)}
              </Select>
            </Field>
          )}
        </form>
      </Modal>

      {/* Start discharge */}
      <Modal
        open={dialog === "plan"}
        onClose={closeDialog}
        title="Start discharge"
        description={selectedAdmission?.patient_name}
        footer={<><Button variant="secondary" onClick={closeDialog}>Cancel</Button><Button type="submit" form="ipd-plan" loading={busy === "plan"}>Start discharge</Button></>}
      >
        <form id="ipd-plan" onSubmit={handleDischargePlanSubmit} className="space-y-4">
          <Field label="Discharge instructions"><Textarea value={planForm.instructions} onChange={(e) => setPlanForm({ ...planForm, instructions: e.target.value })} /></Field>
          <Field label="Pending tasks before discharge"><Textarea value={planForm.pending_tasks} onChange={(e) => setPlanForm({ ...planForm, pending_tasks: e.target.value })} /></Field>
        </form>
      </Modal>

      {/* Discharge summary */}
      <Modal
        open={dialog === "summary"}
        onClose={closeDialog}
        size="lg"
        title="Discharge summary"
        description={`${selectedAdmission?.patient_name || ""} — saved as a draft; the patient's doctor finalizes it.`}
        footer={<><Button variant="secondary" onClick={closeDialog}>Cancel</Button><Button type="submit" form="ipd-summary" loading={busy === "summary"}>Save draft</Button></>}
      >
        <form id="ipd-summary" onSubmit={handleSummarySubmit}>
          <Field label="Clinical summary" required hint="Diagnosis, course in hospital, condition at discharge, medicines and follow-up.">
            <Textarea rows={10} value={summaryText} onChange={(e) => setSummaryText(e.target.value)} />
          </Field>
        </form>
      </Modal>
    </div></>
  )
}

export default IPD
