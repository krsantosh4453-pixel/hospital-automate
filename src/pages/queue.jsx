import { useEffect, useState } from "react"
import { BellRing, CircleCheck, Hospital, ListOrdered, Megaphone, PhoneCall, RotateCcw, SkipForward, Stethoscope, Ticket, UserX } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
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

// Every status a QueueToken can have on the server (encounters.QueueToken.Status).
const QUEUE_STATUSES = ["Waiting", "Called", "Acknowledged", "Ready", "In Consultation", "Completed", "Skipped", "No Show", "Cancelled"]
// Called, then (optionally) acknowledged or ready: on the way to the doctor.
const CALLED_STATUSES = ["Called", "Acknowledged", "Ready"]
// Shown as a tab even when empty; the others appear once a token has them.
const CORE_TABS = ["Waiting", "Called", "In Consultation", "Completed"]
const isCalled = (status) => CALLED_STATUSES.includes(status)

// The "Waiting" column: minutes while waiting, "Now" once called, and a dash
// after the patient has gone in or left the queue.
const waitingLabel = (status, minutes) => {
  if (status === "Waiting") return `${minutes ?? 0} min`
  if (isCalled(status)) return "Now"
  if (status === "In Consultation") return "With doctor"
  return "—"
}

// Per-row actions, as the server allows them (encounters/views.py). The
// server also moves the token's appointment to the matching status.
const ROW_ACTIONS = {
  call: { apiCall: (id) => api.queue.call(id), done: "called", fail: "Failed to call this patient." },
  start: { apiCall: (id) => api.queue.startConsultation(id), done: "sent in to the doctor", fail: "Failed to start the consultation." },
  complete: { apiCall: (id) => api.queue.complete(id), done: "completed", fail: "Failed to complete this patient." },
  skip: { apiCall: (id) => api.queue.skip(id), done: "skipped", fail: "Failed to skip this patient." },
  noShow: { apiCall: (id) => api.queue.noShow(id), done: "marked as no-show", fail: "Failed to mark as no-show." },
  requeue: { apiCall: (id) => api.queue.requeue(id), done: "put back in the queue", fail: "Failed to put the token back in the queue." },
}

