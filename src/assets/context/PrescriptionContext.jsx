import {
  createContext,
  useCallback,
  useContext,
  useState,
} from "react"

import api from "../../services/api.js"

const PrescriptionContext = createContext()

const OFFLINE_CACHE_KEY = "hospitalPrescriptions"


// =====================================
// API -> UI MAPPING
// =====================================
//
// Backend now owns the integer id. We expose a display id (`RX-0001`) used
// by the search boxes in Pharmacy/Reports while retaining `apiId` for every
// write operation, so we never identify a prescription by display name.

const formatDate = (value) => {
  if (!value) return ""

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return ""

  return date.toLocaleDateString("en-IN")
}

const mapPrescriptionFromApi = (record) => ({
  id: `RX-${String(record.id).padStart(4, "0")}`,
  apiId: record.id,
  hospitalId: record.hospital,
  patientId: record.patient,
  patientName: record.patient_name || "",
  doctor: record.doctor_name || record.doctor || "",
  doctorId: record.doctor,
  visitId: record.visit,
  status: record.status,
  dispensedAt: record.dispensed_at || null,
  createdAt: formatDate(record.created_at),
  medicines: (record.items || []).map((item) => ({
    id: item.id,
    name: item.name,
    dosage: item.dosage,
    frequency: item.frequency,
    duration: item.duration,
    quantity: item.quantity,
    instructions: item.instructions,
  })),
})

// Prescriptions are not cached in the browser: they contain patient data and
// hospital PCs are shared. The list always comes from the API.
const clearLegacyCache = () => {
  try {
    localStorage.removeItem(OFFLINE_CACHE_KEY)
  } catch {
    // Storage may be unavailable (private mode); safe to ignore.
  }
}

const cachePrescriptions = () => {}


