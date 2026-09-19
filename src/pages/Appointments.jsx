import { useEffect, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useAppointment } from "../assets/context/AppointmentContext.jsx"
import api from "../services/api.js"


// =====================================================
// Helpers — keep the existing (flat, display-oriented) UI
// shape while talking to the Django Appointment API.
// =====================================================

const two = (value) => String(value).padStart(2, "0")

// Statuses the UI already knows about.
const APPOINTMENT_STATUSES = [
  "Confirmed",
  "Waiting",
  "Completed",
  "Cancelled",
]

// Django stores status as free text (default "Scheduled").
// Normalise it to a value the existing pills understand.
const normaliseStatus = (status) => {
  if (!status) {
    return "Confirmed"
  }

  const match = APPOINTMENT_STATUSES.find(
    (item) =>
      item.toLowerCase() ===
      String(status).toLowerCase()
  )

  return match || "Confirmed"
}

// "2026-09-01" -> "01 Sep 2026" (what the table renders).
const formatDate = (value) => {
  if (!value) {
    return ""
  }

  const date = new Date(
    `${String(value).slice(0, 10)}T00:00:00`
  )

  if (Number.isNaN(date.getTime())) {
    return String(value)
  }

  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}

// "01 Sep 2026" | "2026-09-01" -> "2026-09-01"
// (the value an <input type="date"> needs).
const toInputDate = (value) => {
  if (!value) {
    return ""
  }

  const iso = String(value).trim()

  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
    return iso
  }

  const date = new Date(iso)

  if (Number.isNaN(date.getTime())) {
    return ""
  }

  return `${date.getFullYear()}-${two(
    date.getMonth() + 1
  )}-${two(date.getDate())}`
}

// "10:30 AM" -> "10:30" (the value an <input type="time"> needs).
const toInputTime = (value) => {
  if (!value) {
    return ""
  }

  const raw = String(value).trim()

  if (/^\d{2}:\d{2}$/.test(raw)) {
    return raw
  }

  const match = raw.match(
    /^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i
  )

  if (!match) {
    return ""
  }

  let hours = Number(match[1])
  const minutes = match[2]
  const period = match[3]
    ? match[3].toUpperCase()
    : null

  if (period === "PM" && hours < 12) {
    hours += 12
  }

  if (period === "AM" && hours === 12) {
    hours = 0
  }

  return `${two(hours)}:${minutes}`
}

