import { createContext, useContext, useState } from "react"

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    return localStorage.getItem("patientLoggedIn") === "true"
  })

  const [patient, setPatient] = useState(() => {
    const savedPatient = localStorage.getItem("patient")

    return savedPatient
      ? JSON.parse(savedPatient)
      : null
  })

  const login = (patientData) => {
    setIsLoggedIn(true)
    setPatient(patientData)

    localStorage.setItem(
      "patientLoggedIn",
      "true"
    )

    localStorage.setItem(
      "patient",
      JSON.stringify(patientData)
    )
  }

  const logout = () => {
    setIsLoggedIn(false)
    setPatient(null)

    localStorage.removeItem(
      "patientLoggedIn"
    )

    localStorage.removeItem(
      "patient"
    )
  }

  return (
    <AuthContext.Provider
      value={{
        isLoggedIn,
        patient,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}