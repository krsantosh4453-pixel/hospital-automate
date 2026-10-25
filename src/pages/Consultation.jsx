import { useEffect, useMemo, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import { CalendarClock, ClipboardList, HeartPulse, Hospital, NotebookPen, Pencil, RefreshCw, Stethoscope, Trash2, UserRound } from "lucide-react"
import {
  Alert,
  Avatar,
  Button,
  Card,
  CardHeader,
  ConfirmDialog,
  EmptyState,
  Field,
  Input,
  PageHeader,
  SearchInput,
  Select,
  SkeletonRows,
  StatusBadge,
  TableWrap,
  Tabs,
  Textarea,
} from "../components/ui"

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
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [visitSearch, setVisitSearch] = useState("")

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

  const handleDeleteVitals = (vital) =>
    setPendingDelete({ title: "Delete these vital signs?", run: () => handleDeleteVitalsNow(vital) })

  const handleDeleteVitalsNow = async (vital) => {
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

  const handleDeleteDiagnosis = (diagnosis) =>
    setPendingDelete({ title: "Delete this diagnosis?", run: () => handleDeleteDiagnosisNow(diagnosis) })

  const handleDeleteDiagnosisNow = async (diagnosis) => {
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

  const handleDeleteNote = (note) =>
    setPendingDelete({ title: "Delete this clinical note?", run: () => handleDeleteNoteNow(note) })

  const handleDeleteNoteNow = async (note) => {
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

  const handleDeleteOrder = (order) =>
    setPendingDelete({ title: "Delete this service order?", run: () => handleDeleteOrderNow(order) })

  const handleDeleteOrderNow = async (order) => {
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

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    await pendingDelete.run()
    setDeleting(false)
    setPendingDelete(null)
  }

  const tabs = [
    { id: "vitals", label: "Vitals", icon: HeartPulse, count: vitals.length },
    { id: "diagnoses", label: "Diagnoses", icon: Stethoscope, count: diagnoses.length },
    { id: "notes", label: "Notes", icon: NotebookPen, count: notes.length },
    { id: "orders", label: "Service orders", icon: ClipboardList, count: orders.length },
  ]

  const visibleVisits = visits.filter((visit) =>
    `${visit.patientName} ${visit.apiId} ${visit.doctorName}`.toLowerCase().includes(visitSearch.toLowerCase()),
  )

  const setVital = (field) => (event) => setVitalForm({ ...vitalForm, [field]: event.target.value })

  return (
    <div className="space-y-5">
      <PageHeader
        title="Consultation"
        description="Record vitals, diagnoses, clinical notes and service orders against a patient visit."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Consultation" }]}
        actions={
          <Button variant="secondary" icon={RefreshCw} onClick={refresh} disabled={!selectedHospital}>
            Refresh
          </Button>
        }
      />

      {successMessage && <Alert tone="success" onDismiss={() => setSuccessMessage("")}>{successMessage}</Alert>}
      {errorMessage && <Alert tone="danger" onDismiss={() => setErrorMessage("")}>{errorMessage}</Alert>}
      {visitsError && (
        <Alert tone="warning" action={<Button size="sm" variant="secondary" onClick={refresh}>Retry</Button>}>
          {visitsError}
        </Alert>
      )}

      {!selectedHospital ? (
        <Card>
          <EmptyState icon={Hospital} title="Select a hospital" description="Choose a hospital in the header to start a consultation." />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[20rem_minmax(0,1fr)]">
          {/* Visit list */}
          <Card className="flex max-h-[calc(100vh-10rem)] flex-col overflow-hidden xl:sticky xl:top-20">
            <CardHeader title="Visits" description={loadingVisits ? "Loading…" : `${visits.length} at this hospital`} />
            <div className="border-b border-line p-3">
              <SearchInput value={visitSearch} onChange={setVisitSearch} placeholder="Patient or visit #" label="Search visits" />
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto scrollbar-thin">
              {loadingVisits && visits.length === 0 ? (
                <SkeletonRows rows={4} />
              ) : visibleVisits.length === 0 ? (
                <EmptyState
                  compact
                  icon={CalendarClock}
                  title={visits.length ? "No visit matches" : "No visits yet"}
                  description={visits.length ? undefined : "A visit is created when a patient is issued a queue token."}
                />
              ) : (
                <ul className="divide-y divide-ink-100" role="listbox" aria-label="Visits">
                  {visibleVisits.map((visit) => {
                    const active = String(visit.apiId) === String(selectedVisitId)
                    return (
                      <li key={visit.apiId} role="option" aria-selected={active}>
                        <button
                          type="button"
                          onClick={() => setSelectedVisitId(String(visit.apiId))}
                          className={`flex w-full items-start gap-3 px-4 py-3 text-left ${active ? "bg-brand-50" : "hover:bg-ink-50"}`}
                        >
                          <Avatar name={visit.patientName} size="sm" tone={active ? "brand" : "neutral"} />
                          <span className="min-w-0 flex-1">
                            <span className={`block truncate text-sm font-medium ${active ? "text-brand-900" : "text-ink-900"}`}>{visit.patientName}</span>
                            <span className="block truncate text-xs text-ink-500 tabular-nums">
                              #{visit.apiId} · {visit.visitType} · {visit.visitDay}
                            </span>
                          </span>
                          <StatusBadge status={visit.status} />
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </Card>

          {/* Selected visit */}
          {!selectedVisit ? (
            <Card>
              <EmptyState icon={UserRound} title="Select a visit" description="Choose a patient visit from the list to open the consultation." />
            </Card>
          ) : (
            <div className="min-w-0 space-y-5">
              <Card className="sticky top-16 z-10 shadow-sm">
                <div className="flex flex-wrap items-center gap-x-6 gap-y-3 px-5 py-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <Avatar name={selectedVisit.patientName} size="lg" />
                    <div className="min-w-0">
                      <p className="truncate text-base font-semibold text-ink-900">{selectedVisit.patientName}</p>
                      <p className="text-[13px] text-ink-500 tabular-nums">
                        Visit #{selectedVisit.apiId} · {selectedVisit.visitType} · {formatDateTime(selectedVisit.visitDate)}
                      </p>
                    </div>
                  </div>
                  <div className="text-[13px]">
                    <p className="text-ink-500">Doctor</p>
                    <p className="font-medium text-ink-900">{selectedVisit.doctorName}</p>
                  </div>
                  <div className="ml-auto w-full sm:w-52">
                    <label htmlFor="visit-status" className="sr-only">Visit status</label>
                    <Select
                      id="visit-status"
                      value={selectedVisit.status}
                      onChange={(event) => handleVisitStatusChange(event.target.value)}
                      disabled={savingVisit}
                    >
                      {VISIT_STATUSES.map((status) => (
                        <option key={status} value={status}>{status}</option>
                      ))}
                    </Select>
                  </div>
                </div>
                {selectedVisit.chiefComplaint && (
                  <p className="border-t border-line px-5 py-3 text-sm text-ink-700">
                    <span className="font-medium text-ink-500">Chief complaint: </span>
                    {selectedVisit.chiefComplaint}
                  </p>
                )}
              </Card>

              {clinicalError && (
                <Alert tone="warning" action={<Button size="sm" variant="secondary" onClick={refresh}>Retry</Button>}>
                  {clinicalError}
                </Alert>
              )}

              <Tabs tabs={tabs} value={activeTab} onChange={setActiveTab} label="Clinical records" />

              {loadingClinical && <SkeletonRows rows={3} />}

              {!loadingClinical && activeTab === "vitals" && (
                <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[22rem_minmax(0,1fr)]">
                  <Card as="form" onSubmit={handleSaveVitals}>
                    <CardHeader title={editingVital ? "Edit vital signs" : "Record vital signs"} />
                    <div className="space-y-4 px-5 py-4">
                      <div className="grid grid-cols-2 gap-3">
                        <Field label="Systolic BP (mmHg)"><Input type="number" inputMode="numeric" value={vitalForm.systolicBp} onChange={setVital("systolicBp")} /></Field>
                        <Field label="Diastolic BP (mmHg)"><Input type="number" inputMode="numeric" value={vitalForm.diastolicBp} onChange={setVital("diastolicBp")} /></Field>
                        <Field label="Pulse (bpm)"><Input type="number" inputMode="numeric" value={vitalForm.heartRate} onChange={setVital("heartRate")} /></Field>
                        <Field label="SpO₂ (%)"><Input type="number" inputMode="numeric" value={vitalForm.spo2} onChange={setVital("spo2")} /></Field>
                        <Field label="Temperature (°C)"><Input type="number" step="0.01" inputMode="decimal" value={vitalForm.temperature} onChange={setVital("temperature")} /></Field>
                        <Field label="Resp. rate (/min)"><Input type="number" inputMode="numeric" value={vitalForm.respiratoryRate} onChange={setVital("respiratoryRate")} /></Field>
                        <Field label="Weight (kg)"><Input type="number" step="0.01" inputMode="decimal" value={vitalForm.weight} onChange={setVital("weight")} /></Field>
                        <Field label="Height (cm)"><Input type="number" step="0.01" inputMode="decimal" value={vitalForm.height} onChange={setVital("height")} /></Field>
                        <Field label="Blood sugar (mg/dL)" className="col-span-2"><Input type="number" step="0.01" inputMode="decimal" value={vitalForm.bloodSugar} onChange={setVital("bloodSugar")} /></Field>
                      </div>
                      <Field label="Comments"><Textarea value={vitalForm.comments} onChange={setVital("comments")} /></Field>
                      <FormButtons
                        saving={savingVitals}
                        editing={Boolean(editingVital)}
                        createLabel="Save vitals"
                        onCancel={() => {
                          setVitalForm(emptyVitalForm)
                          setEditingVital(null)
                          setErrorMessage("")
                        }}
                      />
                    </div>
                  </Card>

                  <Card className="overflow-hidden">
                    <CardHeader title="Vital history" />
                    {vitals.length === 0 ? (
                      <EmptyState compact icon={HeartPulse} title="No vitals recorded for this visit yet" />
                    ) : (
                      <TableWrap>
                        <table className="hms-table">
                          <thead>
                            <tr>
                              <th scope="col">Recorded</th>
                              <th scope="col">BP</th>
                              <th scope="col" className="num">Pulse</th>
                              <th scope="col" className="num">Temp</th>
                              <th scope="col" className="num">SpO₂</th>
                              <th scope="col" className="num">Resp</th>
                              <th scope="col" className="num">Weight</th>
                              <th scope="col"><span className="sr-only">Actions</span></th>
                            </tr>
                          </thead>
                          <tbody>
                            {vitals.map((vital) => (
                              <tr key={vital.apiId}>
                                <td className="whitespace-nowrap text-ink-600 tabular-nums">{formatDateTime(vital.recordedAt)}</td>
                                <td className="whitespace-nowrap font-medium tabular-nums">
                                  {vital.systolicBp || vital.diastolicBp ? `${vital.systolicBp ?? "—"}/${vital.diastolicBp ?? "—"}` : "—"}
                                </td>
                                <td className="num">{show(vital.heartRate)}</td>
                                <td className="num">{show(vital.temperature, "°C")}</td>
                                <td className="num">{show(vital.spo2, "%")}</td>
                                <td className="num">{show(vital.respiratoryRate)}</td>
                                <td className="num">{show(vital.weight, " kg")}</td>
                                <td><RowActions label="vital signs" onEdit={() => handleEditVitals(vital)} onDelete={() => handleDeleteVitals(vital)} /></td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </TableWrap>
                    )}
                  </Card>
                </div>
              )}

              {!loadingClinical && activeTab === "diagnoses" && (
                <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[22rem_minmax(0,1fr)]">
                  <Card as="form" onSubmit={handleSaveDiagnosis}>
                    <CardHeader title={editingDiagnosis ? "Edit diagnosis" : "Add diagnosis"} />
                    <div className="space-y-4 px-5 py-4">
                      <Field label="Diagnosis" required>
                        <Input value={diagnosisForm.name} onChange={(e) => setDiagnosisForm({ ...diagnosisForm, name: e.target.value })} />
                      </Field>
                      <div className="grid grid-cols-2 gap-3">
                        <Field label="ICD-10 code" hint="e.g. A09.9">
                          <Input value={diagnosisForm.icd10Code} onChange={(e) => setDiagnosisForm({ ...diagnosisForm, icd10Code: e.target.value })} />
                        </Field>
                        <Field label="Type">
                          <Select value={diagnosisForm.diagnosisType} onChange={(e) => setDiagnosisForm({ ...diagnosisForm, diagnosisType: e.target.value })}>
                            {DIAGNOSIS_TYPES.map((o) => <option key={o} value={o}>{o}</option>)}
                          </Select>
                        </Field>
                      </div>
                      <Field label="Remarks">
                        <Textarea value={diagnosisForm.remarks} onChange={(e) => setDiagnosisForm({ ...diagnosisForm, remarks: e.target.value })} />
                      </Field>
                      <FormButtons
                        saving={savingDiagnosis}
                        editing={Boolean(editingDiagnosis)}
                        createLabel="Add diagnosis"
                        onCancel={() => {
                          setDiagnosisForm(emptyDiagnosisForm)
                          setEditingDiagnosis(null)
                          setErrorMessage("")
                        }}
                      />
                    </div>
                  </Card>

                  <Card className="overflow-hidden">
                    <CardHeader title="Diagnoses" />
                    {diagnoses.length === 0 ? (
                      <EmptyState compact icon={Stethoscope} title="No diagnoses recorded for this visit" />
                    ) : (
                      <TableWrap>
                        <table className="hms-table">
                          <thead>
                            <tr>
                              <th scope="col">Diagnosis</th>
                              <th scope="col">ICD-10</th>
                              <th scope="col">Type</th>
                              <th scope="col">Remarks</th>
                              <th scope="col"><span className="sr-only">Actions</span></th>
                            </tr>
                          </thead>
                          <tbody>
                            {diagnoses.map((diagnosis) => (
                              <tr key={diagnosis.apiId}>
                                <td className="font-medium text-ink-900">{diagnosis.name}</td>
                                <td className="font-mono text-[13px] text-ink-600">{diagnosis.icd10Code || "—"}</td>
                                <td><span className="inline-flex rounded-md bg-ink-100 px-2 py-0.5 text-xs font-medium text-ink-700">{diagnosis.diagnosisType}</span></td>
                                <td className="max-w-xs truncate text-ink-600">{diagnosis.remarks || "—"}</td>
                                <td><RowActions label="diagnosis" onEdit={() => handleEditDiagnosis(diagnosis)} onDelete={() => handleDeleteDiagnosis(diagnosis)} /></td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </TableWrap>
                    )}
                  </Card>
                </div>
              )}

              {!loadingClinical && activeTab === "notes" && (
                <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[22rem_minmax(0,1fr)]">
                  <Card as="form" onSubmit={handleSaveNote}>
                    <CardHeader title={editingNote ? "Edit note" : "Add clinical note"} />
                    <div className="space-y-4 px-5 py-4">
                      <Field label="Note" required hint={`Attributed to ${selectedVisit?.doctorName || "Unassigned"}.`}>
                        <Textarea rows={8} value={noteForm.note} onChange={(e) => setNoteForm({ note: e.target.value })} />
                      </Field>
                      <FormButtons
                        saving={savingNote}
                        editing={Boolean(editingNote)}
                        createLabel="Add note"
                        onCancel={() => {
                          setNoteForm(emptyNoteForm)
                          setEditingNote(null)
                          setErrorMessage("")
                        }}
                      />
                    </div>
                  </Card>

                  <Card>
                    <CardHeader title="Clinical notes" description="Newest first" />
                    {notes.length === 0 ? (
                      <EmptyState compact icon={NotebookPen} title="No clinical notes for this visit yet" />
                    ) : (
                      <ol className="divide-y divide-ink-100">
                        {notes.map((note) => (
                          <li key={note.apiId} className="px-5 py-4">
                            <div className="mb-1.5 flex items-center justify-between gap-3">
                              <time className="text-xs font-medium text-ink-500 tabular-nums">{formatDateTime(note.createdAt)}</time>
                              <RowActions label="note" onEdit={() => handleEditNote(note)} onDelete={() => handleDeleteNote(note)} />
                            </div>
                            <p className="whitespace-pre-wrap text-sm leading-6 text-ink-800">{note.note}</p>
                          </li>
                        ))}
                      </ol>
                    )}
                  </Card>
                </div>
              )}

              {!loadingClinical && activeTab === "orders" && (
                <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[22rem_minmax(0,1fr)]">
                  <Card as="form" onSubmit={handleSaveOrder}>
                    <CardHeader title={editingOrder ? "Edit service order" : "Add service order"} />
                    <div className="space-y-4 px-5 py-4">
                      <Field label="Service" required>
                        <Input value={orderForm.serviceName} onChange={(e) => setOrderForm({ ...orderForm, serviceName: e.target.value })} placeholder="e.g. CBC blood test" />
                      </Field>
                      <div className="grid grid-cols-2 gap-3">
                        <Field label="Quantity">
                          <Input type="number" min="1" inputMode="numeric" value={orderForm.quantity} onChange={(e) => setOrderForm({ ...orderForm, quantity: e.target.value })} />
                        </Field>
                        <Field label="Status">
                          <Select value={orderForm.status} onChange={(e) => setOrderForm({ ...orderForm, status: e.target.value })}>
                            {ORDER_STATUSES.map((o) => <option key={o} value={o}>{o}</option>)}
                          </Select>
                        </Field>
                      </div>
                      <Field label="Remarks">
                        <Textarea value={orderForm.remarks} onChange={(e) => setOrderForm({ ...orderForm, remarks: e.target.value })} />
                      </Field>
                      <FormButtons
                        saving={savingOrder}
                        editing={Boolean(editingOrder)}
                        createLabel="Add order"
                        onCancel={() => {
                          setOrderForm(emptyOrderForm)
                          setEditingOrder(null)
                          setErrorMessage("")
                        }}
                      />
                    </div>
                  </Card>

                  <Card className="overflow-hidden">
                    <CardHeader title="Service orders" />
                    {orders.length === 0 ? (
                      <EmptyState compact icon={ClipboardList} title="No service orders for this visit" />
                    ) : (
                      <TableWrap>
                        <table className="hms-table">
                          <thead>
                            <tr>
                              <th scope="col">Service</th>
                              <th scope="col" className="num">Qty</th>
                              <th scope="col">Status</th>
                              <th scope="col">Remarks</th>
                              <th scope="col"><span className="sr-only">Actions</span></th>
                            </tr>
                          </thead>
                          <tbody>
                            {orders.map((order) => (
                              <tr key={order.apiId}>
                                <td className="font-medium text-ink-900">{order.serviceName}</td>
                                <td className="num">{order.quantity}</td>
                                <td><StatusBadge status={order.status} /></td>
                                <td className="max-w-xs truncate text-ink-600">{order.remarks || "—"}</td>
                                <td><RowActions label="order" onEdit={() => handleEditOrder(order)} onDelete={() => handleDeleteOrder(order)} /></td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </TableWrap>
                    )}
                  </Card>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onCancel={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        loading={deleting}
        destructive
        title={pendingDelete?.title || "Delete record?"}
        confirmLabel="Delete"
        message="This removes the record from the patient's visit. It cannot be undone."
      />
    </div>
  )
}

// ---------------------------------------------------------
// Small presentational helpers (local to this page)
// ---------------------------------------------------------

function FormButtons({ saving, editing, createLabel, onCancel }) {
  return (
    <div className="flex gap-2 pt-1">
      <Button type="submit" loading={saving} className="flex-1 justify-center">
        {editing ? "Save changes" : createLabel}
      </Button>
      {editing && (
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      )}
    </div>
  )
}

function RowActions({ label, onEdit, onDelete }) {
  return (
    <div className="flex items-center justify-end gap-0.5">
      <Button variant="ghost" size="icon-sm" icon={Pencil} onClick={onEdit} aria-label={`Edit ${label}`} title="Edit" />
      <Button variant="danger-ghost" size="icon-sm" icon={Trash2} onClick={onDelete} aria-label={`Delete ${label}`} title="Delete" />
    </div>
  )
}

export default Consultation
