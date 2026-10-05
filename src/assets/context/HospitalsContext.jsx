import { createContext, useContext, useState, useEffect } from "react"
import api from "../../services/api.js"

const HospitalsContext = createContext(null)

const initialHospitals = [
  {
    id: 1,
    name: "City Hospital Begusarai",
    code: "CHB001",
    address: "Begusarai, Bihar",
    phone: "9876543210",
    email: "cityhospital@gmail.com",
    type: "Private",
    status: "Active",
    doctors: 12,
    nurses: 20,
    departments: 6,
  },
  {
    id: 2,
    name: "Sadar Hospital Begusarai",
    code: "SHB001",
    address: "Begusarai, Bihar",
    phone: "9876543211",
    email: "sadarhospital@gmail.com",
    type: "Government",
    status: "Active",
    doctors: 18,
    nurses: 30,
    departments: 8,
  },
  {
    id: 3,
    name: "Medicare Hospital Begusarai",
    code: "MHB001",
    address: "Begusarai, Bihar",
    phone: "9876543212",
    email: "medicare@gmail.com",
    type: "Private",
    status: "Active",
    doctors: 10,
    nurses: 15,
    departments: 5,
  },
]

export function HospitalsProvider({ children }) {
  const [hospitals, setHospitals] = useState(() => {
    const saved = localStorage.getItem(
      "hospitalList"
    )

    return saved
      ? JSON.parse(saved)
      : initialHospitals
  })

  const saveHospitals = (updatedHospitals) => {
    setHospitals(updatedHospitals)

    localStorage.setItem(
      "hospitalList",
      JSON.stringify(updatedHospitals)
    )
  }

  const addHospital = (hospital) => {
    const newHospital = {
      ...hospital,
      id: hospital.id || Date.now(),
      status: hospital.status || "Active",
      doctors: hospital.doctors || 0,
      nurses: hospital.nurses || 0,
      departments: hospital.departments || 0,
    }

    saveHospitals([
      newHospital,
      ...hospitals,
    ])

    return newHospital
  }

  const updateHospital = (id, data) => {
    const updated = hospitals.map(
      (hospital) =>
        hospital.id === id
          ? {
            ...hospital,
            ...data,
          }
          : hospital
    )

    saveHospitals(updated)
  }

  const deleteHospital = (id) => {
    const updated = hospitals.filter(
      (hospital) => hospital.id !== id
    )

    saveHospitals(updated)
  }

  const toggleHospitalStatus = (id) => {
    const updated = hospitals.map(
      (hospital) =>
        hospital.id === id
          ? {
            ...hospital,
            status:
              hospital.status === "Active"
                ? "Inactive"
                : "Active",
          }
          : hospital
    )

    saveHospitals(updated)
  }

  const getHospitalById = (id) => {
    return hospitals.find(
      (hospital) =>
        String(hospital.id) === String(id)
    )
  }

  const getActiveHospitals = () => {
    return hospitals.filter(
      (hospital) =>
        hospital.status === "Active" || hospital.is_active !== false
    )
  }

  useEffect(() => {
    let cancelled = false
    api.hospitals
      .list()
      .then((data) => {
        const results = Array.isArray(data) ? data : data?.results || []
        if (!cancelled && results.length > 0) {
          saveHospitals(
            results.map((hospital) => ({
              ...hospital,
              status: hospital.status || (hospital.is_active === false ? "Inactive" : "Active"),
            }))
          )
        }
      })
      .catch(() => {
        // Keep local/demo hospitals when the API is unavailable or unauthenticated.
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <HospitalsContext.Provider
      value={{
        hospitals,
        authorizedHospitals: hospitals,
        addHospital,
        updateHospital,
        deleteHospital,
        toggleHospitalStatus,
        getHospitalById,
        getActiveHospitals,
      }}
    >
      {children}
    </HospitalsContext.Provider>
  )
}

export function useHospitals() {
  const context = useContext(
    HospitalsContext
  )

  if (!context) {
    throw new Error(
      "useHospitals must be used inside HospitalsProvider"
    )
  }

  return context
}