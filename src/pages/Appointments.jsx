import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Ban, CalendarDays, CalendarPlus, Clock, Eye, Hospital, Pencil, Phone, Stethoscope, Trash2 } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DescriptionList,
  EmptyState,
  Field,
  FormSection,
  Input,
  Modal,
  PageHeader,
  SearchInput,
  SegmentedControl,
  Select,
  SkeletonRows,
  StatusBadge,
  TableWrap,
  Tabs,
  Textarea,
  Toolbar,
} from "../components/ui"
import { APPOINTMENT_STATUSES, CLOSED_STATUSES } from "../config/appointmentStatus.js"

// =====================================================
// Helpers — keep the existing (flat, display-oriented) UI
// shape while talking to the Django Appointment API.
// =====================================================

const two = (value) => String(value).padStart(2, "0")


const normaliseStatus = (status) =>
  APPOINTMENT_STATUSES.find((item) => item.toLowerCase() === String(status || "").toLowerCase()) || "Scheduled"

// "2026-09-01" -> "01 Sep 2026" (what the table renders).
const formatDate = (value) => {
  if (!value) return ""
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
}

// "01 Sep 2026" | "2026-09-01" -> "2026-09-01"
// (the value an <input type="date"> needs).
const toInputDate = (value) => {
  if (!value) return ""
  const iso = String(value).trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}`
}

// "10:30 AM" -> "10:30" (the value an <input type="time"> needs).
const toInputTime = (value) => {
  if (!value) return ""
  const raw = String(value).trim()
  if (/^\d{2}:\d{2}$/.test(raw)) return raw
  const match = raw.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i)
  if (!match) return ""
  let hours = Number(match[1])
  const minutes = match[2]
  const period = match[3] ? match[3].toUpperCase() : null
  if (period === "PM" && hours < 12) hours += 12
  if (period === "AM" && hours === 12) hours = 0
  return `${two(hours)}:${minutes}`
}

// "10:30" -> "10:30 AM" (what the table renders).
const formatTime = (value) => {
  if (!value) return ""
  const raw = String(value).trim()
  const match = raw.match(/^(\d{1,2}):(\d{2})/)
  if (!match) return raw
  let hours = Number(match[1])
  const minutes = match[2]
  const period = hours >= 12 ? "PM" : "AM"
  hours = hours % 12
  if (hours === 0) hours = 12
  return `${two(hours)}:${minutes} ${period}`
}

// Django Appointment -> the flat shape the existing UI expects.
// `apiId` keeps the real backend PK; `id` stays the pretty "A001" code.
const mapAppointmentFromApi = (record) => ({
  apiId: record.id,
  id: `A${String(record.id).padStart(3, "0")}`,
  patient: record.patient_name || "",
  village: record.village || "",
  contact: record.contact || "",
  doctor: record.doctor_name || "",
  date: formatDate(record.appointment_date),
  time: formatTime(record.appointment_time),
  reason: record.reason || "",
  status: normaliseStatus(record.status),
  // Token numbers belong to the Queue/Encounter module (backend
  // QueueToken). They are intentionally left empty here.
  tokenNumber: "",
  hospitalId: record.hospital,
  patientId: record.patient,
  doctorId: record.doctor,
})

const EMPTY_FORM = { patient: "", village: "", contact: "", doctor: "", date: "", time: "", reason: "" }

const todayIso = () => {
  const d = new Date()
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())}`
}

// Network failures get a plain "not saved"; a server refusal keeps its reason.
// After a timeout the server may have saved it, so the list is reloaded.
const notSavedMessage = (error) =>
  error.isNetworkError ? `Not saved: ${error.message}` : error.message

const toList = (data) => (Array.isArray(data) ? data : data?.results || [])

