import { createContext, useContext, useState } from "react"
import { withoutDemoRows } from "../../utils/demoData.js"

const PatientContext = createContext()

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

  const [patient, setPatient] = useState(() => {
    const savedPatient =
      localStorage.getItem("patientData")

    return savedPatient
      ? JSON.parse(savedPatient)
      : null
  })


  // =====================================================
  // PATIENT LIST
  // =====================================================

  const [patients, setPatients] = useState(() => {

    const savedPatients =
      localStorage.getItem("hospitalPatients")

    return savedPatients
      ? withoutDemoRows(JSON.parse(savedPatients), "patients")
      : []
  })


  // =====================================================
  // CURRENT APPOINTMENT
  // =====================================================

  const [appointment, setAppointment] = useState(() => {

    const savedAppointment =
      localStorage.getItem("patientAppointment")

    return savedAppointment
      ? JSON.parse(savedAppointment)
      : null
  })


  // =====================================================
  // CURRENT TOKEN
  // =====================================================

  const [token, setToken] = useState(() => {

    return localStorage.getItem("patientToken") || null

  })


  // =====================================================
  // SAVE PATIENT LIST
  // =====================================================

  const savePatients = (updatedPatients) => {

    setPatients(updatedPatients)

    localStorage.setItem(
      "hospitalPatients",
      JSON.stringify(updatedPatients)
    )
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

    localStorage.removeItem(
      "patientAppointment"
    )

    localStorage.removeItem(
      "patientToken"
    )
  }


  // =====================================================
  // SAVE CURRENT PATIENT
  // =====================================================

  const savePatient = (patientData) => {

    setPatient(patientData)

    localStorage.setItem(
      "patientData",
      JSON.stringify(patientData)
    )
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

    localStorage.setItem(
      "patientAppointment",
      JSON.stringify(appointmentData)
    )
  }


  // =====================================================
  // SAVE TOKEN
  // =====================================================

  const saveToken = (tokenNumber) => {

    setToken(tokenNumber)

    localStorage.setItem(
      "patientToken",
      tokenNumber
    )
  }


  // =====================================================
  // CLEAR PATIENT DATA
  // =====================================================

  const clearPatientData = () => {

    setPatient(null)
    setSelectedHospital(null)
    setAppointment(null)
    setToken(null)

    localStorage.removeItem("patientData")
    localStorage.removeItem("selectedHospital")
    localStorage.removeItem("patientAppointment")
    localStorage.removeItem("patientToken")
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


// =====================================================
// HOOK
// =====================================================

export function usePatient() {

  return useContext(PatientContext)

}