import { createContext, useContext, useState } from "react"
import { withoutDemoRows } from "../../utils/demoData.js"

const AppointmentContext = createContext(null)

export function AppointmentProvider({ children }) {
  const [appointments, setAppointments] = useState(() => {
    const saved = localStorage.getItem("hospitalAppointments")

    return saved
      ? withoutDemoRows(JSON.parse(saved), "appointments")
      : []
  })


  // =========================
  // Save Appointments
  // =========================

  const saveAppointments = (updated) => {
    setAppointments(updated)

    localStorage.setItem(
      "hospitalAppointments",
      JSON.stringify(updated)
    )
  }


  // =========================
  // Generate Token Number
  // =========================

  const generateTokenNumber = (hospitalId) => {

    const hospitalAppointments =
      appointments.filter(
        (appointment) =>
          String(appointment.hospitalId) ===
          String(hospitalId)
      )

    const tokenNumbers =
      hospitalAppointments
        .map((appointment) => {
          if (!appointment.tokenNumber) {
            return 0
          }

          return Number(
            String(appointment.tokenNumber)
              .replace("T-", "")
          ) || 0
        })

    const highestToken =
      tokenNumbers.length > 0
        ? Math.max(...tokenNumbers)
        : 0

    const nextToken =
      highestToken + 1

    return `T-${String(
      nextToken
    ).padStart(3, "0")}`
  }


  // =========================
  // Add Appointment
  // =========================

  const addAppointment = (appointment) => {

    const tokenNumber =
      appointment.tokenNumber ||
      generateTokenNumber(
        appointment.hospitalId
      )

    const newAppointment = {

      ...appointment,

      id:
        appointment.id ||
        `A${Date.now()}`,

      tokenNumber,

      status:
        appointment.status ||
        "Confirmed",

      createdAt:
        appointment.createdAt ||
        new Date().toLocaleString("en-IN"),
    }

    saveAppointments([
      newAppointment,
      ...appointments,
    ])

    return newAppointment
  }


  // =========================
  // Update Appointment
  // =========================

  const updateAppointment = (
    id,
    data
  ) => {

    const updated =
      appointments.map(
        (appointment) =>
          appointment.id === id
            ? {
              ...appointment,
              ...data,
            }
            : appointment
      )

    saveAppointments(updated)
  }


  // =========================
  // Delete Appointment
  // =========================

  const deleteAppointment = (id) => {

    const updated =
      appointments.filter(
        (appointment) =>
          appointment.id !== id
      )

    saveAppointments(updated)
  }


  // =========================
  // Cancel Appointment
  // =========================

  const cancelAppointment = (id) => {

    const updated =
      appointments.map(
        (appointment) =>
          appointment.id === id
            ? {
              ...appointment,
              status: "Cancelled",
            }
            : appointment
      )

    saveAppointments(updated)
  }


  // =========================
  // Get Hospital Appointments
  // =========================

  const getHospitalAppointments = (
    hospitalId
  ) => {

    if (!hospitalId) {
      return []
    }

    return appointments.filter(
      (appointment) =>
        String(appointment.hospitalId) ===
        String(hospitalId)
    )
  }


  // =========================
  // Get Patient Appointments
  // =========================

  const getPatientAppointments = (
    patientId
  ) => {

    if (!patientId) {
      return []
    }

    return appointments.filter(
      (appointment) =>
        String(appointment.patientId) ===
        String(patientId)
    )
  }


  return (
    <AppointmentContext.Provider
      value={{

        appointments,

        addAppointment,

        updateAppointment,

        deleteAppointment,

        cancelAppointment,

        getHospitalAppointments,

        getPatientAppointments,

      }}
    >
      {children}
    </AppointmentContext.Provider>
  )
}


export function useAppointment() {

  const context =
    useContext(AppointmentContext)

  if (!context) {

    throw new Error(
      "useAppointment must be used inside AppointmentProvider"
    )

  }

  return context
}