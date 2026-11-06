import { createContext, useContext } from "react"

// The role context, the built-in roles and their helpers. RoleProvider (./RoleProvider.jsx)
// supplies the value; they live in separate files so React Fast Refresh can hot-reload it.
export const RoleContext = createContext(null)

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
      Laboratory: ["View", "Add"],
      Reports: ["View"],
      IPD: ["View", "Add", "Edit"],
      Emergency: ["View", "Add", "Edit"],
      BloodBank: ["View", "Add"],
      AIScribe: ["View", "Add", "Edit"],
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
      Laboratory: ["View", "Edit"],
      Emergency: ["View", "Add", "Edit"],
      BloodBank: ["View"],
    },
  },
  {
    id: 4,
    name: "Compounder",
    description: "Dispense medicines, manage stock and pharmacy orders",
    permissions: {
      Dashboard: ["View"],
      Compounders: ["View", "Edit"],
      Prescriptions: ["View"],
      Pharmacy: ["View", "Add", "Edit"],
      Inventory: ["View", "Edit"],
      Reports: ["View"],
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
    },
  },
  {
    id: 6,
    name: "Pharmacist",
    description: "Manage pharmacy inventory, sales, and dispensing",
    permissions: {
      Dashboard: ["View"],
      Pharmacy: ["View", "Add", "Edit"],
      Prescriptions: ["View", "Edit"],
      Compounders: ["View"],
      Inventory: ["View", "Edit"],
      Reports: ["View"],
    },
  },
  {
    id: 7,
    name: "Lab Staff",
    description: "Manage laboratory tests and results",
    permissions: {
      Dashboard: ["View"],
      Laboratory: ["View", "Add", "Edit"],
      Reports: ["View"],
    },
  },
  {
    id: 8,
    name: "Blood Bank Staff",
    description: "Manage blood inventory, requests, and transactions",
    permissions: {
      Dashboard: ["View"],
      BloodBank: ["View", "Add", "Edit"],
      Reports: ["View"],
    },
  },
  {
    id: 9,
    name: "Billing Staff",
    description: "Manage invoices, payments, and insurance claims",
    permissions: {
      Dashboard: ["View"],
      Billing: ["View", "Add", "Edit"],
      Reports: ["View"],
    },
  },
  {
    id: 10,
    name: "Inventory Staff",
    description: "Manage procurement and stock",
    permissions: {
      Dashboard: ["View"],
      Inventory: ["View", "Add", "Edit"],
      Reports: ["View"],
    },
  },
  {
    id: 11,
    name: "Hospital Manager",
    description: "Hospital-level administration and oversight",
    permissions: {
      Dashboard: ["View"],
      Patients: ["View"],
      Appointments: ["View", "Add", "Edit"],
      Queue: ["View"],
      Doctors: ["View", "Add", "Edit"],
      Nurses: ["View", "Add", "Edit"],
      Compounders: ["View"],
      Pharmacy: ["View", "Add", "Edit"],
      Laboratory: ["View"],
      Billing: ["View", "Add", "Edit"],
      Inventory: ["View", "Add", "Edit"],
      Reports: ["View", "Add", "Edit"],
      Emergency: ["View"],
      BloodBank: ["View", "Add", "Edit"],
      IPD: ["View"],
      Users: ["View"],
      Hospitals: ["View"],
      Departments: ["View", "Add", "Edit"],
    },
  },
  {
    id: 12,
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

/** Staff roles allowed to open a module, for "only for …" messages. */
export function eligibleRolesFor(moduleName) {
  return DEFAULT_ROLES.filter((role) => role.name !== "Patient" && backendRoleCanView(role.name, moduleName)).map(
    (role) => role.name,
  )
}

export function useRole() {
  const context = useContext(RoleContext)
  if (!context) {
    throw new Error("useRole must be used within RoleProvider")
  }
  return context
}
