import { useEffect, useMemo, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"

// =========================================================
// DOCTOR CONSULTATION
//
// This is a NEW screen added for the clinical/consultation workflow.
// It is intentionally separate from the Nurse / Compounder pages so those
// modules stay exactly as they were.
//
// Everything on this page is backed by the EXISTING Django clinical models:
//   VitalSign      -> /api/clinical/vitals/
//   Diagnosis      -> /api/clinical/diagnoses/
//   ClinicalNote   -> /api/clinical/clinical-notes/
//   ServiceOrder   -> /api/clinical/service-orders/
//
// Every clinical record hangs off an encounters.Visit, so a Visit is selected
// first and the clinical tabs then read/write the records for that visit.
// =========================================================

// Values accepted by Diagnosis.diagnosis_type (free text on the model, but we
// offer the common ones so the doctor does not have to type them).
const DIAGNOSIS_TYPES = [
  "Provisional",
  "Differential",
  "Final",
  "Confirmed",
]

// Values accepted by ServiceOrder.status (defaults to "Pending" on the model).
const ORDER_STATUSES = ["Pending", "Completed", "Cancelled"]

// Values accepted by Visit.status (defaults to "Waiting" on the model).
const VISIT_STATUSES = [
  "Waiting",
  "In Consultation",
  "Completed",
  "Cancelled",
]

// ---------------------------------------------------------
// Small formatting / mapping helpers
// ---------------------------------------------------------

const formatDateTime = (value) => {
  if (!value) {
    return "—"
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return "—"
  }

  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

const formatDay = (value) => {
  if (!value) {
    return "—"
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return "—"
  }

  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}

// Convert the raw backend Visit record into the flat shape the UI renders.
const mapVisitFromApi = (record) => ({
  apiId: record.id,
  patientName: record.patient_name || "Patient",
  doctorName: record.doctor_name || "Unassigned",
  patientApiId: record.patient || null,
  doctorApiId: record.doctor || null,
  visitType: record.visit_type || "OPD",
  chiefComplaint: record.chief_complaint || "",
  status: record.status || "Waiting",
  visitDate: record.visit_date || null,
  visitDay: formatDay(record.visit_date),
  hospitalId: record.hospital || null,
})

const mapVitalFromApi = (record) => ({
  apiId: record.id,
  weight: record.weight,
  height: record.height,
  systolicBp: record.systolic_bp,
  diastolicBp: record.diastolic_bp,
  temperature: record.temperature,
  respiratoryRate: record.respiratory_rate,
  heartRate: record.heart_rate,
  bloodSugar: record.blood_sugar,
  spo2: record.spo2,
  comments: record.comments || "",
  recordedAt: record.recorded_at || null,
})

const mapDiagnosisFromApi = (record) => ({
  apiId: record.id,
  name: record.name || "",
  icd10Code: record.icd10_code || "",
  diagnosisType: record.diagnosis_type || "Provisional",
  remarks: record.remarks || "",
  createdAt: record.created_at || null,
})

const mapNoteFromApi = (record) => ({
  apiId: record.id,
  note: record.note || "",
  doctorApiId: record.doctor || null,
  createdAt: record.created_at || null,
})

const mapOrderFromApi = (record) => ({
  apiId: record.id,
  serviceName: record.service_name || "",
  quantity: record.quantity ?? 1,
  status: record.status || "Pending",
  remarks: record.remarks || "",
  createdAt: record.created_at || null,
})

// Normalise a list response that may be a plain array or a paginated
// { count, next, previous, results } object.
const readResults = (data) =>
  Array.isArray(data) ? data : data?.results || []

// Turn an input string into a number or null (DRF numeric fields reject "").
const num = (value) => {
  if (value === "" || value === null || value === undefined) {
    return null
  }

  const parsed = Number(value)

  return Number.isNaN(parsed) ? null : parsed
}

// Display helper: show a value or an em dash.
const show = (value, suffix = "") => {
  if (value === null || value === undefined || value === "") {
    return "—"
  }

  return `${value}${suffix}`
}

// ---------------------------------------------------------
// Empty form templates
// ---------------------------------------------------------

const emptyVitalForm = {
  weight: "",
  height: "",
  systolicBp: "",
  diastolicBp: "",
  temperature: "",
  respiratoryRate: "",
  heartRate: "",
  bloodSugar: "",
  spo2: "",
  comments: "",
}

const emptyDiagnosisForm = {
  name: "",
  icd10Code: "",
  diagnosisType: "Provisional",
  remarks: "",
}

const emptyNoteForm = {
  note: "",
}

const emptyOrderForm = {
  serviceName: "",
  quantity: "1",
  status: "Pending",
  remarks: "",
}

function Consultation() {
  const { selectedHospital } = usePatient()

  // ---------------------------------------------------------
  // Visit list state
  // ---------------------------------------------------------
  const [visits, setVisits] = useState([])
  const [loadingVisits, setLoadingVisits] = useState(false)
  const [visitsError, setVisitsError] = useState("")
  const [selectedVisitId, setSelectedVisitId] = useState("")

  // ---------------------------------------------------------
  // Clinical record state (for the selected visit)
  // ---------------------------------------------------------
  const [vitals, setVitals] = useState([])
  const [diagnoses, setDiagnoses] = useState([])
  const [notes, setNotes] = useState([])
  const [orders, setOrders] = useState([])
  const [loadingClinical, setLoadingClinical] = useState(false)
  const [clinicalError, setClinicalError] = useState("")

  // ---------------------------------------------------------
  // Feedback + misc UI state
  // ---------------------------------------------------------
  const [activeTab, setActiveTab] = useState("vitals")
  const [successMessage, setSuccessMessage] = useState("")
  const [errorMessage, setErrorMessage] = useState("")
  const [reloadToken, setReloadToken] = useState(0)

  // ---------------------------------------------------------
  // Forms + which record is being edited (null = creating)
  // ---------------------------------------------------------
  const [vitalForm, setVitalForm] = useState(emptyVitalForm)
  const [editingVital, setEditingVital] = useState(null)
  const [savingVitals, setSavingVitals] = useState(false)

  const [diagnosisForm, setDiagnosisForm] = useState(emptyDiagnosisForm)
  const [editingDiagnosis, setEditingDiagnosis] = useState(null)
  const [savingDiagnosis, setSavingDiagnosis] = useState(false)

  const [noteForm, setNoteForm] = useState(emptyNoteForm)
  const [editingNote, setEditingNote] = useState(null)
  const [savingNote, setSavingNote] = useState(false)

  const [orderForm, setOrderForm] = useState(emptyOrderForm)
  const [editingOrder, setEditingOrder] = useState(null)
  const [savingOrder, setSavingOrder] = useState(false)

  const [savingVisit, setSavingVisit] = useState(false)

  const selectedVisit = useMemo(
    () =>
      visits.find(
        (visit) => String(visit.apiId) === String(selectedVisitId)
      ) || null,
    [visits, selectedVisitId]
  )

  // ---------------------------------------------------------
  // LOAD VISITS for the selected hospital
  // ---------------------------------------------------------
  useEffect(() => {
    let cancelled = false

    const loadVisits = async () => {
      if (!selectedHospital) {
        setVisits([])
        setSelectedVisitId("")
        return
      }

      setLoadingVisits(true)
      setVisitsError("")

      try {
        const data = await api.visits.list(selectedHospital.id)

        if (cancelled) {
          return
        }

        const mapped = readResults(data).map(mapVisitFromApi)

        setVisits(mapped)

        // Keep the current selection if it still exists, otherwise default
        // to the first visit so the clinical tabs have something to show.
        setSelectedVisitId((current) => {
          const stillThere = mapped.some(
            (visit) => String(visit.apiId) === String(current)
          )

          if (stillThere) {
            return current
          }

          return mapped.length ? String(mapped[0].apiId) : ""
        })
      } catch (error) {
        if (cancelled) {
          return
        }

        setVisits([])
        setVisitsError(
          error.message || "Failed to load visits."
        )
      } finally {
        if (!cancelled) {
          setLoadingVisits(false)
        }
      }
    }

    loadVisits()

    return () => {
      cancelled = true
    }
  }, [selectedHospital, reloadToken])

  // ---------------------------------------------------------
  // LOAD CLINICAL RECORDS for the selected visit
  // ---------------------------------------------------------
  useEffect(() => {
    let cancelled = false

    const loadClinical = async () => {
      if (!selectedVisitId) {
        setVitals([])
        setDiagnoses([])
        setNotes([])
        setOrders([])
        return
      }

      setLoadingClinical(true)
      setClinicalError("")

      // Fetch all four clinical collections for the visit in parallel. If one
      // fails we still keep the others rather than blanking the whole page.
      const [vitalsResult, diagnosesResult, notesResult, ordersResult] =
        await Promise.allSettled([
          api.clinical.vitals.list(selectedVisitId),
          api.clinical.diagnoses.list(selectedVisitId),
          api.clinical.notes.list(selectedVisitId),
          api.clinical.serviceOrders.list(selectedVisitId),
        ])

      if (cancelled) {
        return
      }

      if (vitalsResult.status === "fulfilled") {
        setVitals(readResults(vitalsResult.value).map(mapVitalFromApi))
      } else {
        setVitals([])
      }

      if (diagnosesResult.status === "fulfilled") {
        setDiagnoses(
          readResults(diagnosesResult.value).map(mapDiagnosisFromApi)
        )
      } else {
        setDiagnoses([])
      }

      if (notesResult.status === "fulfilled") {
        setNotes(readResults(notesResult.value).map(mapNoteFromApi))
      } else {
        setNotes([])
      }

      if (ordersResult.status === "fulfilled") {
        setOrders(readResults(ordersResult.value).map(mapOrderFromApi))
      } else {
        setOrders([])
      }

      const failures = [
        vitalsResult,
        diagnosesResult,
        notesResult,
        ordersResult,
      ].filter((result) => result.status === "rejected")

      if (failures.length) {
        setClinicalError(
          failures[0].reason?.message ||
          "Some clinical records could not be loaded."
        )
      }

      setLoadingClinical(false)
    }

    loadClinical()

    return () => {
      cancelled = true
    }
  }, [selectedVisitId, reloadToken])

  // ---------------------------------------------------------
  // Auto-dismiss the success banner
  // ---------------------------------------------------------
  useEffect(() => {
    if (!successMessage) {
      return undefined
    }

    const timer = setTimeout(() => {
      setSuccessMessage("")
    }, 3000)

    return () => clearTimeout(timer)
  }, [successMessage])

  // ---------------------------------------------------------
  // Reset the "add" forms whenever the visit changes
  // ---------------------------------------------------------
  useEffect(() => {
    setVitalForm(emptyVitalForm)
    setEditingVital(null)
    setDiagnosisForm(emptyDiagnosisForm)
    setEditingDiagnosis(null)
    setNoteForm(emptyNoteForm)
    setEditingNote(null)
    setOrderForm(emptyOrderForm)
    setEditingOrder(null)
    setErrorMessage("")
  }, [selectedVisitId])

  const refresh = () => setReloadToken((token) => token + 1)

  // =========================================================
  // VITALS
  // =========================================================

  const validateVitals = () => {
    const checks = [
      ["weight", 0, 500, "Weight"],
      ["height", 0, 300, "Height"],
      ["systolicBp", 50, 300, "Systolic BP"],
      ["diastolicBp", 30, 200, "Diastolic BP"],
      ["temperature", 30, 45, "Temperature"],
      ["respiratoryRate", 5, 80, "Respiratory rate"],
      ["heartRate", 20, 250, "Pulse / heart rate"],
      ["bloodSugar", 0, 1000, "Blood sugar"],
      ["spo2", 50, 100, "SpO2"],
    ]

    for (const [field, min, max, label] of checks) {
      const value = vitalForm[field]

      if (value === "" || value === null || value === undefined) {
        continue
      }

      const parsed = Number(value)

      if (Number.isNaN(parsed)) {
        return `${label} must be a number.`
      }

      if (parsed < min || parsed > max) {
        return `${label} must be between ${min} and ${max}.`
      }
    }

    const hasAnyValue = checks.some(
      ([field]) =>
        vitalForm[field] !== "" &&
        vitalForm[field] !== null &&
        vitalForm[field] !== undefined
    )

    if (!hasAnyValue) {
      return "Enter at least one vital sign value."
    }

    return ""
  }

  const handleSaveVitals = async (event) => {
    event.preventDefault()

    if (savingVitals || !selectedVisitId) {
      return
    }

    const validationError = validateVitals()

    if (validationError) {
      setErrorMessage(validationError)
      return
    }

    setSavingVitals(true)
    setErrorMessage("")

    const payload = {
      visit: Number(selectedVisitId),
      weight: num(vitalForm.weight),
      height: num(vitalForm.height),
      systolic_bp: num(vitalForm.systolicBp),
      diastolic_bp: num(vitalForm.diastolicBp),
      temperature: num(vitalForm.temperature),
      respiratory_rate: num(vitalForm.respiratoryRate),
      heart_rate: num(vitalForm.heartRate),
      blood_sugar: num(vitalForm.bloodSugar),
      spo2: num(vitalForm.spo2),
      comments: vitalForm.comments.trim(),
    }

    try {
      if (editingVital) {
        const updated = await api.clinical.vitals.update(
          editingVital,
          payload
        )

        setVitals((prev) =>
          prev.map((item) =>
            String(item.apiId) === String(editingVital)
              ? mapVitalFromApi(updated)
              : item
          )
        )

        setSuccessMessage("Vital signs updated.")
      } else {
        const created = await api.clinical.vitals.create(payload)

        setVitals((prev) => [mapVitalFromApi(created), ...prev])
        setSuccessMessage("Vital signs recorded.")
      }

      setVitalForm(emptyVitalForm)
      setEditingVital(null)
    } catch (error) {
      setErrorMessage(
        error.message || "Could not save the vital signs."
      )
    } finally {
      setSavingVitals(false)
    }
  }

  const handleEditVitals = (vital) => {
    setActiveTab("vitals")
    setEditingVital(vital.apiId)
    setErrorMessage("")
    setVitalForm({
      weight: vital.weight ?? "",
      height: vital.height ?? "",
      systolicBp: vital.systolicBp ?? "",
      diastolicBp: vital.diastolicBp ?? "",
      temperature: vital.temperature ?? "",
      respiratoryRate: vital.respiratoryRate ?? "",
      heartRate: vital.heartRate ?? "",
      bloodSugar: vital.bloodSugar ?? "",
      spo2: vital.spo2 ?? "",
      comments: vital.comments || "",
    })
  }

  const handleDeleteVitals = async (vital) => {
    if (!window.confirm("Delete this vital sign record?")) {
      return
    }

    try {
      await api.clinical.vitals.delete(vital.apiId)

      setVitals((prev) =>
        prev.filter(
          (item) => String(item.apiId) !== String(vital.apiId)
        )
      )

      if (String(editingVital) === String(vital.apiId)) {
        setVitalForm(emptyVitalForm)
        setEditingVital(null)
      }

      setSuccessMessage("Vital signs deleted.")
    } catch (error) {
      setErrorMessage(
        error.message || "Could not delete the vital signs."
      )
    }
  }

  // =========================================================
  // DIAGNOSES
  // =========================================================

  const handleSaveDiagnosis = async (event) => {
    event.preventDefault()

    if (savingDiagnosis || !selectedVisitId) {
      return
    }

    if (!diagnosisForm.name.trim()) {
      setErrorMessage("Diagnosis name is required.")
      return
    }

    if (
      diagnosisForm.icd10Code &&
      !/^[A-Za-z][0-9]{2}(\.[0-9A-Za-z]{1,4})?$/.test(
        diagnosisForm.icd10Code.trim()
      )
    ) {
      setErrorMessage(
        "ICD-10 code should look like A09 or A09.9."
      )
      return
    }

    setSavingDiagnosis(true)
    setErrorMessage("")

    const payload = {
      visit: Number(selectedVisitId),
      name: diagnosisForm.name.trim(),
      icd10_code: diagnosisForm.icd10Code.trim(),
      diagnosis_type: diagnosisForm.diagnosisType || "Provisional",
      remarks: diagnosisForm.remarks.trim(),
    }

    try {
      if (editingDiagnosis) {
        const updated = await api.clinical.diagnoses.update(
          editingDiagnosis,
          payload
        )

        setDiagnoses((prev) =>
          prev.map((item) =>
            String(item.apiId) === String(editingDiagnosis)
              ? mapDiagnosisFromApi(updated)
              : item
          )
        )

        setSuccessMessage("Diagnosis updated.")
      } else {
        const created = await api.clinical.diagnoses.create(payload)

        setDiagnoses((prev) => [
          mapDiagnosisFromApi(created),
          ...prev,
        ])
        setSuccessMessage("Diagnosis added.")
      }

      setDiagnosisForm(emptyDiagnosisForm)
      setEditingDiagnosis(null)
    } catch (error) {
      setErrorMessage(
        error.message || "Could not save the diagnosis."
      )
    } finally {
      setSavingDiagnosis(false)
    }
  }

  const handleEditDiagnosis = (diagnosis) => {
    setActiveTab("diagnoses")
    setEditingDiagnosis(diagnosis.apiId)
    setErrorMessage("")
    setDiagnosisForm({
      name: diagnosis.name,
      icd10Code: diagnosis.icd10Code,
      diagnosisType: diagnosis.diagnosisType,
      remarks: diagnosis.remarks,
    })
  }

  const handleDeleteDiagnosis = async (diagnosis) => {
    if (!window.confirm("Delete this diagnosis?")) {
      return
    }

    try {
      await api.clinical.diagnoses.delete(diagnosis.apiId)

      setDiagnoses((prev) =>
        prev.filter(
          (item) => String(item.apiId) !== String(diagnosis.apiId)
        )
      )

      if (String(editingDiagnosis) === String(diagnosis.apiId)) {
        setDiagnosisForm(emptyDiagnosisForm)
        setEditingDiagnosis(null)
      }

      setSuccessMessage("Diagnosis deleted.")
    } catch (error) {
      setErrorMessage(
        error.message || "Could not delete the diagnosis."
      )
    }
  }

  // =========================================================
  // CLINICAL NOTES
  // =========================================================

  const handleSaveNote = async (event) => {
    event.preventDefault()

    if (savingNote || !selectedVisitId) {
      return
    }

    if (!noteForm.note.trim()) {
      setErrorMessage("Note text is required.")
      return
    }

    setSavingNote(true)
    setErrorMessage("")

    const payload = {
      visit: Number(selectedVisitId),
      // Attribute the note to the visit's doctor when one is set.
      doctor: selectedVisit?.doctorApiId || null,
      note: noteForm.note.trim(),
    }

    try {
      if (editingNote) {
        const updated = await api.clinical.notes.update(
          editingNote,
          payload
        )

        setNotes((prev) =>
          prev.map((item) =>
            String(item.apiId) === String(editingNote)
              ? mapNoteFromApi(updated)
              : item
          )
        )

        setSuccessMessage("Clinical note updated.")
      } else {
        const created = await api.clinical.notes.create(payload)

        setNotes((prev) => [mapNoteFromApi(created), ...prev])
        setSuccessMessage("Clinical note added.")
      }

      setNoteForm(emptyNoteForm)
      setEditingNote(null)
    } catch (error) {
      setErrorMessage(
        error.message || "Could not save the clinical note."
      )
    } finally {
      setSavingNote(false)
    }
  }

  const handleEditNote = (note) => {
    setActiveTab("notes")
    setEditingNote(note.apiId)
    setErrorMessage("")
    setNoteForm({ note: note.note })
  }

  const handleDeleteNote = async (note) => {
    if (!window.confirm("Delete this clinical note?")) {
      return
    }

    try {
      await api.clinical.notes.delete(note.apiId)

      setNotes((prev) =>
        prev.filter(
          (item) => String(item.apiId) !== String(note.apiId)
        )
      )

      if (String(editingNote) === String(note.apiId)) {
        setNoteForm(emptyNoteForm)
        setEditingNote(null)
      }

      setSuccessMessage("Clinical note deleted.")
    } catch (error) {
      setErrorMessage(
        error.message || "Could not delete the clinical note."
      )
    }
  }

  // =========================================================
  // SERVICE ORDERS
  // =========================================================

  const handleSaveOrder = async (event) => {
    event.preventDefault()

    if (savingOrder || !selectedVisitId) {
      return
    }

    if (!orderForm.serviceName.trim()) {
      setErrorMessage("Service name is required.")
      return
    }

    const quantity = Number(orderForm.quantity)

    if (!Number.isFinite(quantity) || quantity < 1) {
      setErrorMessage("Quantity must be at least 1.")
      return
    }

    setSavingOrder(true)
    setErrorMessage("")

    const payload = {
      visit: Number(selectedVisitId),
      service_name: orderForm.serviceName.trim(),
      quantity,
      status: orderForm.status || "Pending",
      remarks: orderForm.remarks.trim(),
    }

    try {
      if (editingOrder) {
        const updated = await api.clinical.serviceOrders.update(
          editingOrder,
          payload
        )

        setOrders((prev) =>
          prev.map((item) =>
            String(item.apiId) === String(editingOrder)
              ? mapOrderFromApi(updated)
              : item
          )
        )

        setSuccessMessage("Service order updated.")
      } else {
        const created =
          await api.clinical.serviceOrders.create(payload)

        setOrders((prev) => [mapOrderFromApi(created), ...prev])
        setSuccessMessage("Service order added.")
      }

      setOrderForm(emptyOrderForm)
      setEditingOrder(null)
    } catch (error) {
      setErrorMessage(
        error.message || "Could not save the service order."
      )
    } finally {
      setSavingOrder(false)
    }
  }

  const handleEditOrder = (order) => {
    setActiveTab("orders")
    setEditingOrder(order.apiId)
    setErrorMessage("")
    setOrderForm({
      serviceName: order.serviceName,
      quantity: String(order.quantity ?? 1),
      status: order.status,
      remarks: order.remarks,
    })
  }

  const handleDeleteOrder = async (order) => {
    if (!window.confirm("Delete this service order?")) {
      return
    }

    try {
      await api.clinical.serviceOrders.delete(order.apiId)

      setOrders((prev) =>
        prev.filter(
          (item) => String(item.apiId) !== String(order.apiId)
        )
      )

      if (String(editingOrder) === String(order.apiId)) {
        setOrderForm(emptyOrderForm)
        setEditingOrder(null)
      }

      setSuccessMessage("Service order deleted.")
    } catch (error) {
      setErrorMessage(
        error.message || "Could not delete the service order."
      )
    }
  }

  // =========================================================
  // VISIT STATUS
  // =========================================================

  const handleVisitStatusChange = async (newStatus) => {
    if (!selectedVisit || savingVisit) {
      return
    }

    setSavingVisit(true)
    setErrorMessage("")

    try {
      await api.visits.patch(selectedVisit.apiId, {
        status: newStatus,
      })

      setVisits((prev) =>
        prev.map((visit) =>
          String(visit.apiId) === String(selectedVisit.apiId)
            ? { ...visit, status: newStatus }
            : visit
        )
      )

      setSuccessMessage("Visit status updated.")
    } catch (error) {
      setErrorMessage(
        error.message || "Could not update the visit status."
      )
    } finally {
      setSavingVisit(false)
    }
  }

  // =========================================================
  // RENDER
  // =========================================================

  const tabs = [
    { id: "vitals", label: "Vitals", icon: "❤️", count: vitals.length },
    {
      id: "diagnoses",
      label: "Diagnoses",
      icon: "🩺",
      count: diagnoses.length,
    },
    { id: "notes", label: "Notes", icon: "📝", count: notes.length },
    {
      id: "orders",
      label: "Service Orders",
      icon: "📋",
      count: orders.length,
    },
  ]

  return (
    <div className="p-4 md:p-6 space-y-6 bg-slate-50 min-h-screen">
      {/* =====================================================
          HEADER
      ===================================================== */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">
            Doctor Consultation
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Record vitals, diagnoses, clinical notes and service orders
            against a patient visit.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="px-4 py-2 rounded-xl bg-white border border-slate-200 text-sm text-slate-600">
            🏥{" "}
            <strong className="text-slate-800">
              {selectedHospital ? selectedHospital.name : "No hospital"}
            </strong>
          </span>

          <button
            type="button"
            onClick={refresh}
            className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition cursor-pointer"
          >
            ⟳ Refresh
          </button>
        </div>
      </div>

      {/* =====================================================
          BANNERS
      ===================================================== */}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm">
          ✅ {successMessage}
        </div>
      )}

      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-start justify-between gap-3">
          <span>⚠️ {errorMessage}</span>
          <button
            type="button"
            onClick={() => setErrorMessage("")}
            className="text-red-500 hover:text-red-700 font-bold cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {visitsError && (
        <div className="p-4 rounded-xl bg-orange-50 border border-orange-200 text-orange-700 text-sm flex items-center justify-between gap-3">
          <span>⚠️ {visitsError}</span>
          <button
            type="button"
            onClick={refresh}
            className="px-3 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-700 text-white text-xs font-medium cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {!selectedHospital && (
        <div className="p-6 rounded-2xl bg-white border border-slate-200 text-center text-slate-500">
          Select a hospital from the navbar to start a consultation.
        </div>
      )}

      {/* =====================================================
          VISIT SELECTION
      ===================================================== */}
      {selectedHospital && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
          <div className="flex flex-col md:flex-row md:items-end gap-4">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wide">
                Select Visit
              </label>
              <select
                value={selectedVisitId}
                onChange={(event) =>
                  setSelectedVisitId(event.target.value)
                }
                disabled={loadingVisits}
                className="w-full border border-slate-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-slate-100"
              >
                <option value="">
                  {loadingVisits
                    ? "Loading visits…"
                    : visits.length
                      ? "-- Choose a visit --"
                      : "No visits available"}
                </option>
                {visits.map((visit) => (
                  <option
                    key={visit.apiId}
                    value={visit.apiId}
                  >
                    #{visit.apiId} · {visit.patientName} ·{" "}
                    {visit.visitType} · {visit.visitDay}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:w-64">
              <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wide">
                Visit Status
              </label>
              <select
                value={selectedVisit?.status || ""}
                onChange={(event) =>
                  handleVisitStatusChange(event.target.value)
                }
                disabled={!selectedVisit || savingVisit}
                className="w-full border border-slate-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-slate-100"
              >
                {selectedVisit ? (
                  VISIT_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))
                ) : (
                  <option value="">—</option>
                )}
              </select>
            </div>
          </div>

          {selectedVisit && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
              <Info label="Patient" value={selectedVisit.patientName} />
              <Info label="Doctor" value={selectedVisit.doctorName} />
              <Info label="Visit Type" value={selectedVisit.visitType} />
              <Info
                label="Visit Date"
                value={formatDateTime(selectedVisit.visitDate)}
              />
              {selectedVisit.chiefComplaint && (
                <div className="sm:col-span-2 lg:col-span-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Chief Complaint
                  </p>
                  <p className="text-sm text-slate-700 mt-1">
                    {selectedVisit.chiefComplaint}
                  </p>
                </div>
              )}
            </div>
          )}

          {!loadingVisits && visits.length === 0 && !visitsError && (
            <p className="text-sm text-slate-500">
              No visits found for this hospital. Visits are created when a
              patient is issued a queue token.
            </p>
          )}
        </div>
      )}

      {/* =====================================================
          CLINICAL TABS
      ===================================================== */}
      {selectedHospital && selectedVisitId && (
        <>
          {clinicalError && (
            <div className="p-4 rounded-xl bg-orange-50 border border-orange-200 text-orange-700 text-sm flex items-center justify-between gap-3">
              <span>⚠️ {clinicalError}</span>
              <button
                type="button"
                onClick={refresh}
                className="px-3 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-700 text-white text-xs font-medium cursor-pointer"
              >
                Retry
              </button>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition cursor-pointer border ${activeTab === tab.id
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-100"
                  }`}
              >
                {tab.icon} {tab.label}
                <span
                  className={`ml-2 text-xs px-2 py-0.5 rounded-full ${activeTab === tab.id
                      ? "bg-blue-500 text-white"
                      : "bg-slate-100 text-slate-500"
                    }`}
                >
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          {loadingClinical && (
            <p className="text-sm text-slate-500">
              Loading clinical records…
            </p>
          )}

          {/* ---------------------------------------------
              VITALS
          --------------------------------------------- */}
          {activeTab === "vitals" && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <form
                onSubmit={handleSaveVitals}
                className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4 xl:col-span-1"
              >
                <h2 className="font-semibold text-slate-800">
                  {editingVital ? "Edit Vitals" : "Record Vitals"}
                </h2>

                <div className="grid grid-cols-2 gap-3">
                  <Input
                    label="Weight (kg)"
                    value={vitalForm.weight}
                    onChange={(value) =>
                      setVitalForm({ ...vitalForm, weight: value })
                    }
                    type="number"
                    step="0.01"
                  />
                  <Input
                    label="Height (cm)"
                    value={vitalForm.height}
                    onChange={(value) =>
                      setVitalForm({ ...vitalForm, height: value })
                    }
                    type="number"
                    step="0.01"
                  />
                  <Input
                    label="Systolic BP"
                    value={vitalForm.systolicBp}
                    onChange={(value) =>
                      setVitalForm({ ...vitalForm, systolicBp: value })
                    }
                    type="number"
                  />
                  <Input
                    label="Diastolic BP"
                    value={vitalForm.diastolicBp}
                    onChange={(value) =>
                      setVitalForm({
                        ...vitalForm,
                        diastolicBp: value,
                      })
                    }
                    type="number"
                  />
                  <Input
                    label="Temperature (°C)"
                    value={vitalForm.temperature}
                    onChange={(value) =>
                      setVitalForm({
                        ...vitalForm,
                        temperature: value,
                      })
                    }
                    type="number"
                    step="0.01"
                  />
                  <Input
                    label="Pulse (bpm)"
                    value={vitalForm.heartRate}
                    onChange={(value) =>
                      setVitalForm({ ...vitalForm, heartRate: value })
                    }
                    type="number"
                  />
                  <Input
                    label="Resp. Rate"
                    value={vitalForm.respiratoryRate}
                    onChange={(value) =>
                      setVitalForm({
                        ...vitalForm,
                        respiratoryRate: value,
                      })
                    }
                    type="number"
                  />
                  <Input
                    label="SpO2 (%)"
                    value={vitalForm.spo2}
                    onChange={(value) =>
                      setVitalForm({ ...vitalForm, spo2: value })
                    }
                    type="number"
                  />
                  <Input
                    label="Blood Sugar"
                    value={vitalForm.bloodSugar}
                    onChange={(value) =>
                      setVitalForm({
                        ...vitalForm,
                        bloodSugar: value,
                      })
                    }
                    type="number"
                    step="0.01"
                  />
                </div>

                <TextArea
                  label="Comments"
                  value={vitalForm.comments}
                  onChange={(value) =>
                    setVitalForm({ ...vitalForm, comments: value })
                  }
                />

                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={savingVitals}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium transition cursor-pointer"
                  >
                    {savingVitals
                      ? "Saving…"
                      : editingVital
                        ? "Update Vitals"
                        : "Save Vitals"}
                  </button>

                  {editingVital && (
                    <button
                      type="button"
                      onClick={() => {
                        setVitalForm(emptyVitalForm)
                        setEditingVital(null)
                        setErrorMessage("")
                      }}
                      className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-sm font-medium transition cursor-pointer"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>

              <div className="xl:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100">
                  <h2 className="font-semibold text-slate-800">
                    Vital History
                  </h2>
                </div>

                {vitals.length === 0 ? (
                  <EmptyState text="No vitals recorded for this visit yet." />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                        <tr>
                          <th className="px-4 py-3 text-left">Recorded</th>
                          <th className="px-4 py-3 text-left">BP</th>
                          <th className="px-4 py-3 text-left">Pulse</th>
                          <th className="px-4 py-3 text-left">Temp</th>
                          <th className="px-4 py-3 text-left">SpO2</th>
                          <th className="px-4 py-3 text-left">Resp</th>
                          <th className="px-4 py-3 text-left">Weight</th>
                          <th className="px-4 py-3 text-right">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {vitals.map((vital) => (
                          <tr key={vital.apiId}>
                            <td className="px-4 py-3 text-slate-500">
                              {formatDateTime(vital.recordedAt)}
                            </td>
                            <td className="px-4 py-3 text-slate-700">
                              {vital.systolicBp || vital.diastolicBp
                                ? `${vital.systolicBp ?? "—"}/${vital.diastolicBp ?? "—"
                                }`
                                : "—"}
                            </td>
                            <td className="px-4 py-3">
                              {show(vital.heartRate)}
                            </td>
                            <td className="px-4 py-3">
                              {show(vital.temperature, "°C")}
                            </td>
                            <td className="px-4 py-3">
                              {show(vital.spo2, "%")}
                            </td>
                            <td className="px-4 py-3">
                              {show(vital.respiratoryRate)}
                            </td>
                            <td className="px-4 py-3">
                              {show(vital.weight, " kg")}
                            </td>
                            <td className="px-4 py-3 text-right whitespace-nowrap">
                              <RowActions
                                onEdit={() => handleEditVitals(vital)}
                                onDelete={() =>
                                  handleDeleteVitals(vital)
                                }
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ---------------------------------------------
              DIAGNOSES
          --------------------------------------------- */}
          {activeTab === "diagnoses" && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <form
                onSubmit={handleSaveDiagnosis}
                className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4 xl:col-span-1"
              >
                <h2 className="font-semibold text-slate-800">
                  {editingDiagnosis
                    ? "Edit Diagnosis"
                    : "Add Diagnosis"}
                </h2>

                <Input
                  label="Diagnosis Name *"
                  value={diagnosisForm.name}
                  onChange={(value) =>
                    setDiagnosisForm({
                      ...diagnosisForm,
                      name: value,
                    })
                  }
                />

                <Input
                  label="ICD-10 Code"
                  value={diagnosisForm.icd10Code}
                  onChange={(value) =>
                    setDiagnosisForm({
                      ...diagnosisForm,
                      icd10Code: value,
                    })
                  }
                  placeholder="e.g. A09.9"
                />

                <Select
                  label="Type"
                  value={diagnosisForm.diagnosisType}
                  onChange={(value) =>
                    setDiagnosisForm({
                      ...diagnosisForm,
                      diagnosisType: value,
                    })
                  }
                  options={DIAGNOSIS_TYPES}
                />

                <TextArea
                  label="Remarks"
                  value={diagnosisForm.remarks}
                  onChange={(value) =>
                    setDiagnosisForm({
                      ...diagnosisForm,
                      remarks: value,
                    })
                  }
                />

                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={savingDiagnosis}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium transition cursor-pointer"
                  >
                    {savingDiagnosis
                      ? "Saving…"
                      : editingDiagnosis
                        ? "Update Diagnosis"
                        : "Add Diagnosis"}
                  </button>

                  {editingDiagnosis && (
                    <button
                      type="button"
                      onClick={() => {
                        setDiagnosisForm(emptyDiagnosisForm)
                        setEditingDiagnosis(null)
                        setErrorMessage("")
                      }}
                      className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-sm font-medium transition cursor-pointer"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>

              <div className="xl:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100">
                  <h2 className="font-semibold text-slate-800">
                    Diagnoses
                  </h2>
                </div>

                {diagnoses.length === 0 ? (
                  <EmptyState text="No diagnoses recorded for this visit." />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                        <tr>
                          <th className="px-4 py-3 text-left">
                            Diagnosis
                          </th>
                          <th className="px-4 py-3 text-left">ICD-10</th>
                          <th className="px-4 py-3 text-left">Type</th>
                          <th className="px-4 py-3 text-left">Remarks</th>
                          <th className="px-4 py-3 text-right">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {diagnoses.map((diagnosis) => (
                          <tr key={diagnosis.apiId}>
                            <td className="px-4 py-3 font-medium text-slate-700">
                              {diagnosis.name}
                            </td>
                            <td className="px-4 py-3 text-slate-500">
                              {diagnosis.icd10Code || "—"}
                            </td>
                            <td className="px-4 py-3">
                              <span className="px-2 py-1 rounded-full text-xs bg-blue-50 text-blue-600">
                                {diagnosis.diagnosisType}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-slate-500 max-w-xs truncate">
                              {diagnosis.remarks || "—"}
                            </td>
                            <td className="px-4 py-3 text-right whitespace-nowrap">
                              <RowActions
                                onEdit={() =>
                                  handleEditDiagnosis(diagnosis)
                                }
                                onDelete={() =>
                                  handleDeleteDiagnosis(diagnosis)
                                }
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ---------------------------------------------
              CLINICAL NOTES
          --------------------------------------------- */}
          {activeTab === "notes" && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <form
                onSubmit={handleSaveNote}
                className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4 xl:col-span-1"
              >
                <h2 className="font-semibold text-slate-800">
                  {editingNote ? "Edit Note" : "Add Clinical Note"}
                </h2>

                <TextArea
                  label="Note *"
                  rows={8}
                  value={noteForm.note}
                  onChange={(value) =>
                    setNoteForm({ note: value })
                  }
                />

                <p className="text-xs text-slate-400">
                  Notes are attributed to{" "}
                  <strong>{selectedVisit?.doctorName || "Unassigned"}</strong>.
                </p>

                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={savingNote}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium transition cursor-pointer"
                  >
                    {savingNote
                      ? "Saving…"
                      : editingNote
                        ? "Update Note"
                        : "Add Note"}
                  </button>

                  {editingNote && (
                    <button
                      type="button"
                      onClick={() => {
                        setNoteForm(emptyNoteForm)
                        setEditingNote(null)
                        setErrorMessage("")
                      }}
                      className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-sm font-medium transition cursor-pointer"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>

              <div className="xl:col-span-2 space-y-4">
                {notes.length === 0 ? (
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <EmptyState text="No clinical notes for this visit yet." />
                  </div>
                ) : (
                  notes.map((note) => (
                    <div
                      key={note.apiId}
                      className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5"
                    >
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <span className="text-xs text-slate-400">
                          {formatDateTime(note.createdAt)}
                        </span>
                        <RowActions
                          onEdit={() => handleEditNote(note)}
                          onDelete={() => handleDeleteNote(note)}
                        />
                      </div>
                      <p className="text-sm text-slate-700 whitespace-pre-wrap">
                        {note.note}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* ---------------------------------------------
              SERVICE ORDERS
          --------------------------------------------- */}
          {activeTab === "orders" && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <form
                onSubmit={handleSaveOrder}
                className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4 xl:col-span-1"
              >
                <h2 className="font-semibold text-slate-800">
                  {editingOrder
                    ? "Edit Service Order"
                    : "Add Service Order"}
                </h2>

                <Input
                  label="Service Name *"
                  value={orderForm.serviceName}
                  onChange={(value) =>
                    setOrderForm({
                      ...orderForm,
                      serviceName: value,
                    })
                  }
                  placeholder="e.g. CBC Blood Test"
                />

                <Input
                  label="Quantity"
                  type="number"
                  value={orderForm.quantity}
                  onChange={(value) =>
                    setOrderForm({
                      ...orderForm,
                      quantity: value,
                    })
                  }
                />

                <Select
                  label="Status"
                  value={orderForm.status}
                  onChange={(value) =>
                    setOrderForm({ ...orderForm, status: value })
                  }
                  options={ORDER_STATUSES}
                />

                <TextArea
                  label="Remarks"
                  value={orderForm.remarks}
                  onChange={(value) =>
                    setOrderForm({ ...orderForm, remarks: value })
                  }
                />

                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={savingOrder}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium transition cursor-pointer"
                  >
                    {savingOrder
                      ? "Saving…"
                      : editingOrder
                        ? "Update Order"
                        : "Add Order"}
                  </button>

                  {editingOrder && (
                    <button
                      type="button"
                      onClick={() => {
                        setOrderForm(emptyOrderForm)
                        setEditingOrder(null)
                        setErrorMessage("")
                      }}
                      className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-sm font-medium transition cursor-pointer"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>

              <div className="xl:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100">
                  <h2 className="font-semibold text-slate-800">
                    Service Orders
                  </h2>
                </div>

                {orders.length === 0 ? (
                  <EmptyState text="No service orders for this visit." />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                        <tr>
                          <th className="px-4 py-3 text-left">Service</th>
                          <th className="px-4 py-3 text-left">Qty</th>
                          <th className="px-4 py-3 text-left">Status</th>
                          <th className="px-4 py-3 text-left">Remarks</th>
                          <th className="px-4 py-3 text-right">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {orders.map((order) => (
                          <tr key={order.apiId}>
                            <td className="px-4 py-3 font-medium text-slate-700">
                              {order.serviceName}
                            </td>
                            <td className="px-4 py-3">{order.quantity}</td>
                            <td className="px-4 py-3">
                              <span
                                className={`px-2 py-1 rounded-full text-xs ${orderStatusClass(
                                  order.status
                                )}`}
                              >
                                {order.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-slate-500 max-w-xs truncate">
                              {order.remarks || "—"}
                            </td>
                            <td className="px-4 py-3 text-right whitespace-nowrap">
                              <RowActions
                                onEdit={() => handleEditOrder(order)}
                                onDelete={() => handleDeleteOrder(order)}
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------
// Small presentational helpers (local to this page)
// ---------------------------------------------------------

function orderStatusClass(status) {
  if (status === "Completed") {
    return "bg-emerald-50 text-emerald-600"
  }

  if (status === "Cancelled") {
    return "bg-red-50 text-red-600"
  }

  return "bg-amber-50 text-amber-600"
}

function Info({ label, value }) {
  return (
    <div>
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
        {label}
      </p>
      <p className="text-sm text-slate-700 mt-1">{value || "—"}</p>
    </div>
  )
}

function Input({ label, value, onChange, type = "text", step, placeholder }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-500 mb-1">
        {label}
      </label>
      <input
        type={type}
        step={step}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="w-full border border-slate-300 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  )
}

function Select({ label, value, onChange, options }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-500 mb-1">
        {label}
      </label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full border border-slate-300 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 bg-white"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  )
}

function TextArea({ label, value, onChange, rows = 3 }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-500 mb-1">
        {label}
      </label>
      <textarea
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full border border-slate-300 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 resize-none"
      />
    </div>
  )
}

function RowActions({ onEdit, onDelete }) {
  return (
    <div className="inline-flex gap-2">
      <button
        type="button"
        onClick={onEdit}
        className="px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-600 text-xs font-medium cursor-pointer"
      >
        Edit
      </button>
      <button
        type="button"
        onClick={onDelete}
        className="px-3 py-1.5 rounded-lg bg-red-50 hover:bg-red-100 text-red-600 text-xs font-medium cursor-pointer"
      >
        Delete
      </button>
    </div>
  )
}

function EmptyState({ text }) {
  return (
    <p className="px-5 py-10 text-center text-sm text-slate-400">
      {text}
    </p>
  )
}

export default Consultation
