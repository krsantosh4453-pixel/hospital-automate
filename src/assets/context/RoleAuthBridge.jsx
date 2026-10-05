import { useEffect } from "react"
import { useAuth } from "./AuthContext.jsx"
import { useRole } from "./RoleContext.jsx"
import { getAuthenticatedStaffRole } from "../../utils/roleRouting.js"

export function RoleAuthBridge({ children }) {
  const { user, isStaff, patient, isLoggedIn } = useAuth()
  const { switchRole } = useRole()

  useEffect(() => {
    if (isStaff) {
      const backendRole = getAuthenticatedStaffRole(user)
      if (backendRole) {
        switchRole(backendRole)
      }
      return
    }

    if (isLoggedIn && patient) {
      switchRole("Patient")
    }
  }, [user, isStaff, patient, isLoggedIn, switchRole])

  return children
}