export function PrescriptionProvider({ children }) {

  const [prescriptions, setPrescriptions] = useState(() => {
    clearLegacyCache()
    return []
  })

  const [loading, setLoading] = useState(false)

  const [error, setError] = useState(null)

  // True when the last API attempt failed and we degraded to cached/seed
  // data. The UI uses this to show a non-blocking offline notice.
  const [usingFallback, setUsingFallback] = useState(false)


  // =====================================
  // LOAD FROM API
  // =====================================
  //
  // Reads prescriptions from Django. On success the API data becomes the
  // source of truth. On failure we keep the cached/seed list and flag the
  // offline fallback so the screen is never left empty.

  const loadPrescriptions = useCallback(
    async ({ hospitalId, patientId, visitId } = {}) => {

      setLoading(true)
      setError(null)

      try {

        const response = await api.prescriptions.list({
          hospitalId,
          patientId,
          visitId,
        })

        const records = Array.isArray(response)
          ? response
          : response?.results || []

        const mapped = records.map(mapPrescriptionFromApi)

        setPrescriptions(mapped)
        cachePrescriptions(mapped)
        setUsingFallback(false)

        return mapped

      } catch (err) {

        setError(
          err?.message ||
          "Unable to load prescriptions from the server."
        )
        setUsingFallback(true)

        return prescriptions

      } finally {

        setLoading(false)

      }
    },
    [prescriptions]
  )


  // =====================================
  // RETRY / CLEAR
  // =====================================

  const retryPrescriptions = (params) => loadPrescriptions(params)

  const clearError = () => setError(null)


  // =====================================
  // CREATE (API-BACKED, ASYNC)
  // =====================================
  //
  // Used by the new Prescription page. Expects a backend-shaped payload:
  // { hospital, patient, doctor, visit, status, items: [...] }.
  // Throws on failure so the page can surface validation errors.

  const createPrescription = async (payload) => {

    const created = await api.prescriptions.create(payload)

    const mapped = mapPrescriptionFromApi(created)

    setPrescriptions((prev) => {
      const next = [mapped, ...prev]
      cachePrescriptions(next)
      return next
    })

    setUsingFallback(false)

    return mapped
  }


  // =====================================
  // UPDATE (API-BACKED, ASYNC)
  // =====================================

  const updatePrescription = async (apiId, payload) => {

    const updated = await api.prescriptions.update(apiId, payload)

    const mapped = mapPrescriptionFromApi(updated)

    setPrescriptions((prev) => {
      const next = prev.map((item) =>
        String(item.apiId) === String(apiId) ? mapped : item
      )
      cachePrescriptions(next)
      return next
    })

    return mapped
  }


  // =====================================
  // DELETE (API-BACKED, ASYNC)
  // =====================================

  const deletePrescription = async (apiId) => {

    await api.prescriptions.delete(apiId)

    setPrescriptions((prev) => {
      const next = prev.filter(
        (item) => String(item.apiId) !== String(apiId)
      )
      cachePrescriptions(next)
      return next
    })

    return true
  }


  // =====================================
  // DOCTOR CREATES PRESCRIPTION (LEGACY/OPTIMISTIC)
  // =====================================
  //
  // Kept SYNCHRONOUS and returning the new object because the existing
  // Doctor screen (doctors.jsx) calls it inline and reads `.id`
  // immediately. Behaviour is preserved exactly. When backend ids are
  // present we also best-effort persist in the background without ever
  // blocking or throwing into the caller.

  // Creates the prescription on the server and returns the saved record.
  // Throws when the server rejects it; nothing is kept locally on failure.
  const addPrescription = async (prescription) => {

    if (!prescription.hospitalId) {
      throw new Error(
        "Hospital is required for prescription."
      )
    }


    if (!prescription.patientId) {
      throw new Error(
        "Patient is required for prescription."
      )
    }


    if (
      !prescription.medicines ||
      prescription.medicines.length === 0
    ) {
      throw new Error(
        "At least one medicine is required."
      )
    }

    return createPrescription({
      hospital: Number(prescription.hospitalId),
      patient: Number(prescription.patientId),
      doctor: prescription.doctorId || null,
      visit: prescription.visitId || null,
      status: "Confirmed",
      items: prescription.medicines.map((medicine) => ({
        name: medicine.name,
        dosage: medicine.dosage || "",
        frequency: medicine.frequency || "",
        duration: medicine.duration || "",
        quantity: medicine.quantity || 1,
        instructions: medicine.instructions || "",
      })),
    })
  }


  // =====================================
  // FIND PRESCRIPTION
  // =====================================

  const findPrescription = (
    id,
    hospitalId = null
  ) => {

    if (!id) {
      return null
    }


    return prescriptions.find(
      (prescription) => {

        const idMatch =
          String(prescription.id).toLowerCase() ===
          String(id).trim().toLowerCase()


        const hospitalMatch =
          hospitalId === null ||
          String(prescription.hospitalId) ===
          String(hospitalId)


        return (
          idMatch &&
          hospitalMatch
        )
      }
    )
  }


  // =====================================
  // PHARMACY DISPENSES PRESCRIPTION
  // =====================================
  //
  // Preserves the synchronous contract (pharmacy.jsx reads the returned
  // object). When the record came from the API we also best-effort PATCH
  // the backend status. NOTE: stock deduction is intentionally NOT done
  // here — that belongs to a future Pharmacy task.

  // Marks the prescription Dispensed on the server, then in the list.
  // Throws if it is unknown here or the server refuses. Stock is deducted
  // by the pharmacy sale, not here.
  const dispensePrescription = async (
    id,
    hospitalId = null
  ) => {

    const record = prescriptions.find(
      (prescription) =>
        String(prescription.id) === String(id) &&
        (hospitalId === null || String(prescription.hospitalId) === String(hospitalId))
    )

    if (!record?.apiId) {
      throw new Error("Prescription not found on the server.")
    }

    await api.prescriptions.patch(record.apiId, { status: "Dispensed" })

    const updatedPrescription = {
      ...record,
      status: "Dispensed",
      dispensedAt: new Date().toLocaleDateString("en-IN"),
    }

    setPrescriptions((prev) =>
      prev.map((prescription) =>
        prescription.apiId === record.apiId ? updatedPrescription : prescription
      )
    )

    return updatedPrescription
  }


  // =====================================
  // GET HOSPITAL PRESCRIPTIONS
  // =====================================

  const getHospitalPrescriptions = (
    hospitalId
  ) => {

    if (!hospitalId) {
      return []
    }


    return prescriptions.filter(
      (prescription) =>
        String(prescription.hospitalId) ===
        String(hospitalId)
    )
  }


  // =====================================
  // CONTEXT
  // =====================================

  return (

    <PrescriptionContext.Provider

      value={{

        prescriptions,

        addPrescription,

        findPrescription,

        dispensePrescription,

        getHospitalPrescriptions,

        // API-backed helpers (additive — existing consumers unaffected)
        loadPrescriptions,

        retryPrescriptions,

        createPrescription,

        updatePrescription,

        deletePrescription,

        clearError,

        loading,

        error,

        usingFallback,

      }}

    >

      {children}

    </PrescriptionContext.Provider>

  )
}


// =====================================
// CUSTOM HOOK
// =====================================

export function usePrescription() {

  const context =
    useContext(
      PrescriptionContext
    )


  if (!context) {

    throw new Error(
      "usePrescription must be used inside PrescriptionProvider"
    )

  }


  return context
}
