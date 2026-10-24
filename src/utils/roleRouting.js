const LOGIN_ROLE_KEY = "hms_login_role"

export const LOGIN_ROLES = [
  "Admin",
  "Doctor",
  "Nurse",
  "Compounder",
  "Receptionist",
  "Pharmacist",
  "Lab Staff",
  "Blood Bank Staff",
  "Billing Staff",
  "Inventory Staff",
  "Hospital Manager",
  "Patient",
]

export function saveSelectedLoginRole(role) {
  const next = LOGIN_ROLES.includes(role) ? role : "Patient"
  sessionStorage.setItem(LOGIN_ROLE_KEY, next)
  return next
}

export function getSelectedLoginRole() {
  const saved = sessionStorage.getItem(LOGIN_ROLE_KEY)
  return LOGIN_ROLES.includes(saved) ? saved : "Patient"
}

export function mapBackendRoleToUi(role) {
  if (!role) return null
  if (role === "Reception") return "Receptionist"
  if (role === "Pharmacist") return "Compounder"
  if (role === "Lab Staff") return "Lab Staff"
  if (role === "Blood Bank Staff") return "Blood Bank Staff"
  if (role === "Billing Staff") return "Billing Staff"
  if (role === "Inventory Staff") return "Inventory Staff"
  if (role === "Hospital Manager") return "Hospital Manager"
  return role
}

export function getAuthenticatedStaffRole(user) {
  if (!user) return null
  return mapBackendRoleToUi(
    user.user?.staff_role || user.staff_role || user.user?.roles?.[0] || user.roles?.[0]
  )
}

export function homePathForAuth({ isStaff, user, isPatient }) {
  if (isStaff && getAuthenticatedStaffRole(user)) {
    return "/"
  }
  if (isPatient) {
    return "/patient"
  }
  return "/staff-login"
}

const STAFF_ROUTE_MODULES = [
  ["/admin/users", "Users"],
  ["/admin/roles", "Roles"],
  ["/admin/hospitals", "Hospitals"],
  ["/admin/departments", "Departments"],
  ["/admin/permissions", "Permissions"],
  ["/admin", "Users"],
  ["/patients", "Patients"],
  ["/appointments", "Appointments"],
  ["/queue", "Queue"],
  ["/consultation", "Doctors"],
  ["/prescription", "Prescriptions"],
  ["/doctors", "Doctors"],
  ["/nurses", "Nurses"],
  ["/compounter", "Compounders"],
  ["/pharmacy", "Pharmacy"],
  ["/laboratory", "Laboratory"],
  ["/billing", "Billing"],
  ["/inventory", "Inventory"],
  ["/reports", "Reports"],
  ["/emergency", "Emergency"],
  ["/blood-bank", "BloodBank"],
  ["/ipd", "IPD"],
  ["/ai-scribe", "AIScribe"],
]

export function staffModuleForPath(pathname) {
  if (pathname === "/" || pathname === "/settings" || pathname === "/hospital-selection") {
    return null
  }
  const match = STAFF_ROUTE_MODULES.find(([prefix]) => pathname === prefix || pathname.startsWith(`${prefix}/`))
  return match ? match[1] : "Dashboard"
}
