import { useEffect, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useAppointment } from "../assets/context/AppointmentContext.jsx"
import api from "../services/api.js"

function Queue() {

  // =====================================
  // SELECTED HOSPITAL
  // =====================================

  const { selectedHospital } = usePatient()

  // =====================================
  // APPOINTMENT CONTEXT
  // =====================================

  const {
    appointments: appointmentList,
    updateAppointment,
  } = useAppointment()


  // =====================================
  // QUEUE DATA
  // =====================================

  // Offline / demo seed data — kept so the page still works (exactly as
  // before) when the Django queue API is unreachable.
  const fallbackQueue = [

    {
      token: 24,
      patient: "Rahul Kumar",
      village: "Rajaur",
      contact: "9876543210",
      doctor: "Dr. Sharma",
      department: "General Medicine",
      type: "Consultation",
      waiting: "14 min",
      status: "Waiting",
      hospitalId: 1,
    },

    {
      token: 25,
      patient: "Priya Singh",
      village: "Begusarai",
      contact: "9876543211",
      doctor: "Dr. Sharma",
      department: "General Medicine",
      type: "Follow-up",
      waiting: "10 min",
      status: "Waiting",
      hospitalId: 1,
    },

    {
      token: 26,
      patient: "Amit Kumar",
      village: "Barauni",
      contact: "9876543212",
      doctor: "Dr. Verma",
      department: "Cardiology",
      type: "Consultation",
      waiting: "6 min",
      status: "Waiting",
      hospitalId: 2,
    },

    {
      token: 27,
      patient: "Neha Singh",
      village: "Bihat",
      contact: "9876543213",
      doctor: "Dr. Verma",
      department: "Cardiology",
      type: "Consultation",
      waiting: "2 min",
      status: "In Consultation",
      hospitalId: 2,
    },

    {
      token: 28,
      patient: "Ravi Sharma",
      village: "Teghra",
      contact: "9876543214",
      doctor: "Dr. Gupta",
      department: "Orthopedics",
      type: "Consultation",
      waiting: "18 min",
      status: "Waiting",
      hospitalId: 3,
    },

  ]

  // Live queue records. Seeded with the demo data above and replaced by
  // records from Django (encounters.QueueToken) once the API responds.
  const [queue, setQueue] = useState(fallbackQueue)


  // =====================================
  // FILTER STATES
  // =====================================

  const [departmentFilter, setDepartmentFilter] =
    useState("All Departments")

  const [statusFilter, setStatusFilter] =
    useState("All Status")

  const [search, setSearch] =
    useState("")


  // =====================================
  // API STATE (loading / error / retry / feedback)
  // =====================================

  const [loading, setLoading] =
    useState(false)

  const [loadError, setLoadError] =
    useState("")

  const [offlineMode, setOfflineMode] =
    useState(false)

  const [actionError, setActionError] =
    useState("")

  const [successMessage, setSuccessMessage] =
    useState("")

  const [reloadToken, setReloadToken] =
    useState(0)


  // =====================================
  // DJANGO QUEUETOKEN → QUEUE ROW
  // =====================================

  const mapQueueFromApi = (record) => ({

    token:
      record.token_number,

    patient:
      record.patient_name ||
      "Patient",

    village:
      "",

    contact:
      record.patient_phone ||
      "",

    doctor:
      record.doctor_name ||
      "",

    department:
      record.department ||
      "General",

    type:
      record.visit_type ||
      "OPD",

    waiting:
      String(record.status || "")
        .toLowerCase() === "waiting"
        ? `${record.waiting_minutes ?? 0} min`
        : "Now",

    status:
      record.status ||
      "Waiting",

    hospitalId:
      record.hospital,

    appointmentId:
      record.appointment
        ? `A${String(record.appointment).padStart(3, "0")}`
        : undefined,

    appointmentApiId:
      record.appointment,

    apiId:
      record.id,
  })


  // =====================================
  // LOAD QUEUE FROM DJANGO
  // =====================================

  useEffect(() => {

    let cancelled = false

    const loadQueue = async () => {

      if (!selectedHospital) {
        return
      }

      setLoading(true)
      setLoadError("")

      try {

        const data =
          await api.queue.list(
            selectedHospital.id
          )

        if (cancelled) {
          return
        }

        const records = Array.isArray(data)
          ? data
          : data?.results || []

        setQueue(
          records.map(mapQueueFromApi)
        )

        setOfflineMode(false)

      } catch (error) {

        if (cancelled) {
          return
        }

        // Keep the existing (demo/context) rows visible and fall back to
        // offline behaviour instead of breaking the page.
        setLoadError(
          error.message ||
          "Failed to load the queue."
        )

        setOfflineMode(true)

      } finally {

        if (!cancelled) {
          setLoading(false)
        }

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
  const issueableAppointments = (
    appointmentList || []
  ).filter(
    (appointment) =>
      appointment.apiId &&
      appointment.status !== "Cancelled" &&
      appointment.status !== "Completed" &&
      !queue.some(
        (item) =>
          String(item.appointmentApiId) ===
          String(appointment.apiId)
      )
  )


  const generateToken = async () => {

    setActionError("")
    setSuccessMessage("")

    if (offlineMode) {

      setActionError(
        "Cannot generate tokens while offline."
      )

      return

    }

    if (issueableAppointments.length === 0) {

      alert(
        "No appointment is waiting for a token."
      )

      return

    }

    const nextAppointment =
      issueableAppointments[0]

    try {

      // One server-side call: Appointment → (reused/created) Visit →
      // QueueToken with a token_number allocated by Django.
      const token =
        await api.queue.issue(
          nextAppointment.apiId
        )

      setSuccessMessage(
        `Token #${token.token_number} generated for ${nextAppointment.patient || "patient"}.`
      )

      setReloadToken(
        (value) => value + 1
      )

    } catch (error) {

      setActionError(
        error.message ||
        "Failed to generate a token."
      )

    }
  }


  // =====================================
  // APPOINTMENTS → QUEUE
  // =====================================

  const appointmentQueue = appointmentList
    .filter(
      (appointment) =>
        appointment.status !== "Cancelled" &&
        appointment.status !== "Completed"
    )
    .map((appointment) => {

      let queueStatus = "Waiting"

      if (
        appointment.status ===
        "In Consultation"
      ) {
        queueStatus = "In Consultation"
      }

      if (
        appointment.status ===
        "Skipped"
      ) {
        queueStatus = "Skipped"
      }

      return {
        token:
          appointment.tokenNumber ||
          appointment.id,

        patient:
          appointment.patient ||
          appointment.patientName ||
          "Patient",

        village:
          appointment.village ||
          "",

        contact:
          appointment.contact ||
          "",

        doctor:
          appointment.doctor ||
          "",

        department:
          appointment.department ||
          appointment.reason ||
          "General",

        type:
          "Appointment",

        waiting:
          queueStatus ===
            "Waiting"
            ? "Waiting"
            : "Now",

        status:
          queueStatus,

        hospitalId:
          appointment.hospitalId,

        appointmentId:
          appointment.id,
      }
    })


  // =====================================
  // COMBINE OLD QUEUE + APPOINTMENT QUEUE
  // =====================================

  const allQueue = [
    ...queue,

    ...appointmentQueue.filter(
      (appointmentItem) =>
        !queue.some(
          (queueItem) =>
            String(queueItem.token) ===
            String(appointmentItem.token) &&
            String(queueItem.hospitalId) ===
            String(appointmentItem.hospitalId)
        )
    ),
  ]


  // =====================================
  // HOSPITAL QUEUE
  // =====================================

  const hospitalQueue = selectedHospital
    ? allQueue.filter(
      (item) =>
        String(item.hospitalId) ===
        String(selectedHospital.id)
    )
    : []


  // =====================================
  // SEARCH + FILTER
  // =====================================

  const filteredQueue =
    hospitalQueue.filter(
      (item) => {

        const searchText =
          search.toLowerCase()


        const matchesSearch =

          String(item.patient || "")
            .toLowerCase()
            .includes(searchText)

          ||

          String(item.doctor || "")
            .toLowerCase()
            .includes(searchText)

          ||

          String(item.token || "")
            .toLowerCase()
            .includes(searchText)


        const matchesDepartment =

          departmentFilter ===
          "All Departments"

          ||

          item.department ===
          departmentFilter


        const matchesStatus =

          statusFilter ===
          "All Status"

          ||

          item.status ===
          statusFilter


        return (
          matchesSearch &&
          matchesDepartment &&
          matchesStatus
        )

      }
    )


  // =====================================
  // STATISTICS
  // =====================================

  const waitingCount =
    hospitalQueue.filter(
      (item) =>
        item.status ===
        "Waiting"
    ).length


  const consultationCount =
    hospitalQueue.filter(
      (item) =>
        item.status ===
        "In Consultation"
    ).length


  const completedCount =
    hospitalQueue.filter(
      (item) =>
        item.status ===
        "Completed"
    ).length


  const skippedCount =
    hospitalQueue.filter(
      (item) =>
        item.status ===
        "Skipped"
    ).length


  // =====================================
  // CURRENT TOKEN
  // =====================================

  const currentPatient =
    hospitalQueue.find(
      (item) =>
        item.status ===
        "In Consultation"
    )


  // =====================================
  // UPDATE APPOINTMENT STATUS
  // =====================================

  const updateRelatedAppointment = (
    queueItem,
    status
  ) => {

    // Keep the shared AppointmentContext in sync (existing behaviour).
    if (queueItem.appointmentId) {

      updateAppointment(
        queueItem.appointmentId,
        {
          status: status,
        }
      )

    }

    // Also persist the status on the Django appointment when the queue row
    // is backed by a real record. Failures here are non-fatal: the queue
    // itself (QueueToken) is the source of truth for this page.
    if (queueItem.appointmentApiId) {

      api.appointments
        .patch(
          queueItem.appointmentApiId,
          {
            status: status,
          }
        )
        .catch(() => { })

    }
  }


  // =====================================
  // CALL NEXT PATIENT
  // =====================================

  const callNextPatient = async () => {

    const nextPatient =
      hospitalQueue.find(
        (item) =>
          item.status ===
          "Waiting"
      )


    if (!nextPatient) {

      alert(
        "No waiting patient in the queue."
      )

      return

    }


    setActionError("")
    setSuccessMessage("")


    // Ask Django to advance the queue (completes the token currently being
    // served and calls the next waiting token, persisted server-side).
    if (!offlineMode) {

      try {

        await api.queue.callNext(
          selectedHospital.id
        )

        setSuccessMessage(
          `Called token #${nextPatient.token}.`
        )

      } catch (error) {

        setActionError(
          error.message ||
          "Failed to call the next patient."
        )

      }

    }


    setQueue((prevQueue) =>

      prevQueue.map(
        (item) =>

          String(item.token) ===
            String(nextPatient.token) &&
            String(item.hospitalId) ===
            String(selectedHospital.id)

            ? {
              ...item,
              status:
                "In Consultation",
              waiting:
                "Now",
            }

            : item
      )

    )

    updateRelatedAppointment(
      nextPatient,
      "In Consultation"
    )


    setReloadToken(
      (value) => value + 1
    )
  }


  // =====================================
  // CALL SPECIFIC PATIENT
  // =====================================

  const callPatient = async (token) => {

    const selectedQueuePatient =
      hospitalQueue.find(
        (item) =>
          String(item.token) ===
          String(token)
      )


    setActionError("")
    setSuccessMessage("")


    // Persist the "called" status on the QueueToken when this row is a real
    // API record. Demo/context rows still update locally below.
    if (
      selectedQueuePatient &&
      selectedQueuePatient.apiId &&
      !offlineMode
    ) {

      try {

        await api.queue.call(
          selectedQueuePatient.apiId
        )

        setSuccessMessage(
          `Token #${token} called.`
        )

      } catch (error) {

        setActionError(
          error.message ||
          "Failed to call this patient."
        )

      }

    }


    setQueue((prevQueue) =>

      prevQueue.map(
        (item) =>

          String(item.token) ===
            String(token) &&
            String(item.hospitalId) ===
            String(selectedHospital.id)

            ? {
              ...item,
              status:
                "In Consultation",
              waiting:
                "Now",
            }

            : item
      )

    )


    if (selectedQueuePatient) {

      updateRelatedAppointment(
        selectedQueuePatient,
        "In Consultation"
      )

    }


    setReloadToken(
      (value) => value + 1
    )
  }


  // =====================================
  // COMPLETE PATIENT
  // =====================================

  const completePatient = async (
    token
  ) => {

    const selectedQueuePatient =
      hospitalQueue.find(
        (item) =>
          String(item.token) ===
          String(token)
      )


    setActionError("")
    setSuccessMessage("")


    if (
      selectedQueuePatient &&
      selectedQueuePatient.apiId &&
      !offlineMode
    ) {

      try {

        await api.queue.complete(
          selectedQueuePatient.apiId
        )

        setSuccessMessage(
          `Token #${token} completed.`
        )

      } catch (error) {

        setActionError(
          error.message ||
          "Failed to complete this patient."
        )

      }

    }


    setQueue((prevQueue) =>

      prevQueue.map(
        (item) =>

          String(item.token) ===
            String(token) &&
            String(item.hospitalId) ===
            String(selectedHospital.id)

            ? {
              ...item,
              status:
                "Completed",
            }

            : item
      )

    )


    if (selectedQueuePatient) {

      updateRelatedAppointment(
        selectedQueuePatient,
        "Completed"
      )

    }


    setReloadToken(
      (value) => value + 1
    )
  }


  // =====================================
  // SKIP PATIENT
  // =====================================

  const skipPatient = async (
    token
  ) => {

    const selectedQueuePatient =
      hospitalQueue.find(
        (item) =>
          String(item.token) ===
          String(token)
      )


    setActionError("")
    setSuccessMessage("")


    if (
      selectedQueuePatient &&
      selectedQueuePatient.apiId &&
      !offlineMode
    ) {

      try {

        await api.queue.skip(
          selectedQueuePatient.apiId
        )

        setSuccessMessage(
          `Token #${token} skipped.`
        )

      } catch (error) {

        setActionError(
          error.message ||
          "Failed to skip this patient."
        )

      }

    }


    setQueue((prevQueue) =>

      prevQueue.map(
        (item) =>

          String(item.token) ===
            String(token) &&
            String(item.hospitalId) ===
            String(selectedHospital.id)

            ? {
              ...item,
              status:
                "Skipped",
            }

            : item
      )

    )


    if (selectedQueuePatient) {

      updateRelatedAppointment(
        selectedQueuePatient,
        "Skipped"
      )

    }


    setReloadToken(
      (value) => value + 1
    )
  }


  // =====================================
  // STATUS COLOR
  // =====================================

  const getStatusClass = (
    status
  ) => {

    if (
      status ===
      "Waiting"
    ) {

      return "bg-orange-100 text-orange-700"

    }


    if (
      status ===
      "In Consultation"
    ) {

      return "bg-blue-100 text-blue-700"

    }


    if (
      status ===
      "Completed"
    ) {

      return "bg-green-100 text-green-700"

    }


    if (
      status ===
      "Skipped"
    ) {

      return "bg-gray-100 text-gray-700"

    }


    return "bg-gray-100 text-gray-700"

  }


  // =====================================
  // NO HOSPITAL SELECTED
  // =====================================

  if (!selectedHospital) {

    return (

      <div className="space-y-6">

        <div>

          <p className="text-blue-600 font-semibold text-sm">
            QUEUE MANAGEMENT
          </p>

          <h1 className="text-3xl font-bold text-gray-800 mt-1">
            Queue Management
          </h1>

        </div>


        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">

          <div className="text-5xl mb-4">
            🏥
          </div>

          <h2 className="text-xl font-bold text-gray-800">
            Select a Hospital
          </h2>

          <p className="text-gray-500 mt-2">
            Select a hospital from the header to view its patient queue.
          </p>

        </div>

      </div>

    )
  }


  return (

    <div>


      {/* =====================================
          HEADER
      ===================================== */}

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">

        <div>

          <p className="text-blue-600 font-semibold text-sm">
            QUEUE MANAGEMENT
          </p>

          <h1 className="text-3xl font-bold text-gray-800 mt-1">
            Queue Management
          </h1>

          <p className="text-gray-500 mt-1">
            Manage patient tokens and consultation queue.
          </p>

        </div>


        <div className="flex items-center gap-3">

          <button
            onClick={
              generateToken
            }
            className="bg-emerald-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-emerald-700 transition"
          >
            🎟️ Generate Token
          </button>


          <button
            onClick={
              callNextPatient
            }
            className="bg-blue-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-blue-700 transition"
          >
            📢 Call Next Patient
          </button>

        </div>

      </div>


      {/* =====================================
          SELECTED HOSPITAL
      ===================================== */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        <div className="flex items-center gap-4">

          <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">
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

      </div>


      {/* =====================================
          API STATUS FEEDBACK
      ===================================== */}

      {successMessage && (

        <div className="bg-green-50 border border-green-200 text-green-700 rounded-2xl p-4 mb-6 flex items-center justify-between">

          <span className="font-medium">
            {successMessage}
          </span>

          <button
            onClick={() =>
              setSuccessMessage("")
            }
            className="text-green-700 text-sm"
          >
            Dismiss
          </button>

        </div>

      )}


      {actionError && (

        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-4 mb-6 flex items-center justify-between">

          <span className="font-medium">
            {actionError}
          </span>

          <button
            onClick={() =>
              setActionError("")
            }
            className="text-red-700 text-sm"
          >
            Dismiss
          </button>

        </div>

      )}


      {offlineMode && (

        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-2xl p-4 mb-6 flex items-center justify-between">

          <span className="font-medium">

            {loadError ||
              "Could not reach the server. Showing saved queue data."}

          </span>

          <button
            onClick={() =>
              setReloadToken(
                (value) => value + 1
              )
            }
            className="bg-yellow-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            Retry
          </button>

        </div>

      )}


      {loading && (

        <div className="bg-white border border-gray-100 text-gray-500 rounded-2xl p-4 mb-6 text-center">

          Loading queue from server...

        </div>

      )}


      {/* =====================================
          STATISTICS
      ===================================== */}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-6">


        {/* Current Token */}

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Current Token
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-blue-600">

              {currentPatient
                ? `#${currentPatient.token}`
                : "--"}

            </h2>

            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-xl">
              🎫
            </div>

          </div>

        </div>


        {/* Waiting */}

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Waiting Patients
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-orange-500">
              {waitingCount}
            </h2>

            <div className="w-12 h-12 rounded-xl bg-orange-100 flex items-center justify-center text-xl">
              ⏳
            </div>

          </div>

        </div>


        {/* Consultation */}

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            In Consultation
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-blue-600">
              {consultationCount}
            </h2>

            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-xl">
              👨‍⚕️
            </div>

          </div>

        </div>


        {/* Completed */}

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Completed
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-green-600">
              {completedCount}
            </h2>

            <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center text-xl">
              ✓
            </div>

          </div>

        </div>

      </div>


      {/* =====================================
          CURRENT QUEUE HIGHLIGHT
      ===================================== */}

      {currentPatient && (

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5">

            <div>

              <p className="text-sm text-gray-500">
                Currently Serving
              </p>

              <h2 className="text-4xl font-bold text-blue-600 mt-2">
                Token #{currentPatient.token}
              </h2>

              <p className="text-gray-700 font-medium mt-2">
                {currentPatient.patient}
              </p>

              <p className="text-sm text-gray-500">
                {currentPatient.doctor}
                {" • "}
                {currentPatient.department}
              </p>

            </div>


            <div className="bg-blue-50 rounded-2xl p-6 text-center">

              <p className="text-sm text-gray-500">
                Status
              </p>

              <p className="text-blue-700 font-bold mt-1">
                In Consultation
              </p>

            </div>

          </div>

        </div>

      )}


      {/* =====================================
          FILTERS
      ===================================== */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">


          <input
            type="text"
            placeholder="Search patient, doctor or token..."
            value={search}
            onChange={(e) =>
              setSearch(
                e.target.value
              )
            }
            className="border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
          />


          <select
            value={
              departmentFilter
            }
            onChange={(e) =>
              setDepartmentFilter(
                e.target.value
              )
            }
            className="border border-gray-300 rounded-xl px-4 py-3"
          >

            <option>
              All Departments
            </option>

            <option>
              General Medicine
            </option>

            <option>
              Cardiology
            </option>

            <option>
              Orthopedics
            </option>

            <option>
              Neurology
            </option>

          </select>


          <select
            value={
              statusFilter
            }
            onChange={(e) =>
              setStatusFilter(
                e.target.value
              )
            }
            className="border border-gray-300 rounded-xl px-4 py-3"
          >

            <option>
              All Status
            </option>

            <option>
              Waiting
            </option>

            <option>
              In Consultation
            </option>

            <option>
              Completed
            </option>

            <option>
              Skipped
            </option>

          </select>

        </div>

      </div>


      {/* =====================================
          QUEUE TABLE
      ===================================== */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

        <div className="p-6 border-b">

          <h2 className="text-xl font-bold text-gray-800">
            {selectedHospital.name} Patient Queue
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            {filteredQueue.length} patient(s) in queue
          </p>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-gray-50">

              <tr>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Token
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Patient
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Village
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Contact
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Doctor
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Department
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Type
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Waiting
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Status
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Actions
                </th>

              </tr>

            </thead>


            <tbody>

              {filteredQueue.length === 0 ? (

                <tr>

                  <td
                    colSpan="10"
                    className="text-center py-12 text-gray-500"
                  >

                    <div className="text-4xl mb-3">
                      🎫
                    </div>

                    <p className="font-semibold">
                      No patients found
                    </p>

                    <p className="text-sm mt-1">
                      No matching patients in {selectedHospital.name}.
                    </p>

                  </td>

                </tr>

              ) : (

                filteredQueue.map(
                  (item, index) => (

                    <tr
                      key={`${item.token}-${item.hospitalId}-${index}`}
                      className="border-t hover:bg-gray-50 transition"
                    >


                      {/* Token */}

                      <td className="px-6 py-4">

                        <span className="font-bold text-blue-600">
                          #{item.token}
                        </span>

                      </td>


                      {/* Patient */}

                      <td className="px-6 py-4">

                        <p className="font-semibold text-gray-800">
                          {item.patient}
                        </p>

                      </td>


                      {/* Village */}

                      <td className="px-6 py-4 text-gray-600">
                        {item.village || "—"}
                      </td>


                      {/* Contact */}

                      <td className="px-6 py-4 text-gray-600">
                        {item.contact || "—"}
                      </td>


                      {/* Doctor */}

                      <td className="px-6 py-4 text-gray-600">
                        {item.doctor}
                      </td>


                      {/* Department */}

                      <td className="px-6 py-4 text-gray-600">
                        {item.department}
                      </td>


                      {/* Type */}

                      <td className="px-6 py-4 text-gray-600">
                        {item.type}
                      </td>


                      {/* Waiting */}

                      <td className="px-6 py-4 text-gray-600">
                        {item.waiting}
                      </td>


                      {/* Status */}

                      <td className="px-6 py-4">

                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                            item.status
                          )}`}
                        >

                          {item.status}

                        </span>

                      </td>


                      {/* Actions */}

                      <td className="px-6 py-4">

                        <div className="flex gap-2 flex-wrap">


                          {item.status ===
                            "Waiting" && (

                              <button
                                onClick={() =>
                                  callPatient(
                                    item.token
                                  )
                                }
                                className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100"
                              >
                                Call
                              </button>

                            )}


                          {item.status ===
                            "In Consultation" && (

                              <button
                                onClick={() =>
                                  completePatient(
                                    item.token
                                  )
                                }
                                className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100"
                              >
                                Complete
                              </button>

                            )}


                          {item.status ===
                            "Waiting" && (

                              <button
                                onClick={() =>
                                  skipPatient(
                                    item.token
                                  )
                                }
                                className="px-3 py-2 text-sm bg-orange-50 text-orange-700 rounded-lg hover:bg-orange-100"
                              >
                                Skip
                              </button>

                            )}

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


      {/* =====================================
          QUEUE SUMMARY
      ===================================== */}

      <div className="bg-blue-50 border border-blue-100 rounded-2xl p-5 mt-6">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">

          <div>

            <p className="font-semibold text-blue-800">
              Queue Summary
            </p>

            <p className="text-sm text-blue-600 mt-1">
              {selectedHospital.name}
            </p>

          </div>


          <div className="flex gap-5 text-sm flex-wrap">

            <span className="text-orange-600">
              Waiting:{" "}
              <strong>
                {waitingCount}
              </strong>
            </span>

            <span className="text-blue-600">
              Consulting:{" "}
              <strong>
                {consultationCount}
              </strong>
            </span>

            <span className="text-green-600">
              Completed:{" "}
              <strong>
                {completedCount}
              </strong>
            </span>

            <span className="text-gray-600">
              Skipped:{" "}
              <strong>
                {skippedCount}
              </strong>
            </span>

          </div>

        </div>

      </div>


    </div>
  )
}


export default Queue