// "10:30" -> "10:30 AM" (what the table renders).
const formatTime = (value) => {
  if (!value) {
    return ""
  }

  const raw = String(value).trim()
  const match = raw.match(/^(\d{1,2}):(\d{2})/)

  if (!match) {
    return raw
  }

  let hours = Number(match[1])
  const minutes = match[2]
  const period = hours >= 12 ? "PM" : "AM"

  hours = hours % 12

  if (hours === 0) {
    hours = 12
  }

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


function Appointments() {

  const { selectedHospital } = usePatient()

  const {
    appointments: savedAppointments,
    addAppointment,
    updateAppointment,
    deleteAppointment,
    cancelAppointment,
    getHospitalAppointments,
  } = useAppointment()

  // Offline / demo seed data — kept so the page still works
  // (exactly as before) when the Django API is unreachable.
  const fallbackAppointments = [
    {
      id: "A001",
      patient: "Rahul Kumar",
      village: "Rajaur",
      contact: "9876543210",
      doctor: "Dr. Sharma",
      date: "01 Sep 2026",
      time: "10:30 AM",
      reason: "General Checkup",
      status: "Confirmed",
      tokenNumber: "T-001",
      hospitalId: 1,
    },
    {
      id: "A002",
      patient: "Priya Singh",
      village: "Begusarai",
      contact: "9876543211",
      doctor: "Dr. Verma",
      date: "01 Sep 2026",
      time: "11:00 AM",
      reason: "Cardiology",
      status: "Waiting",
      tokenNumber: "T-002",
      hospitalId: 1,
    },
    {
      id: "A003",
      patient: "Amit Kumar",
      village: "Barauni",
      contact: "9876543212",
      doctor: "Dr. Singh",
      date: "01 Sep 2026",
      time: "11:30 AM",
      reason: "Follow-up",
      status: "Completed",
      tokenNumber: "T-003",
      hospitalId: 2,
    },
  ]

  const [appointments, setAppointments] = useState(
    fallbackAppointments
  )

  // API / UX states.
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [offlineMode, setOfflineMode] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")
  const [reloadToken, setReloadToken] = useState(0)


  // =====================================================
  // OLD APPOINTMENTS + NEW CONTEXT APPOINTMENTS
  // =====================================================

  const allAppointments = [
    ...appointments,
    ...savedAppointments.filter(
      (saved) =>
        !appointments.some(
          (old) => String(old.id) === String(saved.id)
        )
    ),
  ]

  const [search, setSearch] = useState("")
  const [doctorFilter, setDoctorFilter] = useState("All Doctors")
  const [statusFilter, setStatusFilter] = useState("All Status")

  const [showForm, setShowForm] = useState(false)
  const [showView, setShowView] = useState(false)

  const [selectedAppointment, setSelectedAppointment] = useState(null)

  const [formData, setFormData] = useState({
    patient: "",
    village: "",
    contact: "",
    doctor: "",
    date: "",
    time: "",
    reason: "",
  })


  // =========================
  // Load appointments from Django
  // =========================

  useEffect(() => {

    if (!selectedHospital) {
      setAppointments([])
      setLoadError("")
      setOfflineMode(false)
      return
    }

    let cancelled = false

    const loadAppointments = async () => {

      setLoading(true)
      setLoadError("")

      try {

        const data =
          await api.appointments.list(
            selectedHospital.id
          )

        const results = Array.isArray(data)
          ? data
          : data?.results || []

        if (cancelled) {
          return
        }

        setAppointments(
          results.map(mapAppointmentFromApi)
        )

        setOfflineMode(false)

      } catch (error) {

        if (cancelled) {
          return
        }

        // Fall back to localStorage / demo data so the
        // existing behaviour keeps working.
        const localAppointments =
          getHospitalAppointments(
            selectedHospital.id
          )

        const demoAppointments =
          fallbackAppointments.filter(
            (appointment) =>
              String(appointment.hospitalId) ===
              String(selectedHospital.id)
          )

        setAppointments(
          localAppointments.length > 0
            ? localAppointments
            : demoAppointments
        )

        setOfflineMode(true)
        setLoadError(
          error.message ||
          "Unable to reach the server. Showing locally saved appointments."
        )

      } finally {

        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadAppointments()

    return () => {
      cancelled = true
    }

  }, [selectedHospital, reloadToken])


  // Auto-dismiss the success message.
  useEffect(() => {

    if (!successMessage) {
      return
    }

    const timer = setTimeout(
      () => setSuccessMessage(""),
      4000
    )

    return () => clearTimeout(timer)

  }, [successMessage])


  // =========================
  // Hospital Filter
  // =========================

  const hospitalAppointments = selectedHospital
    ? allAppointments.filter(
      (appointment) =>
        String(appointment.hospitalId) ===
        String(selectedHospital.id)
    )
    : []


  // =========================
  // Doctor options (from data)
  // Falls back to the original fixed list so the UI is never empty.
  // =========================

  const doctorOptions = Array.from(
    new Set(
      hospitalAppointments
        .map((appointment) => appointment.doctor)
        .filter(Boolean)
    )
  ).sort()

  const doctorChoices =
    doctorOptions.length > 0
      ? doctorOptions
      : ["Dr. Sharma", "Dr. Verma", "Dr. Singh"]


  // =========================
  // Search + Filter
  // =========================

  const filteredAppointments =
    hospitalAppointments.filter((appointment) => {

      const patientName =
        appointment.patient || ""

      const appointmentId =
        appointment.id || ""

      const matchesSearch =
        patientName
          .toLowerCase()
          .includes(search.toLowerCase()) ||
        appointmentId
          .toLowerCase()
          .includes(search.toLowerCase())

      const matchesDoctor =
        doctorFilter === "All Doctors" ||
        appointment.doctor === doctorFilter

      const matchesStatus =
        statusFilter === "All Status" ||
        appointment.status === statusFilter

      return (
        matchesSearch &&
        matchesDoctor &&
        matchesStatus
      )
    })


  // =========================
  // Form Change
  // =========================

  const handleChange = (e) => {

    const { name, value } = e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }


  // =========================
  // Resolve a patient name -> backend patient id
  // (find first, create if it does not exist)
  // =========================

  const resolvePatientId = async (
    name,
    contact
  ) => {

    const trimmedName = (name || "").trim()

    if (!trimmedName) {
      throw new Error(
        "Patient name is required."
      )
    }

    const data = await api.patients.list(
      selectedHospital.id
    )

    const results = Array.isArray(data)
      ? data
      : data?.results || []

    const match = results.find(
      (patient) =>
        (patient.name || "")
          .trim()
          .toLowerCase() ===
        trimmedName.toLowerCase()
    )

    if (match) {
      return match.id
    }

    // Not found — create a minimal patient record so the
    // Appointment foreign key can be satisfied.
    const created = await api.patients.create({
      name: trimmedName,
      age: 0,
      gender: "Not specified",
      phone: (contact || "").trim(),
      condition: "Appointment booking",
      status: "Active",
      hospital: selectedHospital.id,
    })

    return created.id
  }


  // =========================
  // Resolve a doctor name -> backend doctor id
  // (find first, create if it does not exist)
  // =========================

  const resolveDoctorId = async (name) => {

    const trimmedName = (name || "").trim()

    if (!trimmedName) {
      throw new Error("Doctor is required.")
    }

    const data = await api.doctors.list(
      selectedHospital.id
    )

    const results = Array.isArray(data)
      ? data
      : data?.results || []

    const match = results.find(
      (doctor) =>
        (doctor.name || "")
          .trim()
          .toLowerCase() ===
        trimmedName.toLowerCase()
    )

    if (match) {
      return match.id
    }

    const created = await api.doctors.create({
      name: trimmedName,
      specialization: "General",
      phone: "",
      status: "Active",
      hospital: selectedHospital.id,
    })

    return created.id
  }


  // =========================
  // Add Appointment
  // =========================

  const handleSubmit = async (e) => {

    e.preventDefault()

    if (!selectedHospital) {

      alert(
        "Please select a hospital before booking an appointment."
      )

      return
    }

    if (formData.contact.length !== 10) {

      alert(
        "Please enter a valid 10 digit contact number."
      )

      return
    }

    // Local (offline) appointment — keeps the original client-side
    // id + token behaviour when the backend is unreachable.
    const localAppointment = {

      id: `A${String(
        allAppointments.length + 1
      ).padStart(3, "0")}`,

      patient: formData.patient,

      village: formData.village,

      contact: formData.contact,

      doctor: formData.doctor,

      date: formatDate(formData.date),

      time: formatTime(formData.time),

      reason: formData.reason,

      status: "Confirmed",

      tokenNumber: `T-${String(
        allAppointments.length + 1
      ).padStart(3, "0")}`,

      hospitalId:
        selectedHospital.id,
    }

    setSaving(true)

    try {

      const patientId = await resolvePatientId(
        formData.patient,
        formData.contact
      )

      const doctorId = await resolveDoctorId(
        formData.doctor
      )

      const created =
        await api.appointments.create({
          hospital: selectedHospital.id,
          patient: patientId,
          doctor: doctorId,
          appointment_date: formData.date,
          appointment_time: formData.time,
          reason: formData.reason,
          status: "Confirmed",
          village: formData.village,
          contact: formData.contact,
        })

      const mapped = mapAppointmentFromApi(created)

      // Keep the API row + the local context copy in sync.
      // Same id => the de-duplicated merge shows a single row.
      setAppointments((prev) => [mapped, ...prev])

      addAppointment({
        ...mapped,
        tokenNumber: localAppointment.tokenNumber,
      })

      setOfflineMode(false)
      setSuccessMessage("Appointment booked successfully.")

      resetForm()

    } catch (error) {

      // Degrade to the original local behaviour.
      setOfflineMode(true)

      setAppointments((prev) => [
        ...prev,
        localAppointment,
      ])

      addAppointment(localAppointment)

      setSuccessMessage(
        "Saved locally. The server could not be reached."
      )

      resetForm()

    } finally {

      setSaving(false)
    }
  }


  // =========================
  // Delete Appointment
  // =========================

  const handleDelete = async (appointment) => {

    const confirmDelete =
      window.confirm(
        "Are you sure you want to delete this appointment?"
      )

    if (!confirmDelete) {
      return
    }

    // Remove locally first (original behaviour).
    setAppointments((prev) =>
      prev.filter(
        (item) =>
          String(item.id) !==
          String(appointment.id)
      )
    )

    deleteAppointment(appointment.id)

    // Local-only rows (or offline mode) cannot be deleted
    // from the server.
    if (
      appointment.apiId === undefined ||
      offlineMode
    ) {
      setSuccessMessage(
        "Appointment removed locally."
      )
      return
    }

    try {

      await api.appointments.delete(
        appointment.apiId
      )

      setSuccessMessage(
        "Appointment deleted successfully."
      )

    } catch (error) {

      setOfflineMode(true)
      setSuccessMessage(
        "Removed locally. The server could not be reached."
      )
    }
  }


  // =========================
  // Cancel Appointment
  // =========================

  const handleCancel = async (appointment) => {

    setAppointments((prev) =>
      prev.map((item) =>
        String(item.id) ===
          String(appointment.id)
          ? {
            ...item,
            status: "Cancelled",
          }
          : item
      )
    )

    // NEW CODE
    cancelAppointment(appointment.id)

    if (
      appointment.apiId === undefined ||
      offlineMode
    ) {
      setSuccessMessage(
        "Appointment cancelled locally."
      )
      return
    }

    try {

      await api.appointments.patch(
        appointment.apiId,
        { status: "Cancelled" }
      )

      setSuccessMessage(
        "Appointment cancelled successfully."
      )

    } catch (error) {

      setOfflineMode(true)
      setSuccessMessage(
        "Cancelled locally. The server could not be reached."
      )
    }
  }


  // =========================
  // View Appointment
  // =========================

  const handleView = (appointment) => {

    setSelectedAppointment(
      appointment
    )

    setShowView(true)
  }


  // =========================
  // Edit Appointment
  // =========================

  const handleEdit = (appointment) => {

    setSelectedAppointment(
      appointment
    )

    setFormData({

      patient:
        appointment.patient || "",

      village:
        appointment.village || "",

      contact:
        appointment.contact || "",

      doctor:
        appointment.doctor || "",

      date:
        toInputDate(appointment.date),

      time:
        toInputTime(appointment.time),

      reason:
        appointment.reason || "",
    })

    setShowForm(true)
  }


  // =========================
  // Save Edit
  // =========================

  const handleUpdate = async (e) => {

    e.preventDefault()

    if (formData.contact.length !== 10) {

      alert(
        "Please enter a valid 10 digit contact number."
      )

      return
    }

    if (!selectedHospital) {

      alert(
        "Please select a hospital before updating an appointment."
      )

      return
    }

    const target = selectedAppointment

    setSaving(true)

    try {

      const patientId = await resolvePatientId(
        formData.patient,
        formData.contact
      )

      const doctorId = await resolveDoctorId(
        formData.doctor
      )

      const updated =
        await api.appointments.update(
          target.apiId ?? target.id,
          {
            hospital: selectedHospital.id,
            patient: patientId,
            doctor: doctorId,
            appointment_date: formData.date,
            appointment_time: formData.time,
            reason: formData.reason,
            status: target.status,
            village: formData.village,
            contact: formData.contact,
          }
        )

      const mapped = mapAppointmentFromApi(updated)

      setAppointments((prev) =>
        prev.map((appointment) =>
          String(appointment.id) ===
            String(target.id)
            ? {
              ...appointment,
              ...mapped,
            }
            : appointment
        )
      )

      // NEW CODE
      updateAppointment(
        target.id,
        {
          patient: formData.patient,
          village: formData.village,
          contact: formData.contact,
          doctor: formData.doctor,
          date: formatDate(formData.date),
          time: formatTime(formData.time),
          reason: formData.reason,
        }
      )

      setOfflineMode(false)
      setSuccessMessage(
        "Appointment updated successfully."
      )

      resetForm()

    } catch (error) {

      // Degrade to the original local behaviour.
      setOfflineMode(true)

      setAppointments((prev) =>
        prev.map((appointment) =>
          String(appointment.id) ===
            String(target.id)
            ? {
              ...appointment,

              patient:
                formData.patient,

              village:
                formData.village,

              contact:
                formData.contact,

              doctor:
                formData.doctor,

              date:
                formatDate(formData.date),

              time:
                formatTime(formData.time),

              reason:
                formData.reason,
            }
            : appointment
        )
      )

      updateAppointment(
        target.id,
        {
          patient: formData.patient,
          village: formData.village,
          contact: formData.contact,
          doctor: formData.doctor,
          date: formatDate(formData.date),
          time: formatTime(formData.time),
          reason: formData.reason,
        }
      )

      setSuccessMessage(
        "Saved locally. The server could not be reached."
      )

      resetForm()
    } finally {

      setSaving(false)
    }
  }


  // =========================
  // Reset
  // =========================

  const resetForm = () => {

    setFormData({

      patient: "",

      village: "",

      contact: "",

      doctor: "",

      date: "",

      time: "",

      reason: "",
    })

    setSelectedAppointment(
      null
    )

    setShowForm(false)
  }


  return (

    <div>

      {/* =========================
          Header
      ========================= */}

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

        <div>

          <h1 className="text-3xl font-bold text-gray-800">
            Appointments
          </h1>

          <p className="text-gray-500 mt-1">
            Schedule and manage hospital appointments
          </p>

        </div>

        <button
          onClick={() => {

            if (!selectedHospital) {

              alert(
                "Please select a hospital first."
              )

              return
            }

            setSelectedAppointment(null)

            setFormData({
              patient: "",
              village: "",
              contact: "",
              doctor: "",
              date: "",
              time: "",
              reason: "",
            })

            setShowForm(true)

          }}
          className="bg-blue-600 text-white px-5 py-3 rounded-lg font-medium hover:bg-blue-700"
        >
          + New Appointment
        </button>

      </div>


      {/* =========================
          Current Hospital
      ========================= */}

      <div className="bg-white rounded-xl shadow-sm p-5 mb-6 border border-gray-100">

        {selectedHospital ? (

          <div className="flex items-center gap-4">

            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-2xl">
              🏥
            </div>

            <div>

              <p className="text-xs text-gray-500">
                Current Hospital
              </p>

              <h2 className="font-bold text-gray-800">
                {selectedHospital.name}
              </h2>

              <p className="text-sm text-gray-500">
                📍 {selectedHospital.address}
              </p>

            </div>

          </div>

        ) : (

          <div>

            <p className="font-semibold text-orange-600">
              ⚠️ No hospital selected
            </p>

            <p className="text-sm text-gray-500 mt-1">
              Select a hospital from the header first.
            </p>

          </div>

        )}

      </div>


      {/* =========================
          Feedback (success / offline / error)
      ========================= */}

      {successMessage && (

        <div className="bg-green-50 border border-green-200 text-green-700 rounded-xl px-5 py-3 mb-6">
          {successMessage}
        </div>

      )}

      {offlineMode && (

        <div className="bg-amber-50 border border-amber-200 text-amber-700 rounded-xl px-5 py-3 mb-6">
          Offline mode — showing locally saved appointments. Changes are kept on this device until the server is reachable again.
        </div>

      )}

      {loadError && (

        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-5 py-3 mb-6 flex items-center justify-between gap-4">

          <span>{loadError}</span>

          <button
            onClick={() =>
              setReloadToken(
                (token) => token + 1
              )
            }
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Retry
          </button>

        </div>

      )}


      {/* =========================
          Content
      ========================= */}

      {selectedHospital && (

        <>

          {/* =========================
              Search & Filters
          ========================= */}

          <div className="bg-white rounded-xl shadow-sm p-5 mb-6">

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

              <input
                type="text"
                placeholder="Search patient or appointment ID..."
                value={search}
                onChange={(e) =>
                  setSearch(
                    e.target.value
                  )
                }
                className="border border-gray-300 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              />

              <select
                value={doctorFilter}
                onChange={(e) =>
                  setDoctorFilter(
                    e.target.value
                  )
                }
                className="border border-gray-300 rounded-lg px-4 py-3"
              >

                <option>
                  All Doctors
                </option>

                {doctorChoices.map((doctor) => (

                  <option
                    key={doctor}
                    value={doctor}
                  >
                    {doctor}
                  </option>

                ))}

              </select>

              <select
                value={statusFilter}
                onChange={(e) =>
                  setStatusFilter(
                    e.target.value
                  )
                }
                className="border border-gray-300 rounded-lg px-4 py-3"
              >

                <option>
                  All Status
                </option>

                <option>
                  Confirmed
                </option>

                <option>
                  Waiting
                </option>

                <option>
                  Completed
                </option>

                <option>
                  Cancelled
                </option>

              </select>

            </div>

          </div>


          {/* =========================
              Appointment Table
          ========================= */}

          <div className="bg-white rounded-xl shadow-sm overflow-hidden">

            <div className="p-5 border-b">

              <h2 className="text-lg font-semibold text-gray-800">
                Appointment List
              </h2>

              <p className="text-sm text-gray-500 mt-1">
                {filteredAppointments.length}
                {" "}
                appointment(s) found
              </p>

            </div>

            <div className="overflow-x-auto">

              <table className="w-full">

                <thead className="bg-gray-50">

                  <tr>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      ID
                    </th>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      Patient
                    </th>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      Village
                    </th>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      Contact
                    </th>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      Doctor
                    </th>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      Date
                    </th>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      Time
                    </th>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      Token
                    </th>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      Status
                    </th>

                    <th className="text-left px-5 py-4 text-sm text-gray-600">
                      Actions
                    </th>

                  </tr>

                </thead>

                <tbody>

                  {loading ? (

                    <tr>

                      <td
                        colSpan="10"
                        className="text-center py-10 text-gray-500"
                      >
                        Loading appointments...
                      </td>

                    </tr>

                  ) : filteredAppointments.length === 0 ? (

                    <tr>

                      <td
                        colSpan="10"
                        className="text-center py-10 text-gray-500"
                      >
                        No appointments found
                      </td>

                    </tr>

                  ) : (

                    filteredAppointments.map(
                      (appointment) => (

                        <tr
                          key={appointment.id}
                          className="border-t hover:bg-gray-50"
                        >

                          <td className="px-5 py-4 font-medium text-blue-600">
                            {appointment.id}
                          </td>

                          <td className="px-5 py-4">

                            <div className="font-medium text-gray-800">
                              {appointment.patient}
                            </div>

                            <div className="text-sm text-gray-500">
                              {appointment.reason}
                            </div>

                          </td>

                          <td className="px-5 py-4 text-gray-600">
                            {appointment.village || "—"}
                          </td>

                          <td className="px-5 py-4 text-gray-600">
                            {appointment.contact || "—"}
                          </td>

                          <td className="px-5 py-4 text-gray-600">
                            {appointment.doctor}
                          </td>

                          <td className="px-5 py-4 text-gray-600">
                            {appointment.date}
                          </td>

                          <td className="px-5 py-4 text-gray-600">
                            {appointment.time}
                          </td>

                          <td className="px-5 py-4">

                            <span className="px-3 py-1 rounded-full bg-purple-100 text-purple-700 font-semibold text-sm">
                              {appointment.tokenNumber || "—"}
                            </span>

                          </td>

                          <td className="px-5 py-4">

                            <span
                              className={`px-3 py-1 rounded-full text-xs font-medium ${appointment.status ===
                                "Confirmed"
                                ? "bg-blue-100 text-blue-700"
                                : appointment.status ===
                                  "Waiting"
                                  ? "bg-orange-100 text-orange-700"
                                  : appointment.status ===
                                    "Completed"
                                    ? "bg-green-100 text-green-700"
                                    : "bg-red-100 text-red-700"
                                }`}
                            >
                              {appointment.status}
                            </span>

                          </td>

                          <td className="px-5 py-4">

                            <div className="flex gap-2">

                              <button
                                onClick={() =>
                                  handleView(
                                    appointment
                                  )
                                }
                                className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
                              >
                                View
                              </button>

                              <button
                                onClick={() =>
                                  handleEdit(
                                    appointment
                                  )
                                }
                                className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                              >
                                Edit
                              </button>

                              <button
                                onClick={() =>
                                  handleCancel(
                                    appointment
                                  )
                                }
                                disabled={
                                  appointment.status ===
                                  "Cancelled" ||
                                  appointment.status ===
                                  "Completed"
                                }
                                className="px-3 py-1 text-sm bg-orange-100 text-orange-700 rounded hover:bg-orange-200 disabled:opacity-40"
                              >
                                Cancel
                              </button>

                              <button
                                onClick={() =>
                                  handleDelete(
                                    appointment
                                  )
                                }
                                className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                              >
                                Delete
                              </button>

                            </div>

                          </td>

                        </tr>

                      )
                    )

                  )}

                </tbody>

              </table>

            </div>

          </div>


          {/* =========================
              Add / Edit Modal
          ========================= */}

          {showForm && (

            <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

              <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl">

                <div className="flex justify-between items-center p-6 border-b">

                  <div>

                    <h2 className="text-xl font-bold text-gray-800">

                      {selectedAppointment
                        ? "Edit Appointment"
                        : "New Appointment"}

                    </h2>

                    <p className="text-sm text-gray-500 mt-1">
                      Enter appointment details
                    </p>

                  </div>

                  <button
                    onClick={resetForm}
                    className="text-2xl text-gray-500"
                  >
                    ×
                  </button>

                </div>

                <form
                  onSubmit={
                    selectedAppointment
                      ? handleUpdate
                      : handleSubmit
                  }
                  className="p-6 space-y-4"
                >

                  {/* Patient Name */}

                  <div>

                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Patient Name
                    </label>

                    <input
                      type="text"
                      name="patient"
                      value={formData.patient}
                      onChange={handleChange}
                      required
                      placeholder="Enter patient name"
                      className="w-full border rounded-lg px-4 py-3"
                    />

                  </div>


                  {/* Village Name */}

                  <div>

                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Village Name
                    </label>

                    <input
                      type="text"
                      name="village"
                      value={formData.village}
                      onChange={handleChange}
                      required
                      placeholder="Enter village name"
                      className="w-full border rounded-lg px-4 py-3"
                    />

                  </div>


                  {/* Contact Number */}

                  <div>

                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Contact Number
                    </label>

                    <input
                      type="tel"
                      name="contact"
                      value={formData.contact}
                      onChange={(e) => {

                        const value =
                          e.target.value.replace(
                            /\D/g,
                            ""
                          )

                        if (value.length <= 10) {

                          setFormData({
                            ...formData,
                            contact: value,
                          })

                        }

                      }}
                      required
                      maxLength="10"
                      placeholder="Enter 10 digit contact number"
                      className="w-full border rounded-lg px-4 py-3"
                    />

                  </div>


                  {/* Doctor */}

                  <div>

                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Doctor
                    </label>

                    <select
                      name="doctor"
                      value={formData.doctor}
                      onChange={handleChange}
                      required
                      className="w-full border rounded-lg px-4 py-3"
                    >

                      <option value="">
                        Select Doctor
                      </option>

                      {doctorChoices.map((doctor) => (

                        <option
                          key={doctor}
                          value={doctor}
                        >
                          {doctor}
                        </option>

                      ))}

                      {formData.doctor &&
                        !doctorChoices.includes(
                          formData.doctor
                        ) && (

                          <option value={formData.doctor}>
                            {formData.doctor}
                          </option>

                        )}

                    </select>

                  </div>


                  {/* Date + Time */}

                  <div className="grid grid-cols-2 gap-4">

                    <div>

                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Date
                      </label>

                      <input
                        type="date"
                        name="date"
                        value={formData.date}
                        onChange={handleChange}
                        required
                        className="w-full border rounded-lg px-4 py-3"
                      />

                    </div>

                    <div>

                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Time
                      </label>

                      <input
                        type="time"
                        name="time"
                        value={formData.time}
                        onChange={handleChange}
                        required
                        className="w-full border rounded-lg px-4 py-3"
                      />

                    </div>

                  </div>


                  {/* Reason */}

                  <div>

                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Reason
                    </label>

                    <textarea
                      name="reason"
                      value={formData.reason}
                      onChange={handleChange}
                      required
                      rows="3"
                      placeholder="Enter appointment reason"
                      className="w-full border rounded-lg px-4 py-3"
                    />

                  </div>


                  {/* Buttons */}

                  <div className="flex justify-end gap-3 pt-3">

                    <button
                      type="button"
                      onClick={resetForm}
                      className="px-5 py-3 border rounded-lg"
                    >
                      Cancel
                    </button>

                    <button
                      type="submit"
                      disabled={saving}
                      className="px-5 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
                    >

                      {saving
                        ? "Saving..."
                        : selectedAppointment
                          ? "Save Changes"
                          : "Book Appointment"}

                    </button>

                  </div>

                </form>

              </div>

            </div>

          )}


          {/* =========================
              View Modal
          ========================= */}

          {showView &&
            selectedAppointment && (

              <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

                <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">

                  <div className="p-6 border-b">

                    <div className="flex justify-between">

                      <div>

                        <h2 className="text-xl font-bold text-gray-800">
                          Appointment Details
                        </h2>

                        <p className="text-blue-600 mt-1">
                          {selectedAppointment.id}
                        </p>

                      </div>

                      <button
                        onClick={() =>
                          setShowView(false)
                        }
                        className="text-2xl text-gray-500"
                      >
                        ×
                      </button>

                    </div>

                  </div>


                  <div className="p-6 space-y-4">

                    <div>

                      <p className="text-sm text-gray-500">
                        Hospital
                      </p>

                      <p className="font-semibold">
                        {selectedHospital.name}
                      </p>

                    </div>


                    <div>

                      <p className="text-sm text-gray-500">
                        Token Number
                      </p>

                      <p className="font-semibold text-purple-600">
                        {selectedAppointment.tokenNumber || "—"}
                      </p>

                    </div>


                    <div>

                      <p className="text-sm text-gray-500">
                        Patient
                      </p>

                      <p className="font-semibold">
                        {selectedAppointment.patient}
                      </p>

                    </div>


                    <div>

                      <p className="text-sm text-gray-500">
                        Village
                      </p>

                      <p className="font-semibold">
                        {selectedAppointment.village || "—"}
                      </p>

                    </div>


                    <div>

                      <p className="text-sm text-gray-500">
                        Contact Number
                      </p>

                      <p className="font-semibold">
                        {selectedAppointment.contact || "—"}
                      </p>

                    </div>


                    <div>

                      <p className="text-sm text-gray-500">
                        Doctor
                      </p>

                      <p className="font-semibold">
                        {selectedAppointment.doctor}
                      </p>

                    </div>


                    <div className="grid grid-cols-2 gap-4">

                      <div>

                        <p className="text-sm text-gray-500">
                          Date
                        </p>

                        <p className="font-semibold">
                          {selectedAppointment.date}
                        </p>

                      </div>


                      <div>

                        <p className="text-sm text-gray-500">
                          Time
                        </p>

                        <p className="font-semibold">
                          {selectedAppointment.time}
                        </p>

                      </div>

                    </div>


                    <div>

                      <p className="text-sm text-gray-500">
                        Reason
                      </p>

                      <p className="font-semibold">
                        {selectedAppointment.reason}
                      </p>

                    </div>


                    <div>

                      <p className="text-sm text-gray-500">
                        Status
                      </p>

                      <p className="font-semibold">
                        {selectedAppointment.status}
                      </p>

                    </div>

                  </div>


                  <div className="p-6 border-t text-right">

                    <button
                      onClick={() =>
                        setShowView(false)
                      }
                      className="px-5 py-2 bg-gray-100 rounded-lg"
                    >
                      Close
                    </button>

                  </div>

                </div>

              </div>

            )}

        </>

      )}

    </div>
  )
}

export default Appointments