function Queue() {
  const { selectedHospital } = usePatient()

  // Live queue records from Django (encounters.QueueToken).
  const [queue, setQueue] = useState([])
  // Booked appointments from Django, so any desk can issue their tokens
  // (not only the browser that booked them).
  const [serverAppointments, setServerAppointments] = useState([])

  const [departmentFilter, setDepartmentFilter] = useState("All Departments")
  const [statusFilter, setStatusFilter] = useState("All Status")
  const [search, setSearch] = useState("")

  // API state (loading / error / retry / feedback). Starts loading so no
  // action runs against the empty lists before the first fetch returns.
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
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
    waiting: waitingLabel(record.status || "Waiting", record.waiting_minutes),
    status: record.status || "Waiting",
    hospitalId: record.hospital,
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
        const [data, appointmentData] = await Promise.all([
          api.queue.list(selectedHospital.id),
          api.appointments.list(selectedHospital.id),
        ])
        if (cancelled) return
        const records = Array.isArray(data) ? data : data?.results || []
        setQueue(records.map(mapQueueFromApi))
        const appointments = Array.isArray(appointmentData) ? appointmentData : appointmentData?.results || []
        setServerAppointments(
          appointments.map((appointment) => ({
            apiId: appointment.id,
            hospitalId: appointment.hospital,
            status: appointment.status,
            patient: appointment.patient_name,
          })),
        )
      } catch (error) {
        if (cancelled) return
        // Show nothing rather than a queue the server may no longer hold.
        setQueue([])
        setServerAppointments([])
        setLoadError(error.message || "Failed to load the queue.")
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
  // one yet, as stored on the server for this hospital.
  const issueableAppointments = serverAppointments.filter(
    (appointment) =>
      appointment.apiId &&
      String(appointment.hospitalId) === String(selectedHospital?.id) &&
      appointment.status === "Scheduled" &&
      !queue.some((item) => String(item.appointmentApiId) === String(appointment.apiId)),
  )

  const generateToken = async () => {
    setActionError("")
    setSuccessMessage("")

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

  // The queue is the server's QueueTokens only. Appointments kept in this
  // browser used to be merged in with made-up token numbers ("A001"), which
  // other desks never saw; booked appointments now get real tokens above.
  const allQueue = queue

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
  const filteredQueue = baseFiltered.filter((item) => statusFilter === "All Status" || (statusFilter === "Called" ? isCalled(item.status) : item.status === statusFilter))

  // Statistics
  const countOf = (status) => hospitalQueue.filter((item) => item.status === status).length
  const waitingCount = countOf("Waiting")
  const consultationCount = countOf("In Consultation")
  const completedCount = countOf("Completed")
  const calledCount = hospitalQueue.filter((item) => isCalled(item.status)).length

  const currentPatient = hospitalQueue.find((item) => item.status === "In Consultation")
  // Called and on the way to the doctor, shown when nobody is in consultation.
  const calledPatient = hospitalQueue.find((item) => isCalled(item.status))
  const servingPatient = currentPatient || calledPatient
  const nextWaiting = hospitalQueue.find((item) => item.status === "Waiting")

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

    // Django advances the queue (completes the token being served and calls
    // the next one). The screen changes only from the server's reload.
    try {
      await api.queue.callNext(selectedHospital.id)
      setSuccessMessage(`Called token #${nextPatient.token}. Start the consultation when the patient comes in.`)
    } catch (error) {
      setActionError(`Not changed: ${error.message || "Failed to call the next patient."}`)
    } finally {
      setBusy("")
      setReloadToken((value) => value + 1)
    }
  }

  // Shared handler for the per-row queue actions (ROW_ACTIONS).
  const rowAction = async (token, kind) => {
    const config = ROW_ACTIONS[kind]

    const selectedQueuePatient = hospitalQueue.find((item) => String(item.token) === String(token))
    setActionError("")
    setSuccessMessage("")
    setBusy(`${kind}-${token}`)

    // Saved on the QueueToken first; the screen changes only from the reload.
    try {
      await config.apiCall(selectedQueuePatient.apiId)
      setSuccessMessage(`Token #${token} ${config.done}.`)
    } catch (error) {
      setActionError(`Not changed: ${error.message || config.fail}`)
    } finally {
      setBusy("")
      setReloadToken((value) => value + 1)
    }
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

  // "Called" groups Called, Acknowledged and Ready; the rest are one status each.
  const inTab = (item, tab) => (tab === "Called" ? isCalled(item.status) : item.status === tab)
  const statusTabs = [
    { id: "All Status", label: "All", count: baseFiltered.length },
    ...QUEUE_STATUSES.filter((s) => !["Acknowledged", "Ready"].includes(s))
      .map((s) => ({ id: s, label: s, count: baseFiltered.filter((i) => inTab(i, s)).length }))
      .filter((tab) => CORE_TABS.includes(tab.id) || tab.count > 0 || tab.id === statusFilter),
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
              disabled={loading}
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
      {loadError && (
        <Alert
          tone="danger"
          title="Queue could not be loaded"
          action={<Button size="sm" variant="secondary" onClick={() => setReloadToken((value) => value + 1)}>Retry</Button>}
        >
          {loadError}
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        {/* Now serving */}
        <Card className="flex flex-col justify-between overflow-hidden">
          <div className="bg-brand-900 px-5 py-5 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-brand-200">
              {currentPatient || !calledPatient ? "Now serving" : "Called · on the way"}
            </p>
            <p className="mt-2 text-5xl font-semibold tracking-tight tabular-nums" aria-live="polite">
              {servingPatient ? `#${servingPatient.token}` : "—"}
            </p>
            <p className="mt-2 truncate text-[15px] font-medium text-brand-50">{servingPatient ? servingPatient.patient : "No patient in consultation"}</p>
            {servingPatient && (
              <p className="mt-0.5 truncate text-[13px] text-brand-200">
                {[servingPatient.doctor, servingPatient.department].filter(Boolean).join(" · ")}
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
            {currentPatient ? (
              <Button
                size="sm"
                variant="subtle"
                icon={CircleCheck}
                loading={busy === `complete-${currentPatient.token}`}
                onClick={() => rowAction(currentPatient.token, "complete")}
              >
                Complete
              </Button>
            ) : calledPatient && (
              <Button
                size="sm"
                variant="subtle"
                icon={Stethoscope}
                loading={busy === `start-${calledPatient.token}`}
                onClick={() => rowAction(calledPatient.token, "start")}
              >
                Start consultation
              </Button>
            )}
          </div>
        </Card>

        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <StatTile icon={ListOrdered} tone="warning" label="Waiting" value={waitingCount} onClick={() => setStatusFilter("Waiting")} />
          <StatTile icon={BellRing} label="Called" value={calledCount} onClick={() => setStatusFilter("Called")} />
          <StatTile icon={Stethoscope} label="In consultation" value={consultationCount} onClick={() => setStatusFilter("In Consultation")} />
          <StatTile icon={CircleCheck} tone="success" label="Completed" value={completedCount} onClick={() => setStatusFilter("Completed")} />
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
                        {isCalled(item.status) && (
                          <>
                            <Button size="sm" variant="subtle" icon={Stethoscope} loading={busy === `start-${item.token}`} onClick={() => rowAction(item.token, "start")}>
                              Start consultation
                            </Button>
                            <Button size="sm" variant="ghost" icon={UserX} loading={busy === `noShow-${item.token}`} onClick={() => rowAction(item.token, "noShow")}>
                              No show
                            </Button>
                          </>
                        )}
                        {item.status === "In Consultation" && (
                          <Button size="sm" variant="subtle" icon={CircleCheck} loading={busy === `complete-${item.token}`} onClick={() => rowAction(item.token, "complete")}>
                            Complete
                          </Button>
                        )}
                        {(item.status === "Skipped" || item.status === "No Show") && (
                          <Button size="sm" variant="ghost" icon={RotateCcw} loading={busy === `requeue-${item.token}`} onClick={() => rowAction(item.token, "requeue")}>
                            Back to queue
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