function Appointments() {
  const { selectedHospital } = usePatient()

  // Always loaded from the Django API. Nothing is kept in the browser: an
  // appointment exists only once the server has saved it.
  const [appointments, setAppointments] = useState([])

  // API / UX states.
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [formError, setFormError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const [reloadToken, setReloadToken] = useState(0)

  // Doctors registered at this hospital (the only valid choices).
  const [doctors, setDoctors] = useState([])
  const [doctorsLoaded, setDoctorsLoaded] = useState(false)

  // Patient name suggestions while typing in the form.
  const [patientSuggestions, setPatientSuggestions] = useState([])

  const [search, setSearch] = useState("")
  const [doctorFilter, setDoctorFilter] = useState("All Doctors")
  const [statusFilter, setStatusFilter] = useState("All Status")
  const [dateFilter, setDateFilter] = useState("all")

  const [showForm, setShowForm] = useState(false)
  const [showView, setShowView] = useState(false)
  const [selectedAppointment, setSelectedAppointment] = useState(null)
  const [formData, setFormData] = useState(EMPTY_FORM)
  const [confirm, setConfirm] = useState(null) // { type: "cancel" | "delete", appointment }

  // =========================
  // Load appointments from Django
  // =========================

  useEffect(() => {
    if (!selectedHospital) {
      setAppointments([])
      setLoadError("")
      return undefined
    }

    let cancelled = false

    const loadAppointments = async () => {
      setLoading(true)
      setLoadError("")

      try {
        const data = await api.appointments.list(selectedHospital.id)
        if (cancelled) return
        setAppointments(toList(data).map(mapAppointmentFromApi))
      } catch (error) {
        if (cancelled) return
        setAppointments([])
        setLoadError(error.message || "Unable to reach the server. Appointments could not be loaded.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadAppointments()

    return () => {
      cancelled = true
    }
  }, [selectedHospital, reloadToken])

  // Load this hospital's doctors for the selector and filter.
  useEffect(() => {
    if (!selectedHospital) {
      setDoctors([])
      return undefined
    }
    let cancelled = false
    setDoctorsLoaded(false)
    api.doctors
      .list(selectedHospital.id)
      .then((data) => {
        if (!cancelled) setDoctors(toList(data))
      })
      .catch(() => {
        if (!cancelled) setDoctors([])
      })
      .finally(() => {
        if (!cancelled) setDoctorsLoaded(true)
      })
    return () => {
      cancelled = true
    }
  }, [selectedHospital, reloadToken])

  // Suggest existing patients while the name is being typed.
  useEffect(() => {
    const term = formData.patient.trim()
    if (!showForm || !selectedHospital || term.length < 2) {
      setPatientSuggestions([])
      return undefined
    }
    const timer = setTimeout(() => {
      api.patients
        .list(selectedHospital.id, 1, term)
        .then((data) => setPatientSuggestions(toList(data).slice(0, 8)))
        .catch(() => setPatientSuggestions([]))
    }, 250)
    return () => clearTimeout(timer)
  }, [formData.patient, showForm, selectedHospital])

  // Auto-dismiss the success message.
  useEffect(() => {
    if (!successMessage) return undefined
    const timer = setTimeout(() => setSuccessMessage(""), 4000)
    return () => clearTimeout(timer)
  }, [successMessage])

  // =========================
  // Hospital Filter
  // =========================

  const hospitalAppointments = selectedHospital
    ? appointments.filter((appointment) => String(appointment.hospitalId) === String(selectedHospital.id))
    : []

  // Doctor choices: the hospital's registered doctors, plus any name already on
  // an appointment (so older rows can still be filtered and edited).
  const doctorNames = new Set(doctors.map((d) => d.name).filter(Boolean))
  hospitalAppointments.forEach((a) => a.doctor && doctorNames.add(a.doctor))
  const doctorChoices = Array.from(doctorNames).sort()

  // =========================
  // Search + Filter
  // =========================

  const today = todayIso()

  const baseFiltered = hospitalAppointments.filter((appointment) => {
    const q = search.toLowerCase()
    const matchesSearch =
      (appointment.patient || "").toLowerCase().includes(q) ||
      (appointment.id || "").toLowerCase().includes(q) ||
      (appointment.contact || "").includes(search)
    const matchesDoctor = doctorFilter === "All Doctors" || appointment.doctor === doctorFilter
    const iso = toInputDate(appointment.date)
    const matchesDate = dateFilter === "all" || (dateFilter === "today" ? iso === today : iso >= today)
    return matchesSearch && matchesDoctor && matchesDate
  })

  const statusCounts = APPOINTMENT_STATUSES.reduce(
    (acc, s) => ({ ...acc, [s]: baseFiltered.filter((a) => a.status === s).length }),
    {},
  )

  const filteredAppointments = baseFiltered
    .filter((appointment) => statusFilter === "All Status" || appointment.status === statusFilter)
    .sort((a, b) => `${toInputDate(a.date)} ${toInputTime(a.time)}`.localeCompare(`${toInputDate(b.date)} ${toInputTime(b.time)}`))

  // =========================
  // Form Change
  // =========================

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData({ ...formData, [name]: value })
  }

  // =========================
  // Resolve a patient name -> backend patient id
  // (find first, create if it does not exist)
  // =========================

  const resolvePatientId = async (name, contact) => {
    const trimmedName = (name || "").trim()
    if (!trimmedName) throw new Error("Patient name is required.")

    // Search the whole hospital, not just the first page.
    const results = toList(await api.patients.list(selectedHospital.id, 1, trimmedName))
    const digits = (contact || "").trim()
    const sameName = results.filter((patient) => (patient.name || "").trim().toLowerCase() === trimmedName.toLowerCase())
    const match = sameName.find((patient) => digits && String(patient.phone || "").endsWith(digits)) || sameName[0]
    if (match) return match.id

    // Not found — create a minimal patient record so the
    // Appointment foreign key can be satisfied.
    const created = await api.patients.create({
      name: trimmedName,
      age: 0,
      gender: "Not specified",
      phone: digits,
      condition: "Appointment booking",
      status: "Active",
      hospital: selectedHospital.id,
    })
    return created.id
  }

  // =========================
  // Resolve a doctor name -> backend doctor id
  // Only doctors registered at this hospital can be booked; this screen
  // never creates doctor records.
  // =========================

  const resolveDoctorId = async (name) => {
    const trimmedName = (name || "").trim()
    if (!trimmedName) throw new Error("Doctor is required.")

    const known = doctors.length ? doctors : toList(await api.doctors.list(selectedHospital.id))
    const match = known.find((doctor) => (doctor.name || "").trim().toLowerCase() === trimmedName.toLowerCase())
    if (!match) {
      const error = new Error(`${trimmedName} is not a registered doctor at this hospital.`)
      error.status = 400
      throw error
    }
    return match.id
  }

  const validate = () => {
    if (!selectedHospital) return "Please select a hospital first."
    if (formData.contact.length !== 10) return "Please enter a valid 10 digit contact number."
    return ""
  }

  // =========================
  // Add Appointment
  // =========================

  const handleSubmit = async (e) => {
    e.preventDefault()
    const problem = validate()
    if (problem) {
      setFormError(problem)
      return
    }
    setFormError("")

    setSaving(true)

    try {
      const patientId = await resolvePatientId(formData.patient, formData.contact)
      const doctorId = await resolveDoctorId(formData.doctor)

      const created = await api.appointments.create({
        hospital: selectedHospital.id,
        patient: patientId,
        doctor: doctorId,
        appointment_date: formData.date,
        appointment_time: formData.time,
        reason: formData.reason,
        village: formData.village,
        contact: formData.contact,
      })

      setAppointments((prev) => [mapAppointmentFromApi(created), ...prev])
      setSuccessMessage("Appointment booked.")
      resetForm()
    } catch (error) {
      // Refused, unreachable or timed out: nothing is saved in the browser.
      setFormError(notSavedMessage(error))
      if (error.isTimeout) setReloadToken((t) => t + 1)
    } finally {
      setSaving(false)
    }
  }

  // =========================
  // Delete Appointment
  // =========================

  // The row leaves the list only after the server has deleted it.
  const handleDelete = async (appointment) => {
    try {
      await api.appointments.delete(appointment.apiId)
      setAppointments((prev) => prev.filter((item) => String(item.id) !== String(appointment.id)))
      setSuccessMessage("Appointment deleted.")
    } catch (error) {
      setLoadError(`Not deleted: ${error.message}`)
      setReloadToken((t) => t + 1)
    }
  }

  // =========================
  // Cancel Appointment
  // =========================

  // The status changes only after the server has cancelled it.
  const handleCancel = async (appointment) => {
    try {
      await api.appointments.patch(appointment.apiId, { status: "Cancelled" })
      setAppointments((prev) =>
        prev.map((item) => (String(item.id) === String(appointment.id) ? { ...item, status: "Cancelled" } : item)),
      )
      setSuccessMessage("Appointment cancelled.")
    } catch (error) {
      setLoadError(`Not cancelled: ${error.message}`)
      setReloadToken((t) => t + 1)
    }
  }

  const runConfirmed = async () => {
    const { type, appointment } = confirm
    setConfirm(null)
    setShowView(false)
    if (type === "delete") await handleDelete(appointment)
    else await handleCancel(appointment)
  }

  // =========================
  // View / Edit
  // =========================

  const handleView = (appointment) => {
    setSelectedAppointment(appointment)
    setShowView(true)
  }

  const handleEdit = (appointment) => {
    setSelectedAppointment(appointment)
    setFormData({
      patient: appointment.patient || "",
      village: appointment.village || "",
      contact: appointment.contact || "",
      doctor: appointment.doctor || "",
      date: toInputDate(appointment.date),
      time: toInputTime(appointment.time),
      reason: appointment.reason || "",
    })
    setFormError("")
    setShowView(false)
    setShowForm(true)
  }

  const openNew = () => {
    if (!selectedHospital) {
      setLoadError("Please select a hospital first.")
      return
    }
    setSelectedAppointment(null)
    setFormData(EMPTY_FORM)
    setFormError("")
    setShowForm(true)
  }

  // =========================
  // Save Edit
  // =========================

  const handleUpdate = async (e) => {
    e.preventDefault()
    const problem = validate()
    if (problem) {
      setFormError(problem)
      return
    }
    setFormError("")

    const target = selectedAppointment

    setSaving(true)

    try {
      const patientId = await resolvePatientId(formData.patient, formData.contact)
      const doctorId = await resolveDoctorId(formData.doctor)

      const updated = await api.appointments.update(target.apiId ?? target.id, {
        hospital: selectedHospital.id,
        patient: patientId,
        doctor: doctorId,
        appointment_date: formData.date,
        appointment_time: formData.time,
        reason: formData.reason,
        status: target.status,
        village: formData.village,
        contact: formData.contact,
      })

      const mapped = mapAppointmentFromApi(updated)
      setAppointments((prev) =>
        prev.map((appointment) => (String(appointment.id) === String(target.id) ? { ...appointment, ...mapped } : appointment)),
      )
      setSuccessMessage("Appointment updated.")
      resetForm()
    } catch (error) {
      setFormError(notSavedMessage(error))
      if (error.isTimeout) setReloadToken((t) => t + 1)
    } finally {
      setSaving(false)
    }
  }

  // =========================
  // Reset
  // =========================

  const resetForm = () => {
    setFormData(EMPTY_FORM)
    setSelectedAppointment(null)
    setFormError("")
    setShowForm(false)
  }

  const canChange = (a) => !CLOSED_STATUSES.includes(a.status)

  const statusTabs = [
    { id: "All Status", label: "All", count: baseFiltered.length },
    ...APPOINTMENT_STATUSES.map((s) => ({ id: s, label: s, count: statusCounts[s] })),
  ]

  return (
    <div className="space-y-5">
      <PageHeader
        title="Appointments"
        description={selectedHospital ? `Bookings at ${selectedHospital.name}.` : "Select a hospital from the header to see its appointments."}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Appointments" }]}
        actions={
          <Button icon={CalendarPlus} onClick={openNew} disabled={!selectedHospital}>
            New appointment
          </Button>
        }
      />

      {successMessage && (
        <Alert tone="success" onDismiss={() => setSuccessMessage("")}>
          {successMessage}
        </Alert>
      )}

      {loadError && (
        <Alert
          tone="danger"
          action={<Button size="sm" variant="secondary" onClick={() => setReloadToken((token) => token + 1)}>Retry</Button>}
        >
          {loadError}
        </Alert>
      )}

      {!selectedHospital ? (
        <Card>
          <EmptyState icon={Hospital} title="No hospital selected" description="Choose a hospital in the header to manage its appointments." />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="px-4 pt-2">
            <Tabs tabs={statusTabs} value={statusFilter} onChange={setStatusFilter} label="Filter by status" />
          </div>
          <Toolbar>
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Patient, phone or appointment ID"
              label="Search appointments"
              className="w-full sm:max-w-xs"
            />
            <Select
              value={doctorFilter}
              onChange={(e) => setDoctorFilter(e.target.value)}
              aria-label="Filter by doctor"
              className="w-full sm:w-52"
            >
              <option>All Doctors</option>
              {doctorChoices.map((doctor) => (
                <option key={doctor} value={doctor}>{doctor}</option>
              ))}
            </Select>
            <SegmentedControl
              label="Date range"
              value={dateFilter}
              onChange={setDateFilter}
              options={[
                { value: "all", label: "All dates" },
                { value: "today", label: "Today" },
                { value: "upcoming", label: "Upcoming" },
              ]}
            />
          </Toolbar>

          {loading && filteredAppointments.length === 0 ? (
            <SkeletonRows rows={6} />
          ) : filteredAppointments.length === 0 ? (
            <EmptyState
              icon={CalendarDays}
              title={hospitalAppointments.length ? "No appointments match these filters" : "No appointments yet"}
              description={hospitalAppointments.length ? "Change the status, doctor or date filter." : "Booked appointments for this hospital will appear here."}
              action={!hospitalAppointments.length && <Button icon={CalendarPlus} onClick={openNew}>New appointment</Button>}
            />
          ) : (
            <>
              <TableWrap className="hidden lg:block">
                <table className="hms-table">
                  <caption className="sr-only">Appointments at {selectedHospital.name}</caption>
                  <thead>
                    <tr>
                      <th scope="col">When</th>
                      <th scope="col">Patient</th>
                      <th scope="col">Doctor</th>
                      <th scope="col">Contact</th>
                      <th scope="col">Token</th>
                      <th scope="col">Status</th>
                      <th scope="col"><span className="sr-only">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAppointments.map((appointment) => (
                      <tr key={appointment.id}>
                        <td className="whitespace-nowrap">
                          <span className="block font-medium text-ink-900 tabular-nums">{appointment.time || "—"}</span>
                          <span className="block text-xs text-ink-500 tabular-nums">{appointment.date}</span>
                        </td>
                        <td className="max-w-[18rem]">
                          <button type="button" onClick={() => handleView(appointment)} className="text-left">
                            <span className="block font-medium text-ink-900 hover:text-brand-700">{appointment.patient}</span>
                            <span className="block truncate text-xs text-ink-500">
                              <span className="tabular-nums">{appointment.id}</span>
                              {appointment.reason ? ` · ${appointment.reason}` : ""}
                            </span>
                          </button>
                        </td>
                        <td className="whitespace-nowrap">{appointment.doctor || <span className="text-ink-400">—</span>}</td>
                        <td>
                          <span className="block tabular-nums">{appointment.contact || "—"}</span>
                          {appointment.village && <span className="block text-xs text-ink-500">{appointment.village}</span>}
                        </td>
                        <td className="tabular-nums">{appointment.tokenNumber || <span className="text-ink-400">—</span>}</td>
                        <td>
                          <div className="flex flex-wrap items-center gap-1.5">
                            <StatusBadge status={appointment.status} />
                            {appointment.apiId === undefined && (
                              <Badge tone="warning" className="normal-case">On this device only</Badge>
                            )}
                          </div>
                        </td>
                        <td>
                          <div className="flex items-center justify-end gap-0.5">
                            <Button variant="ghost" size="icon-sm" icon={Eye} onClick={() => handleView(appointment)} aria-label={`View appointment ${appointment.id}`} title="View" />
                            <Button variant="ghost" size="icon-sm" icon={Pencil} onClick={() => handleEdit(appointment)} aria-label={`Edit appointment ${appointment.id}`} title="Edit" />
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              icon={Ban}
                              disabled={!canChange(appointment)}
                              onClick={() => setConfirm({ type: "cancel", appointment })}
                              aria-label={`Cancel appointment ${appointment.id}`}
                              title="Cancel appointment"
                            />
                            <Button variant="danger-ghost" size="icon-sm" icon={Trash2} onClick={() => setConfirm({ type: "delete", appointment })} aria-label={`Delete appointment ${appointment.id}`} title="Delete" />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>

              <ul className="divide-y divide-ink-100 lg:hidden">
                {filteredAppointments.map((appointment) => (
                  <li key={appointment.id}>
                    <button type="button" onClick={() => handleView(appointment)} className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-ink-50">
                      <span className="w-16 shrink-0">
                        <span className="block text-sm font-semibold text-ink-900 tabular-nums">{appointment.time || "—"}</span>
                        <span className="block text-[11px] text-ink-500 tabular-nums">{appointment.date}</span>
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium text-ink-900">{appointment.patient}</span>
                        <span className="block truncate text-xs text-ink-500">{appointment.doctor}{appointment.reason ? ` · ${appointment.reason}` : ""}</span>
                      </span>
                      <StatusBadge status={appointment.status} />
                    </button>
                  </li>
                ))}
              </ul>
              <p className="border-t border-line px-4 py-2.5 text-xs text-ink-500">
                Showing {filteredAppointments.length} of {hospitalAppointments.length} appointments
              </p>
            </>
          )}
        </Card>
      )}

      {/* Add / Edit */}
      <Modal
        open={showForm}
        onClose={resetForm}
        size="lg"
        title={selectedAppointment ? `Edit appointment ${selectedAppointment.id}` : "New appointment"}
        description={selectedHospital ? `At ${selectedHospital.name}` : undefined}
        footer={
          <>
            <Button variant="secondary" onClick={resetForm} disabled={saving}>Cancel</Button>
            <Button type="submit" form="appointment-form" loading={saving} disabled={doctorsLoaded && doctorChoices.length === 0}>
              {selectedAppointment ? "Save changes" : "Book appointment"}
            </Button>
          </>
        }
      >
        <form id="appointment-form" onSubmit={selectedAppointment ? handleUpdate : handleSubmit} className="space-y-6">
          {formError && <Alert tone="danger" title="Not saved">{formError}</Alert>}
          {doctorsLoaded && doctorChoices.length === 0 && (
            <Alert tone="warning" title="No doctors registered">
              Add a doctor for this hospital before booking. <Link to="/doctors" className="font-medium underline">Go to Doctors</Link>
            </Alert>
          )}

          <FormSection title="Patient" description="Start typing to pick an existing patient; a new record is created only if none matches.">
            <Field label="Patient name" required className="sm:col-span-2">
              <Input name="patient" value={formData.patient} onChange={handleChange} list="appointment-patient-suggestions" autoComplete="off" />
            </Field>
            <datalist id="appointment-patient-suggestions">
              {patientSuggestions.map((p) => (
                <option key={p.id} value={p.name}>{p.phone ? `${p.phone}` : ""}</option>
              ))}
            </datalist>
            <Field label="Mobile number" required hint="10 digits">
              <Input
                type="tel"
                inputMode="numeric"
                name="contact"
                value={formData.contact}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, "")
                  if (value.length <= 10) setFormData({ ...formData, contact: value })
                }}
                maxLength={10}
              />
            </Field>
            <Field label="Village / locality" required>
              <Input name="village" value={formData.village} onChange={handleChange} />
            </Field>
          </FormSection>

          <FormSection title="Visit">
            <Field label="Doctor" required className="sm:col-span-2">
              <Select name="doctor" value={formData.doctor} onChange={handleChange}>
                <option value="">{doctorsLoaded ? "Select doctor" : "Loading doctors…"}</option>
                {doctorChoices.map((doctor) => (
                  <option key={doctor} value={doctor}>{doctor}</option>
                ))}
              </Select>
            </Field>
            <Field label="Date" required>
              <Input type="date" name="date" value={formData.date} onChange={handleChange} min={selectedAppointment ? undefined : today} />
            </Field>
            <Field label="Time" required>
              <Input type="time" name="time" value={formData.time} onChange={handleChange} />
            </Field>
            <Field label="Reason for visit" required className="sm:col-span-2">
              <Textarea name="reason" value={formData.reason} onChange={handleChange} rows={3} />
            </Field>
          </FormSection>
        </form>
      </Modal>

      {/* Details */}
      <Modal
        open={showView && Boolean(selectedAppointment)}
        onClose={() => setShowView(false)}
        title="Appointment details"
        description={selectedAppointment?.id}
        footer={
          selectedAppointment && (
            <>
              <Button variant="danger-ghost" icon={Trash2} onClick={() => setConfirm({ type: "delete", appointment: selectedAppointment })} className="mr-auto">
                Delete
              </Button>
              {canChange(selectedAppointment) && (
                <Button variant="secondary" icon={Ban} onClick={() => setConfirm({ type: "cancel", appointment: selectedAppointment })}>
                  Cancel appointment
                </Button>
              )}
              <Button icon={Pencil} onClick={() => handleEdit(selectedAppointment)}>Edit</Button>
            </>
          )
        }
      >
        {selectedAppointment && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3 rounded-xl bg-ink-50 px-4 py-3">
              <Clock size={18} className="text-brand-600" aria-hidden="true" />
              <p className="text-sm font-semibold text-ink-900 tabular-nums">
                {selectedAppointment.date} · {selectedAppointment.time}
              </p>
              <StatusBadge status={selectedAppointment.status} className="ml-auto" />
            </div>
            <DescriptionList
              items={[
                { label: "Patient", value: selectedAppointment.patient },
                { label: "Doctor", value: selectedAppointment.doctor && <span className="inline-flex items-center gap-1.5"><Stethoscope size={14} className="text-ink-400" aria-hidden="true" />{selectedAppointment.doctor}</span> },
                { label: "Mobile", value: selectedAppointment.contact && <span className="inline-flex items-center gap-1.5 tabular-nums"><Phone size={14} className="text-ink-400" aria-hidden="true" />{selectedAppointment.contact}</span> },
                { label: "Village / locality", value: selectedAppointment.village },
                { label: "Token", value: selectedAppointment.tokenNumber },
                { label: "Hospital", value: selectedHospital?.name },
              ]}
            />
            <DescriptionList columns={1} items={[{ label: "Reason for visit", value: selectedAppointment.reason }]} />
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={Boolean(confirm)}
        onCancel={() => setConfirm(null)}
        onConfirm={runConfirmed}
        destructive
        title={confirm?.type === "delete" ? "Delete appointment?" : "Cancel appointment?"}
        confirmLabel={confirm?.type === "delete" ? "Delete" : "Cancel appointment"}
        cancelLabel="Keep"
        message={
          confirm && (
            <>
              {confirm.type === "delete" ? "This permanently removes" : "This cancels"} the appointment for{" "}
              <strong className="font-semibold text-ink-900">{confirm.appointment.patient}</strong> on{" "}
              {confirm.appointment.date} at {confirm.appointment.time}.
              {confirm.type === "delete" && " It cannot be undone."}
            </>
          )
        }
      />
    </div>
  )
}

export default Appointments
