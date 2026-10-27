import { createContext, useContext, useState, useEffect, useCallback } from "react"
import api from "../../services/api.js"

const AuthContext = createContext()
const DEV_AUTH_BYPASS_KEY = "hms_dev_auth_bypass"

function isDevelopmentAuthBypassEnabled() {
  if (!import.meta.env.DEV) {
    return false
  }

  // Off unless explicitly enabled: when on, anyone opening the dev server is
  // signed in as a fake Admin and sees every add/create action.
  const configured = import.meta.env.VITE_DEV_AUTH_BYPASS
  if (configured === undefined || configured === null || configured === "") {
    return false
  }

  return String(configured).toLowerCase() === "true"
}

function buildDevAuthUser() {
  const user = {
    id: "dev-admin",
    username: "dev-admin",
    email: "dev-admin@hospital.local",
    first_name: "Development",
    last_name: "Admin",
    full_name: "Development Admin",
    staff_role: "Admin",
    roles: ["Admin"],
  }

  return {
    ...user,
    user: {
      ...user,
      roles: [...user.roles],
      user: undefined,
    },
  }
}

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

  const clearDevelopmentAccess = useCallback(() => {
    localStorage.removeItem(DEV_AUTH_BYPASS_KEY)
  }, [])

  const applyDevelopmentAccess = useCallback(() => {
    const devUser = buildDevAuthUser()
    setUser(devUser)
    setPatient(null)
    setIsStaff(true)
    setIsPatient(false)
    setIsLoggedIn(true)
    localStorage.setItem(DEV_AUTH_BYPASS_KEY, "true")
    localStorage.setItem("user", JSON.stringify(devUser))
    localStorage.setItem("roles", JSON.stringify(["Admin"]))
    return devUser
  }, [])

  const applyPatientSession = useCallback((session) => {
    // Browser sessions get their tokens as httpOnly cookies ("session": "cookie").
    if (!(session?.access || session?.session === "cookie") || !session?.patient) {
      throw new Error("Patient login did not return a valid session.")
    }
    api.auth.applySession(session)
    setUser(null)
    setPatient(session.patient)
    setIsStaff(false)
    setIsPatient(true)
    setIsLoggedIn(true)
    localStorage.setItem("patient", JSON.stringify(session.patient))
    window.dispatchEvent(new Event("auth:login"))
    return session
  }, [])

  const applyStaffSession = useCallback((userData) => {
    setUser(userData)
    setPatient(null)
    setIsStaff(true)
    setIsPatient(false)
    setIsLoggedIn(true)
    window.dispatchEvent(new Event("auth:login"))
    return userData
  }, [])

  const loadUserFromToken = useCallback(async () => {
    const { accessToken, refreshToken } = api.auth.getTokens()
    const devBypassEnabled = isDevelopmentAuthBypassEnabled()
    const devBypassActive = localStorage.getItem(DEV_AUTH_BYPASS_KEY) === "true"

    if (devBypassEnabled && (!accessToken && !refreshToken)) {
      applyDevelopmentAccess()
      setIsLoading(false)
      return
    }

    if (!accessToken && !refreshToken) {
      if (devBypassEnabled && devBypassActive) {
        applyDevelopmentAccess()
      } else {
        clearDevelopmentAccess()
        clearSessionState()
      }
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
  }, [applyDevelopmentAccess, applyStaffSession, clearSessionState])

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
    clearDevelopmentAccess()
    return applyStaffSession(userData)
  }

  const staffLoginStartOtp = async (username, password) => {
    const data = await api.auth.staffLoginStartOtp(username, password)
    return data
  }

  const staffOtpVerify = async (challenge, otp) => {
    const data = await api.auth.staffOtpVerify(challenge, otp)
    clearDevelopmentAccess()
    return applyStaffSession(data.user)
  }

  const staffOtpResend = async (challenge) => {
    const data = await api.auth.staffOtpResend(challenge)
    return data
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
    clearDevelopmentAccess()
    api.auth.logout()
    clearSessionState()
    // Lets other providers drop patient data they hold in memory.
    window.dispatchEvent(new Event("auth:logout"))
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
        staffLoginStartOtp,
        staffOtpVerify,
        staffOtpResend,
        patientLogin,
        adoptExternalSession,
        logout,
        setPatientData,
        clearPatientData,
        refreshUser: loadUserFromToken,
        applyDevelopmentAccess,
        devBypassAvailable: isDevelopmentAuthBypassEnabled(),
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
