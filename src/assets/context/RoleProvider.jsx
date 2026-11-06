import { useState, useEffect, useCallback } from "react"
import { useAuth } from "./AuthContext.jsx"
import { usePatient } from "./PatientContext.jsx"
import api from "../../services/api.js"
import { getAuthenticatedStaffRole } from "../../utils/roleRouting.js"
import { DEFAULT_ROLES, RoleContext } from "./RoleContext.jsx"

export function RoleProvider({ children }) {
  const { isStaff, isPatient, user } = useAuth()
  // Roles are built in. The Permissions page used to save edits to localStorage
  // that no permission check ever read; drop any such leftovers.
  const roles = DEFAULT_ROLES
  useEffect(() => {
    try {
      localStorage.removeItem("hms_role_permissions")
    } catch {
      // Storage unavailable (private mode): nothing to clean up.
    }
  }, [])

  const authenticatedRoles = (() => {
    if (isPatient && !isStaff) return ["Patient"]
    if (!isStaff) return []
    const raw = user?.user?.roles || user?.roles || []
    const mapped = raw.map((role) => {
      if (role === "Reception") return "Receptionist"
      return role
    })
    const primary = getAuthenticatedStaffRole(user)
    if (primary && !mapped.includes(primary)) mapped.unshift(primary)
    return mapped.filter(Boolean)
  })()

  const [chosenRole, setChosenRole] = useState(null)
  const activeRoleName = authenticatedRoles.includes(chosenRole)
    ? chosenRole
    : authenticatedRoles[0] || null

  // Current active role object comes from the authenticated backend role.
  const activeRole = DEFAULT_ROLES.find((role) => role.name === activeRoleName) || null

  // Switch only among roles the backend actually assigned.
  const switchRole = useCallback((roleName) => {
    const requested = roleName === "Reception" ? "Receptionist" : roleName
    if (!authenticatedRoles.includes(requested)) return
    setChosenRole(requested)
  }, [authenticatedRoles])

  // The hospital's narrowing of built-in roles (Permissions page). The server
  // enforces it; here it only hides what would be refused.
  const { selectedHospital } = usePatient() || {}
  const hospitalId = selectedHospital?.id
  const [restrictions, setRestrictions] = useState([])
  const [restrictionsToken, setRestrictionsToken] = useState(0)
  const reloadRestrictions = useCallback(() => setRestrictionsToken((n) => n + 1), [])
  useEffect(() => {
    if (!isStaff || !hospitalId) {
      setRestrictions([])
      return undefined
    }
    let cancelled = false
    api.roleRestrictions.list(hospitalId)
      .then((data) => !cancelled && setRestrictions(Array.isArray(data) ? data : data?.results || []))
      .catch(() => !cancelled && setRestrictions([]))
    return () => {
      cancelled = true
    }
  }, [isStaff, hospitalId, restrictionsToken])

  // Permission checks
  const hasPermission = (moduleName, action = "View") => {
    if (!activeRoleName) return false
    if (activeRoleName === "Admin") return true
    const rule = restrictions.find((r) => r.role === activeRoleName && r.module === moduleName)
    if (rule?.access === "none") return false
    if (rule?.access === "view" && action !== "View") return false
    const rolePerms = activeRole?.permissions || {}
    const modulePerms = rolePerms[moduleName] || []
    return modulePerms.includes(action)
  }

  const canView = (moduleName) => hasPermission(moduleName, "View")
  const canAdd = (moduleName) => hasPermission(moduleName, "Add")
  const canEdit = (moduleName) => hasPermission(moduleName, "Edit")
  const canDelete = (moduleName) => hasPermission(moduleName, "Delete")

  return (
    <RoleContext.Provider
      value={{
        roles,
        activeRole,
        activeRoleName,
        switchRole,
        hasPermission,
        canView,
        canAdd,
        canEdit,
        canDelete,
        restrictions,
        reloadRestrictions,
      }}
    >
      {children}
    </RoleContext.Provider>
  )
}
