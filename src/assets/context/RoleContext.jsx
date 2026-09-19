import { createContext, useContext, useState, useEffect } from "react"

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
    },
  },
  {
    id: 4,
    name: "Compounder",
    description: "Dispense medicines, manage stock and pharmacy orders",
    permissions: {
      Dashboard: ["View"],
      Compounders: ["View", "Edit"],
      Prescriptions: ["View", "Edit"],
      Pharmacy: ["View", "Add", "Edit"],
      Inventory: ["View"],
    },
  },
  {
    id: 5,
    name: "Reception",
    description: "Patient registration, token generation, appointments, and billing",
    permissions: {
      Dashboard: ["View"],
      Patients: ["View", "Add", "Edit"],
      Appointments: ["View", "Add", "Edit"],
      Queue: ["View", "Edit"],
      Billing: ["View", "Add"],
      Doctors: ["View"],
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

export function RoleProvider({ children }) {
  // Load roles & permissions from localStorage or defaults
  const [roles, setRoles] = useState(() => {
    const saved = localStorage.getItem("hms_role_permissions")
    if (saved) {
      try {
        return JSON.parse(saved)
      } catch (e) {
        console.error("Failed to parse saved role permissions:", e)
      }
    }
    return DEFAULT_ROLES
  })

  // Active role (e.g. "Admin", "Doctor", "Nurse", "Compounder", "Reception", "Patient")
  const [activeRoleName, setActiveRoleName] = useState(() => {
    return localStorage.getItem("hms_active_role") || "Admin"
  })

  // Save roles whenever changed
  useEffect(() => {
    localStorage.setItem("hms_role_permissions", JSON.stringify(roles))
  }, [roles])

  // Save active role whenever changed
  useEffect(() => {
    localStorage.setItem("hms_active_role", activeRoleName)
  }, [activeRoleName])

  // Current active role object
  const activeRole = roles.find((r) => r.name === activeRoleName) || roles[0]

  // Switch the active user role
  const switchRole = (roleName) => {
    const found = roles.find((r) => r.name.toLowerCase() === roleName.toLowerCase())
    if (found) {
      setActiveRoleName(found.name)
    }
  }

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
    if (!activeRole) return false
    // Admin has superuser access
    if (activeRole.name === "Admin") return true

    const rolePerms = activeRole.permissions || {}
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
