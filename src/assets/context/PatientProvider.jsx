import { useEffect, useState } from "react"
import { clearCachedPatientData } from "../../services/api.js"
import { PatientContext } from "./PatientContext.jsx"

// Hospital PCs are shared: patient rows, appointments and tokens stay in
// memory and never reach localStorage. Only the selected hospital is kept.
const LEGACY_PATIENT_KEYS = ["patientToken", "patient"]

function forgetStoredPatientRows() {
  clearCachedPatientData()
  try {
    for (const key of LEGACY_PATIENT_KEYS) localStorage.removeItem(key)
  } catch {
    // Storage may be unavailable (private mode); nothing to clear.
  }
}


export function PatientProvider({ children }) {

  // =====================================================
  // SELECTED HOSPITAL
  // =====================================================

  const [selectedHospital, setSelectedHospital] = useState(() => {
    const savedHospital =
      localStorage.getItem("selectedHospital")

    return savedHospital
      ? JSON.parse(savedHospital)
      : null
  })


  // =====================================================
  // CURRENT LOGGED-IN / SELECTED PATIENT
  // =====================================================

  const [patient, setPatient] = useState(null)


  // =====================================================
  // PATIENT LIST
  // =====================================================

  const [patients, setPatients] = useState([])


  // =====================================================
  // CURRENT APPOINTMENT
  // =====================================================

  const [appointment, setAppointment] = useState(null)


  // =====================================================
  // CURRENT TOKEN
  // =====================================================

  const [token, setToken] = useState(null)


  // Signing out (or an expired session) drops patient rows held in memory.
  // Copies an older version stored are removed once, on start.
  useEffect(() => {
    forgetStoredPatientRows()
  }, [])

  useEffect(() => {
    const forgetPatients = () => {
      setPatients([])
      setPatient(null)
      setAppointment(null)
    }
    window.addEventListener("auth:logout", forgetPatients)
    return () => window.removeEventListener("auth:logout", forgetPatients)
  }, [])


  // =====================================================
  // SAVE PATIENT LIST
  // =====================================================

  const savePatients = (updatedPatients) => {

    setPatients(updatedPatients)
  }


  // =====================================================
  // HOSPITAL SELECT
  // =====================================================

  const selectHospital = (hospital) => {

    setSelectedHospital(hospital)

    localStorage.setItem(
      "selectedHospital",
      JSON.stringify(hospital)
    )

    // Hospital change hone par
    // current appointment/token reset
    setAppointment(null)
    setToken(null)
  }


  // =====================================================
  // SAVE CURRENT PATIENT
  // =====================================================

  const savePatient = (patientData) => {

    setPatient(patientData)
  }


  // =====================================================
  // ADD PATIENT
  // =====================================================

  const addPatient = (patientData) => {

    const newPatient = {

      ...patientData,

      id:
        patientData.id ||
        `PAT-${Date.now()}`,

      hospitalId:
        patientData.hospitalId ||
        selectedHospital?.id,

      createdAt:
        patientData.createdAt ||
        new Date().toLocaleString("en-IN"),

    }

    savePatients([
      newPatient,
      ...patients,
    ])

    return newPatient
  }


  // =====================================================
  // UPDATE PATIENT
  // =====================================================

  const updatePatient = (id, data) => {

    const updatedPatients =
      patients.map((existingPatient) =>
        String(existingPatient.id) === String(id)
          ? {
            ...existingPatient,
            ...data,
          }
          : existingPatient
      )

    savePatients(updatedPatients)
  }


  // =====================================================
  // DELETE PATIENT
  // =====================================================

  const deletePatient = (id) => {

    const updatedPatients =
      patients.filter(
        (existingPatient) =>
          String(existingPatient.id) !== String(id)
      )

    savePatients(updatedPatients)
  }


  // =====================================================
  // GET PATIENTS OF SELECTED HOSPITAL
  // =====================================================

  const getHospitalPatients = (hospitalId) => {

    if (!hospitalId) {
      return []
    }

    return patients.filter(
      (existingPatient) =>
        String(existingPatient.hospitalId) ===
        String(hospitalId)
    )
  }


  // =====================================================
  // FIND PATIENT
  // =====================================================

  const findPatient = (id) => {

    return patients.find(
      (existingPatient) =>
        String(existingPatient.id) === String(id)
    )
  }


  // =====================================================
  // SAVE APPOINTMENT
  // =====================================================

  const saveAppointment = (appointmentData) => {

    setAppointment(appointmentData)
  }


  // =====================================================
  // SAVE TOKEN
  // =====================================================

  const saveToken = (tokenNumber) => {

    setToken(tokenNumber)
  }


  // =====================================================
  // CLEAR PATIENT DATA
  // =====================================================

  const clearPatientData = () => {

    setPatient(null)
    setSelectedHospital(null)
    setAppointment(null)
    setToken(null)

    localStorage.removeItem("selectedHospital")
    forgetStoredPatientRows()
  }


  // =====================================================
  // PROVIDER
  // =====================================================

  return (

    <PatientContext.Provider
      value={{

        // Existing
        patient,
        selectedHospital,
        appointment,
        token,

        savePatient,
        selectHospital,
        saveAppointment,
        saveToken,
        clearPatientData,

        // New
        patients,
        addPatient,
        updatePatient,
        deletePatient,
        getHospitalPatients,
        findPatient,

      }}
    >

      {children}

    </PatientContext.Provider>

  )
}
