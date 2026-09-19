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
// DEMO SEED (offline fallback only)
// =====================================
//
// The original UI shipped with a single hardcoded demo record and no
// persistence. It is kept verbatim as the offline fallback so the
// Prescription / Pharmacy / Home / Reports screens never render blank when
// the Django backend is unreachable. This is NOT the source of truth once
// the API responds.

const DEMO_SEED = [
  {
    id: "RX-2026-001",
    hospitalId: 1,
    patientId: "P001",
    patientName: "Rahul Kumar",
    doctor: "Dr. Sharma",
    status: "Confirmed",
    medicines: [
      {
        name: "Paracetamol 500mg",
        dosage: "500 mg",
        frequency: "1-0-1",
        duration: "5 days",
        quantity: 10,
      },
      {
        name: "Amoxicillin 500mg",
        dosage: "500 mg",
        frequency: "0-0-1",
        duration: "5 days",
        quantity: 5,
      },
    ],
    createdAt: "01/09/2026",
  },
]


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

const loadCachedPrescriptions = () => {
  try {
    const cached = localStorage.getItem(OFFLINE_CACHE_KEY)

    if (cached) {
      const parsed = JSON.parse(cached)

      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed
      }
    }
  } catch {
    // Corrupt cache should never break the app.
  }

  return DEMO_SEED
}

const cachePrescriptions = (list) => {
  try {
    localStorage.setItem(OFFLINE_CACHE_KEY, JSON.stringify(list))
  } catch {
    // Storage may be unavailable (private mode); safe to ignore.
  }
}


export function PrescriptionProvider({ children }) {

  const [prescriptions, setPrescriptions] = useState(loadCachedPrescriptions)

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

  const addPrescription = (prescription) => {

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


    const newPrescription = {

      ...prescription,

      id: `RX-2026-${String(
        prescriptions.length + 1
      ).padStart(3, "0")}`,

      status: "Confirmed",

      createdAt:
        new Date().toLocaleDateString(
          "en-IN"
        ),

    }


    setPrescriptions((prev) => {

      const next = [...prev, newPrescription]

      cachePrescriptions(next)

      return next

    })


    // Best-effort persistence. Only attempted when we have real numeric
    // foreign keys (the demo AI card passes placeholder ids such as
    // "P001", which the backend correctly rejects). Failure is silent by
    // design so the existing demo flow is unaffected offline.
    const hasRealFks =
      Number.isInteger(prescription.patientId) &&
      Number.isInteger(prescription.hospitalId)

    if (hasRealFks) {

      api.prescriptions
        .create({
          hospital: prescription.hospitalId,
          patient: prescription.patientId,
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
        .catch(() => {
          // Offline / rejected demo payload — keep the local record.
        })

    }


    return newPrescription
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

  const dispensePrescription = (
    id,
    hospitalId = null
  ) => {

    let updatedPrescription = null


    setPrescriptions((prev) => {

      const next = prev.map(
        (prescription) => {

          const idMatch =
            String(prescription.id) === String(id)


          const hospitalMatch =
            hospitalId === null ||
            String(prescription.hospitalId) ===
            String(hospitalId)


          if (
            idMatch &&
            hospitalMatch
          ) {

            updatedPrescription = {

              ...prescription,

              status:
                "Dispensed",

              dispensedAt:
                new Date().toLocaleDateString(
                  "en-IN"
                ),

            }


            return updatedPrescription
          }


          return prescription
        }
      )

      cachePrescriptions(next)

      return next

    })


    if (updatedPrescription?.apiId) {

      api.prescriptions
        .patch(updatedPrescription.apiId, {
          status: "Dispensed",
          dispensed_at: new Date().toISOString(),
        })
        .catch(() => {
          // Offline — the local status stays Dispensed.
        })

    }


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
