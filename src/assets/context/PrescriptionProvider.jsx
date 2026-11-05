import { useCallback, useState } from "react"

import api from "../../services/api.js"
import { PrescriptionContext } from "./PrescriptionContext.jsx"
import { mapPrescriptionFromApi } from "../../utils/prescriptionRecord.js"


const OFFLINE_CACHE_KEY = "hospitalPrescriptions"


// API -> UI mapping lives in utils/prescriptionRecord.js (shared with the
// pharmacy queue): display id RX-0001, `apiId` for every write.

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

  const deletePrescription = async (apiId, reason) => {

    await api.prescriptions.delete(apiId, reason)

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
  // FETCH ONE BY RX NUMBER (API-BACKED, ASYNC)
  // =====================================
  //
  // The pharmacy looks prescriptions up on the server, so one written after
  // its page loaded is found. Returns null when the number is malformed,
  // unknown, or belongs to another hospital; other errors are thrown.

  const fetchPrescription = async (rxId, hospitalId = null) => {

    const match = /^RX-0*(\d+)$/i.exec(String(rxId).trim())
    if (!match) {
      return null
    }

    let record
    try {
      record = await api.prescriptions.get(match[1])
    } catch (err) {
      if (err?.status === 404) {
        return null
      }
      throw err
    }

    const mapped = mapPrescriptionFromApi(record)
    if (hospitalId !== null && String(mapped.hospitalId) !== String(hospitalId)) {
      return null
    }

    setPrescriptions((prev) => [
      mapped,
      ...prev.filter((item) => String(item.apiId) !== String(mapped.apiId)),
    ])

    return mapped
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


  // Dispensing is not done here: the Pharmacy page's dispense endpoint
  // issues stock and is the only thing that marks a prescription Dispensed.


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

        fetchPrescription,

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
