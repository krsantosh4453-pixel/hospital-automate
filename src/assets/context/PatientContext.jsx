import { createContext, useContext, useEffect, useState } from "react"

const PatientContext = createContext()

export function PatientProvider({ children }) {

  const [selectedHospital, setSelectedHospital] = useState(() => {
    const savedHospital =
      localStorage.getItem("selectedHospital")

    return savedHospital
      ? JSON.parse(savedHospital)
      : null
  })

  const [patient, setPatient] = useState(() => {
    const savedPatient =
      localStorage.getItem("patientData")

    return savedPatient
      ? JSON.parse(savedPatient)
      : null
  })

  const [appointment, setAppointment] = useState(() => {
    const savedAppointment =
      localStorage.getItem("patientAppointment")

    return savedAppointment
      ? JSON.parse(savedAppointment)
      : null
  })

  const [token, setToken] = useState(() => {
    return localStorage.getItem("patientToken") || null
  })


  // Hospital select/change
  const selectHospital = (hospital) => {

    setSelectedHospital(hospital)

    localStorage.setItem(
      "selectedHospital",
      JSON.stringify(hospital)
    )

    // Hospital change hone par
    // hospital-specific patient data reset
    setAppointment(null)
    setToken(null)

    localStorage.removeItem(
      "patientAppointment"
    )

    localStorage.removeItem(
      "patientToken"
    )
  }


  // Patient save
  const savePatient = (patientData) => {

    setPatient(patientData)

    localStorage.setItem(
      "patientData",
      JSON.stringify(patientData)
    )
  }


  // Appointment save
  const saveAppointment = (appointmentData) => {

    setAppointment(appointmentData)

    localStorage.setItem(
      "patientAppointment",
      JSON.stringify(appointmentData)
    )
  }


  // Token save
  const saveToken = (tokenNumber) => {

    setToken(tokenNumber)

    localStorage.setItem(
      "patientToken",
      tokenNumber
    )
  }


  // Clear patient data
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


  return (
    <PatientContext.Provider
      value={{
        patient,
        selectedHospital,
        appointment,
        token,

        savePatient,
        selectHospital,
        saveAppointment,
        saveToken,
        clearPatientData,
      }}
    >
      {children}
    </PatientContext.Provider>
  )
}


export function usePatient() {
  return useContext(PatientContext)
}