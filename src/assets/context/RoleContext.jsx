import { createContext, useContext, useState, useEffect, useCallback } from "react"
import { useAuth } from "./AuthContext.jsx"
import { getAuthenticatedStaffRole } from "../../utils/roleRouting.js"

const RoleContext = createContext(null)

// Default modules and permission mappings
export const ALL_MODULES = [
  "Dashboard",
  "Patients",
  "Appointments",
  "Queue",
  "Doctors",
  "Nurses",
  "Compounders",
  "Pharmacy",
  "Laboratory",
  "Billing",
  "Inventory",
  "Prescriptions",
  "Reports",
  "Emergency",
  "BloodBank",
  "IPD",
  "AIScribe",
  "Users",
  "Roles",
  "Hospitals",
  "Departments",
  "Permissions",
]

export const DEFAULT_ROLES = [
  {
    id: 1,
    name: "Admin",
    description: "Full system access to all modules and administration",
    permissions: {
      Dashboard: ["View", "Add", "Edit", "Delete"],
      Patients: ["View", "Add", "Edit", "Delete"],
      Appointments: ["View", "Add", "Edit", "Delete"],
      Queue: ["View", "Add", "Edit", "Delete"],
      Doctors: ["View", "Add", "Edit", "Delete"],
      Nurses: ["View", "Add", "Edit", "Delete"],
      Compounders: ["View", "Add", "Edit", "Delete"],
      Pharmacy: ["View", "Add", "Edit", "Delete"],
      Laboratory: ["View", "Add", "Edit", "Delete"],
      Billing: ["View", "Add", "Edit", "Delete"],
      Inventory: ["View", "Add", "Edit", "Delete"],
      Prescriptions: ["View", "Add", "Edit", "Delete"],
      Reports: ["View", "Add", "Edit", "Delete"],
      Emergency: ["View", "Add", "Edit", "Delete"],
      BloodBank: ["View", "Add", "Edit", "Delete"],
      IPD: ["View", "Add", "Edit", "Delete"],
      AIScribe: ["View", "Add", "Edit", "Delete"],
      Users: ["View", "Add", "Edit", "Delete"],
      Roles: ["View", "Add", "Edit", "Delete"],
      Hospitals: ["View", "Add", "Edit", "Delete"],
      Departments: ["View", "Add", "Edit", "Delete"],
      Permissions: ["View", "Add", "Edit", "Delete"],
    },
  },
  {
    id: 2,
    name: "Doctor",
    description: "Access to patients, consultations, appointments, lab results and prescriptions",
    permissions: {
      Dashboard: ["View"],
      Patients: ["View", "Edit"],
      Appointments: ["View", "Edit"],
      Queue: ["View"],
      Doctors: ["View"],
      Prescriptions: ["View", "Add", "Edit"],
      Laboratory: ["View"],
      Reports: ["View"],
    },
  },
  {
    id: 3,
    name: "Nurse",
    description: "Manage patient vitals, queue triage, and view appointments",
    permissions: {
      Dashboard: ["View"],
      Patients: ["View", "Edit"],
      Appointments: ["View"],
      Queue: ["View", "Edit"],
      Nurses: ["View", "Edit"],
      Prescriptions: ["View"],
      IPD: ["View", "Edit"],
      Reports: ["View"],
    },
  },
  {
    id: 4,
    name: "Compounder",
    description: "Dispense medicines, manage stock and pharmacy orders",
    permissions: {
      Dashboard: ["View"],
      Patients: ["View"],
      Compounders: ["View", "Edit"],
      Prescriptions: ["View", "Edit"],
      Pharmacy: ["View", "Add", "Edit"],
      Inventory: ["View", "Edit"],
      Queue: ["View"],
    },
  },
  {
    id: 5,
    name: "Receptionist",
    description: "Patient registration, token generation, appointments, and billing",
    permissions: {
      Dashboard: ["View"],
      Patients: ["View", "Add", "Edit"],
      Appointments: ["View", "Add", "Edit"],
      Queue: ["View", "Edit"],
      Billing: ["View", "Add"],
      Doctors: ["View"],
      Reports: ["View"],
      IPD: ["View", "Add"],
    },
  },
  {
    id: 6,
    name: "Patient",
    description: "View personal appointments, queue status, lab tests and invoices",
    permissions: {
      Dashboard: ["View"],
      Appointments: ["View", "Add"],
      Queue: ["View"],
      Prescriptions: ["View"],
      Laboratory: ["View"],
      Billing: ["View"],
    },
  },
]

export function backendRoleCanView(roleName, moduleName) {
  if (!moduleName) return Boolean(roleName)
  const role = DEFAULT_ROLES.find((item) => item.name === roleName)
  if (!role) return false
  if (role.name === "Admin") return true
  return (role.permissions?.[moduleName] || []).includes("View")
}

export function RoleProvider({ children }) {
  const { isStaff, isPatient, user } = useAuth()
  // Load roles & permissions from localStorage or defaults
  const [roles, setRoles] = useState(() => {
    const extraAdminPerms = {
      Emergency: ["View", "Add", "Edit", "Delete"],
      BloodBank: ["View", "Add", "Edit", "Delete"],
      IPD: ["View", "Add", "Edit", "Delete"],
      AIScribe: ["View", "Add", "Edit", "Delete"],
    }
    const saved = localStorage.getItem("hms_role_permissions")
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        return parsed.map((role) => {
          const name = role.name === "Reception" ? "Receptionist" : role.name
          if (name !== "Admin") {
            return { ...role, name }
          }
          return {
            ...role,
            name,
            permissions: { ...extraAdminPerms, ...(role.permissions || {}) },
          }
        })
      } catch (e) {
        console.error("Failed to parse saved role permissions:", e)
      }
    }
    return DEFAULT_ROLES
  })

  const authenticatedRoles = (() => {
    if (isPatient && !isStaff) return ["Patient"]
    if (!isStaff) return []
    const raw = user?.user?.roles || user?.roles || []
    const mapped = raw.map((role) => {
      if (role === "Reception") return "Receptionist"
      if (role === "Pharmacist") return "Compounder"
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

  // Save roles whenever changed
  useEffect(() => {
    localStorage.setItem("hms_role_permissions", JSON.stringify(roles))
  }, [roles])

  // Current active role object comes from the authenticated backend role.
  const activeRole = DEFAULT_ROLES.find((role) => role.name === activeRoleName) || null

  // Switch only among roles the backend actually assigned.
  const switchRole = useCallback((roleName) => {
    const requested = roleName === "Reception" ? "Receptionist" : roleName === "Pharmacist" ? "Compounder" : roleName
    if (!authenticatedRoles.includes(requested)) return
    setChosenRole(requested)
  }, [authenticatedRoles])

  // Update permissions for a specific role
  const updateRolePermissions = (roleId, newPermissions) => {
    setRoles((prevRoles) =>
      prevRoles.map((role) =>
        role.id === roleId ? { ...role, permissions: newPermissions } : role
      )
    )
  }

  // Permission checks
  const hasPermission = (moduleName, action = "View") => {
    if (!activeRoleName) return false
    if (activeRoleName === "Admin") return true
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
        updateRolePermissions,
        hasPermission,
        canView,
        canAdd,
        canEdit,
        canDelete,
      }}
    >
      {children}
    </RoleContext.Provider>
  )
}

export function useRole() {
  const context = useContext(RoleContext)
  if (!context) {
    throw new Error("useRole must be used within RoleProvider")
  }
  return context
}
