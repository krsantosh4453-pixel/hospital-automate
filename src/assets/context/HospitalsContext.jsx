import { createContext, useCallback, useContext, useEffect, useState } from "react"
import api from "../../services/api.js"

const HospitalsContext = createContext(null)

// Hospitals come only from the API: staff get the hospitals they belong to,
// patients get the public directory. There is no demo fallback, because a
// made-up hospital id would point at a real, unrelated hospital.
const normalise = (hospital) => ({
  ...hospital,
  status: hospital.status || (hospital.is_active === false ? "Inactive" : "Active"),
})

export function HospitalsProvider({ children }) {
  const [hospitals, setHospitals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const refresh = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      let data
      try {
        data = await api.hospitals.list()
      } catch {
        // Not staff (or not signed in yet): fall back to the public directory.
        data = await api.hospitals.directory()
      }
      const results = Array.isArray(data) ? data : data?.results || []
      setHospitals(results.map(normalise))
    } catch (err) {
      setHospitals([])
      setError(err.message || "Could not load hospitals.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const onAuthChange = () => refresh()
    window.addEventListener("auth:logout", onAuthChange)
    window.addEventListener("auth:login", onAuthChange)
    return () => {
      window.removeEventListener("auth:logout", onAuthChange)
      window.removeEventListener("auth:login", onAuthChange)
    }
  }, [refresh])

  // Writes go to the API (platform admins create; hospital admins edit) and
  // the list is reloaded from the server, so the UI shows what was saved.
  const toPayload = (data) => ({
    name: data.name,
    code: data.code || null,
    type: data.type || "Private",
    address: data.address || "",
    city: data.city || "",
    state: data.state || "",
    phone: data.phone || "",
    email: data.email || "",
    is_active: (data.status || "Active") === "Active",
  })

  const addHospital = async (hospital) => {
    const created = await api.hospitals.create(toPayload(hospital))
    await refresh()
    return created
  }

  const updateHospital = async (id, data) => {
    const updated = await api.hospitals.update(id, toPayload(data))
    await refresh()
    return updated
  }

  const deleteHospital = async (id) => {
    await api.hospitals.remove(id)
    await refresh()
  }

  const toggleHospitalStatus = async (id) => {
    const hospital = hospitals.find((h) => String(h.id) === String(id))
    if (!hospital) return
    await api.hospitals.update(id, { is_active: hospital.status !== "Active" })
    await refresh()
  }

  const getHospitalById = (id) => hospitals.find((hospital) => String(hospital.id) === String(id))

  const getActiveHospitals = () => hospitals.filter((hospital) => hospital.status === "Active")

  return (
    <HospitalsContext.Provider
      value={{
        hospitals,
        authorizedHospitals: hospitals,
        loading,
        error,
        refresh,
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
