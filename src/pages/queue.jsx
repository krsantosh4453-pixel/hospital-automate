import { useEffect, useState } from "react"
import { CircleCheck, Hospital, ListOrdered, Megaphone, PhoneCall, SkipForward, Stethoscope, Ticket } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useAppointment } from "../assets/context/AppointmentContext.jsx"
import api from "../services/api.js"
import {
  Alert,
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  SearchInput,
  Select,
  SkeletonRows,
  StatTile,
  StatusBadge,
  TableWrap,
  Tabs,
  Toolbar,
} from "../components/ui"

const QUEUE_STATUSES = ["Waiting", "In Consultation", "Completed", "Skipped"]

function Queue() {
  const { selectedHospital } = usePatient()
  const { appointments: appointmentList, updateAppointment } = useAppointment()

  // Live queue records from Django (encounters.QueueToken).
  const [queue, setQueue] = useState([])

  const [departmentFilter, setDepartmentFilter] = useState("All Departments")
  const [statusFilter, setStatusFilter] = useState("All Status")
  const [search, setSearch] = useState("")

  // API state (loading / error / retry / feedback)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [offlineMode, setOfflineMode] = useState(false)
  const [actionError, setActionError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const [reloadToken, setReloadToken] = useState(0)
  const [busy, setBusy] = useState("")

  // =====================================
  // DJANGO QUEUETOKEN → QUEUE ROW
  // =====================================

  const mapQueueFromApi = (record) => ({
    token: record.token_number,
    patient: record.patient_name || "Patient",
    village: "",
    contact: record.patient_phone || "",
    doctor: record.doctor_name || "",
    department: record.department || "General",
    type: record.visit_type || "OPD",
    waiting: String(record.status || "").toLowerCase() === "waiting" ? `${record.waiting_minutes ?? 0} min` : "Now",
    status: record.status || "Waiting",
    hospitalId: record.hospital,
    appointmentId: record.appointment ? `A${String(record.appointment).padStart(3, "0")}` : undefined,
    appointmentApiId: record.appointment,
    apiId: record.id,
  })

  // =====================================
  // LOAD QUEUE FROM DJANGO
  // =====================================

  useEffect(() => {
    let cancelled = false

    const loadQueue = async () => {
      if (!selectedHospital) return
      setLoading(true)
      setLoadError("")
      try {
        const data = await api.queue.list(selectedHospital.id)
        if (cancelled) return
        const records = Array.isArray(data) ? data : data?.results || []
        setQueue(records.map(mapQueueFromApi))
        setOfflineMode(false)
      } catch (error) {
        if (cancelled) return
        // Keep existing rows visible and fall back to offline behaviour.
        setLoadError(error.message || "Failed to load the queue.")
        setOfflineMode(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadQueue()
    return () => {
      cancelled = true
    }
  }, [selectedHospital, reloadToken])

  // =====================================
  // GENERATE TOKEN (Appointment → Visit → QueueToken)
  // =====================================

  // Appointments that are ready to be issued a queue token but do not have
  // one yet (API-backed only, i.e. they carry a real backend id).
  const issueableAppointments = (appointmentList || []).filter(
    (appointment) =>
      appointment.apiId &&
      String(appointment.hospitalId) === String(selectedHospital?.id) &&
      appointment.status !== "Cancelled" &&
      appointment.status !== "Completed" &&
      !queue.some((item) => String(item.appointmentApiId) === String(appointment.apiId)),
  )

  const generateToken = async () => {
    setActionError("")
    setSuccessMessage("")

    if (offlineMode) {
      setActionError("Cannot generate tokens while offline.")
      return
    }
    if (issueableAppointments.length === 0) {
      setActionError("No booked appointment is waiting for a token.")
      return
    }

    const nextAppointment = issueableAppointments[0]
    setBusy("generate")
    try {
      // One server-side call: Appointment → (reused/created) Visit →
      // QueueToken with a token_number allocated by Django.
      const token = await api.queue.issue(nextAppointment.apiId)
      setSuccessMessage(`Token #${token.token_number} generated for ${nextAppointment.patient || "patient"}.`)
      setReloadToken((value) => value + 1)
    } catch (error) {
      setActionError(error.message || "Failed to generate a token.")
    } finally {
      setBusy("")
    }
  }

  // =====================================
  // APPOINTMENTS → QUEUE
  // =====================================

  const appointmentQueue = appointmentList
    .filter((appointment) => appointment.status !== "Cancelled" && appointment.status !== "Completed")
    .map((appointment) => {
      let queueStatus = "Waiting"
      if (appointment.status === "In Consultation") queueStatus = "In Consultation"
      if (appointment.status === "Skipped") queueStatus = "Skipped"

      return {
        token: appointment.tokenNumber || appointment.id,
        patient: appointment.patient || appointment.patientName || "Patient",
        village: appointment.village || "",
        contact: appointment.contact || "",
        doctor: appointment.doctor || "",
        department: appointment.department || appointment.reason || "General",
        type: "Appointment",
        waiting: queueStatus === "Waiting" ? "Waiting" : "Now",
        status: queueStatus,
        hospitalId: appointment.hospitalId,
        appointmentId: appointment.id,
      }
    })

  // Combine server queue + appointment queue
  const allQueue = [
    ...queue,
    ...appointmentQueue.filter(
      (appointmentItem) =>
        !queue.some(
          (queueItem) =>
            String(queueItem.token) === String(appointmentItem.token) &&
            String(queueItem.hospitalId) === String(appointmentItem.hospitalId),
        ),
    ),
  ]

  const hospitalQueue = selectedHospital
    ? allQueue.filter((item) => String(item.hospitalId) === String(selectedHospital.id))
    : []

  // Departments actually present in this queue.
  const departments = Array.from(new Set(hospitalQueue.map((i) => i.department).filter(Boolean))).sort()

  const baseFiltered = hospitalQueue.filter((item) => {
    const searchText = search.toLowerCase()
    const matchesSearch =
      String(item.patient || "").toLowerCase().includes(searchText) ||
      String(item.doctor || "").toLowerCase().includes(searchText) ||
      String(item.token || "").toLowerCase().includes(searchText)
    const matchesDepartment = departmentFilter === "All Departments" || item.department === departmentFilter
    return matchesSearch && matchesDepartment
  })
  const filteredQueue = baseFiltered.filter((item) => statusFilter === "All Status" || item.status === statusFilter)

  // Statistics
  const countOf = (status) => hospitalQueue.filter((item) => item.status === status).length
  const waitingCount = countOf("Waiting")
  const consultationCount = countOf("In Consultation")
  const completedCount = countOf("Completed")
  const skippedCount = countOf("Skipped")

  const currentPatient = hospitalQueue.find((item) => item.status === "In Consultation")
  const nextWaiting = hospitalQueue.find((item) => item.status === "Waiting")

  // =====================================
  // UPDATE APPOINTMENT STATUS
  // =====================================

  const updateRelatedAppointment = (queueItem, status) => {
    // Keep the shared AppointmentContext in sync (existing behaviour).
    if (queueItem.appointmentId) updateAppointment(queueItem.appointmentId, { status })

    // Also persist the status on the Django appointment when the queue row
    // is backed by a real record. Failures here are non-fatal: the queue
    // itself (QueueToken) is the source of truth for this page.
    if (queueItem.appointmentApiId) {
      api.appointments.patch(queueItem.appointmentApiId, { status }).catch(() => {})
    }
  }

  const setLocalStatus = (token, patch) =>
    setQueue((prevQueue) =>
      prevQueue.map((item) =>
        String(item.token) === String(token) && String(item.hospitalId) === String(selectedHospital.id) ? { ...item, ...patch } : item,
      ),
    )

  // =====================================
  // CALL NEXT PATIENT
  // =====================================

  const callNextPatient = async () => {
    const nextPatient = hospitalQueue.find((item) => item.status === "Waiting")
    if (!nextPatient) {
      setActionError("No patient is waiting in the queue.")
      return
    }

    setActionError("")
    setSuccessMessage("")
    setBusy("next")

    // Ask Django to advance the queue (completes the token currently being
    // served and calls the next waiting token, persisted server-side).
    if (!offlineMode) {
      try {
        await api.queue.callNext(selectedHospital.id)
        setSuccessMessage(`Called token #${nextPatient.token}.`)
      } catch (error) {
        setActionError(error.message || "Failed to call the next patient.")
      }
    }

    setLocalStatus(nextPatient.token, { status: "In Consultation", waiting: "Now" })
    updateRelatedAppointment(nextPatient, "In Consultation")
    setBusy("")
    setReloadToken((value) => value + 1)
  }

  // Shared handler for per-row call / complete / skip.
  const rowAction = async (token, kind) => {
    const config = {
      call: { apiCall: api.queue.call, status: "In Consultation", patch: { status: "In Consultation", waiting: "Now" }, done: "called", fail: "Failed to call this patient." },
      complete: { apiCall: api.queue.complete, status: "Completed", patch: { status: "Completed" }, done: "completed", fail: "Failed to complete this patient." },
      skip: { apiCall: api.queue.skip, status: "Skipped", patch: { status: "Skipped" }, done: "skipped", fail: "Failed to skip this patient." },
    }[kind]

    const selectedQueuePatient = hospitalQueue.find((item) => String(item.token) === String(token))
    setActionError("")
    setSuccessMessage("")
    setBusy(`${kind}-${token}`)

    // Persist on the QueueToken when this row is a real API record.
    if (selectedQueuePatient && selectedQueuePatient.apiId && !offlineMode) {
      try {
        await config.apiCall(selectedQueuePatient.apiId)
        setSuccessMessage(`Token #${token} ${config.done}.`)
      } catch (error) {
        setActionError(error.message || config.fail)
      }
    }

    setLocalStatus(token, config.patch)
    if (selectedQueuePatient) updateRelatedAppointment(selectedQueuePatient, config.status)
    setBusy("")
    setReloadToken((value) => value + 1)
  }

  if (!selectedHospital) {
    return (
      <div className="space-y-5">
        <PageHeader title="Queue" breadcrumbs={[{ label: "Home", to: "/" }, { label: "Queue" }]} />
        <Card>
          <EmptyState icon={Hospital} title="Select a hospital" description="Choose a hospital in the header to see its patient queue." />
        </Card>
      </div>
    )
  }

  const statusTabs = [
    { id: "All Status", label: "All", count: baseFiltered.length },
    ...QUEUE_STATUSES.map((s) => ({ id: s, label: s, count: baseFiltered.filter((i) => i.status === s).length })),
  ]

  return (
    <div className="space-y-5">
      <PageHeader
        title="OPD queue"
        description={`Tokens and consultation flow at ${selectedHospital.name}.`}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Queue" }]}
        actions={
          <>
            <Button
              variant="secondary"
              icon={Ticket}
              onClick={generateToken}
              loading={busy === "generate"}
              title={issueableAppointments.length ? `${issueableAppointments.length} booked appointment(s) without a token` : "No booked appointment is waiting for a token"}
            >
              Issue token{issueableAppointments.length ? ` (${issueableAppointments.length})` : ""}
            </Button>
            <Button icon={Megaphone} onClick={callNextPatient} loading={busy === "next"} disabled={!nextWaiting}>
              Call next patient
            </Button>
          </>
        }
      />

      {successMessage && <Alert tone="success" onDismiss={() => setSuccessMessage("")}>{successMessage}</Alert>}
      {actionError && <Alert tone="danger" onDismiss={() => setActionError("")}>{actionError}</Alert>}
      {offlineMode && (
        <Alert
          tone="warning"
          title="Server unreachable"
          action={<Button size="sm" variant="secondary" onClick={() => setReloadToken((value) => value + 1)}>Retry</Button>}
        >
          {loadError || "Could not reach the server. Showing saved queue data."}
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        {/* Now serving */}
        <Card className="flex flex-col justify-between overflow-hidden">
          <div className="bg-brand-900 px-5 py-5 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-brand-200">Now serving</p>
            <p className="mt-2 text-5xl font-semibold tracking-tight tabular-nums" aria-live="polite">
              {currentPatient ? `#${currentPatient.token}` : "—"}
            </p>
            <p className="mt-2 truncate text-[15px] font-medium text-brand-50">{currentPatient ? currentPatient.patient : "No patient in consultation"}</p>
            {currentPatient && (
              <p className="mt-0.5 truncate text-[13px] text-brand-200">
                {[currentPatient.doctor, currentPatient.department].filter(Boolean).join(" · ")}
              </p>
            )}
          </div>
          <div className="flex items-center justify-between gap-3 px-5 py-4">
            <div className="min-w-0">
              <p className="text-xs font-medium text-ink-500">Next in line</p>
              <p className="truncate text-sm font-semibold text-ink-900">
                {nextWaiting ? `#${nextWaiting.token} · ${nextWaiting.patient}` : "Nobody waiting"}
              </p>
            </div>
            {currentPatient && (
              <Button
                size="sm"
                variant="subtle"
                icon={CircleCheck}
                loading={busy === `complete-${currentPatient.token}`}
                onClick={() => rowAction(currentPatient.token, "complete")}
              >
                Complete
              </Button>
            )}
          </div>
        </Card>

        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <StatTile icon={ListOrdered} tone="warning" label="Waiting" value={waitingCount} onClick={() => setStatusFilter("Waiting")} />
          <StatTile icon={Stethoscope} label="In consultation" value={consultationCount} onClick={() => setStatusFilter("In Consultation")} />
          <StatTile icon={CircleCheck} tone="success" label="Completed" value={completedCount} onClick={() => setStatusFilter("Completed")} />
          <StatTile icon={SkipForward} tone="neutral" label="Skipped" value={skippedCount} onClick={() => setStatusFilter("Skipped")} />
        </div>
      </div>

      <Card className="overflow-hidden">
        <CardHeader
          title="Patient queue"
          description={`${filteredQueue.length} of ${hospitalQueue.length} token${hospitalQueue.length === 1 ? "" : "s"}`}
        />
        <div className="px-4 pt-1">
          <Tabs tabs={statusTabs} value={statusFilter} onChange={setStatusFilter} label="Filter by status" />
        </div>
        <Toolbar>
          <SearchInput value={search} onChange={setSearch} placeholder="Patient, doctor or token" label="Search queue" className="w-full sm:max-w-xs" />
          <Select value={departmentFilter} onChange={(e) => setDepartmentFilter(e.target.value)} aria-label="Filter by department" className="w-full sm:w-56">
            <option>All Departments</option>
            {departments.map((d) => (
              <option key={d}>{d}</option>
            ))}
          </Select>
        </Toolbar>

        {loading && hospitalQueue.length === 0 ? (
          <SkeletonRows rows={5} />
        ) : filteredQueue.length === 0 ? (
          <EmptyState
            icon={Ticket}
            title={hospitalQueue.length ? "No tokens match these filters" : "The queue is empty"}
            description={hospitalQueue.length ? "Change the status or department filter." : "Issue a token from a booked appointment to start the queue."}
          />
        ) : (
          <TableWrap>
            <table className="hms-table">
              <caption className="sr-only">Patient queue at {selectedHospital.name}</caption>
              <thead>
                <tr>
                  <th scope="col">Token</th>
                  <th scope="col">Patient</th>
                  <th scope="col">Doctor</th>
                  <th scope="col">Department</th>
                  <th scope="col">Type</th>
                  <th scope="col">Waiting</th>
                  <th scope="col">Status</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {filteredQueue.map((item, index) => (
                  <tr key={`${item.token}-${item.hospitalId}-${index}`} className={item.status === "In Consultation" ? "[&>td]:bg-brand-50/60" : ""}>
                    <td>
                      <span className="inline-flex min-w-12 items-center justify-center rounded-md bg-ink-100 px-2 py-1 text-sm font-semibold text-ink-900 tabular-nums">
                        #{item.token}
                      </span>
                    </td>
                    <td>
                      <span className="block font-medium text-ink-900">{item.patient}</span>
                      {(item.contact || item.village) && (
                        <span className="block text-xs text-ink-500 tabular-nums">{[item.contact, item.village].filter(Boolean).join(" · ")}</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap">{item.doctor || <span className="text-ink-400">—</span>}</td>
                    <td>{item.department}</td>
                    <td className="text-ink-600">{item.type}</td>
                    <td className="whitespace-nowrap tabular-nums text-ink-600">{item.waiting}</td>
                    <td><StatusBadge status={item.status} /></td>
                    <td>
                      <div className="flex items-center justify-end gap-1.5">
                        {item.status === "Waiting" && (
                          <>
                            <Button size="sm" variant="subtle" icon={PhoneCall} loading={busy === `call-${item.token}`} onClick={() => rowAction(item.token, "call")}>
                              Call
                            </Button>
                            <Button size="sm" variant="ghost" icon={SkipForward} loading={busy === `skip-${item.token}`} onClick={() => rowAction(item.token, "skip")}>
                              Skip
                            </Button>
                          </>
                        )}
                        {item.status === "In Consultation" && (
                          <Button size="sm" variant="subtle" icon={CircleCheck} loading={busy === `complete-${item.token}`} onClick={() => rowAction(item.token, "complete")}>
                            Complete
                          </Button>
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
    </div>
  )
}

export default Queue
