import { createContext, useContext, useState, useEffect, useCallback } from "react"
import api from "../../services/api.js"

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isStaff, setIsStaff] = useState(false)
  const [isPatient, setIsPatient] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [patient, setPatient] = useState(null)

  const clearSessionState = useCallback(() => {
    setUser(null)
    setPatient(null)
    setIsLoggedIn(false)
    setIsStaff(false)
    setIsPatient(false)
    localStorage.removeItem("patientLoggedIn")
    localStorage.removeItem("patient")
  }, [])

  const applyPatientSession = useCallback((session) => {
    if (!session?.access || !session?.patient) {
      throw new Error("Patient login did not return a valid session.")
    }
    api.auth.applySession(session)
    setUser(null)
    setPatient(session.patient)
    setIsStaff(false)
    setIsPatient(true)
    setIsLoggedIn(true)
    localStorage.setItem("patient", JSON.stringify(session.patient))
    return session
  }, [])

  const applyStaffSession = useCallback((userData) => {
    setUser(userData)
    setPatient(null)
    setIsStaff(true)
    setIsPatient(false)
    setIsLoggedIn(true)
    return userData
  }, [])

  const loadUserFromToken = useCallback(async () => {
    const { accessToken, refreshToken } = api.auth.getTokens()
    if (!accessToken && !refreshToken) {
      clearSessionState()
      setIsLoading(false)
      return
    }

    try {
      try {
        const userData = await api.auth.getMe()
        applyStaffSession(userData)
        return
      } catch (staffError) {
        const patientData = await api.auth.patientMe()
        if (!patientData?.patient) {
          throw staffError
        }
        setUser(null)
        setPatient(patientData.patient)
        setIsStaff(false)
        setIsPatient(true)
        setIsLoggedIn(true)
        localStorage.setItem("patient", JSON.stringify(patientData.patient))
      }
    } catch {
      api.auth.clearTokens()
      clearSessionState()
    } finally {
      setIsLoading(false)
    }
  }, [applyStaffSession, clearSessionState])

  useEffect(() => {
    loadUserFromToken()

    const handleLogout = () => {
      clearSessionState()
    }

    window.addEventListener("auth:logout", handleLogout)
    return () => window.removeEventListener("auth:logout", handleLogout)
  }, [loadUserFromToken, clearSessionState])

  const staffLogin = async (username, password) => {
    await api.auth.staffLogin(username, password)
    const userData = await api.auth.getMe()
    return applyStaffSession(userData)
  }

  const patientLogin = (session) => applyPatientSession(session)

  const adoptExternalSession = async (session) => {
    api.auth.applySession(session)
    if (session?.account_type === "staff") {
      const userData = await api.auth.getMe()
      return applyStaffSession(userData)
    }
    return applyPatientSession(session)
  }

  const logout = () => {
    api.auth.logout()
    clearSessionState()
  }

  const setPatientData = (patientData) => {
    setPatient(patientData)
  }

  const clearPatientData = () => {
    setPatient(null)
  }

  const isAuthenticated = isStaff || isPatient

  return (
    <AuthContext.Provider
      value={{
        user,
        patient,
        isLoggedIn,
        isAuthenticated,
        isStaff,
        isPatient,
        isLoading,
        login: patientLogin,
        staffLogin,
        patientLogin,
        adoptExternalSession,
        logout,
        setPatientData,
        clearPatientData,
        refreshUser: loadUserFromToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
