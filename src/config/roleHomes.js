import {
  BedDouble,
  CalendarPlus,
  ChartColumn,
  Droplet,
  FileText,
  FlaskConical,
  HeartPulse,
  ListOrdered,
  Package,
  Pill,
  ReceiptIndianRupee,
  Search,
  Siren,
  Sparkles,
  Stethoscope,
  Syringe,
  UserPlus,
} from "lucide-react"

/*
 * What each staff role sees on its home page after signing in. Admin and
 * Hospital Manager keep the full hospital dashboard. Every other role gets
 * only the figures and shortcuts for its own work; `module` is still checked
 * with canView(), and the server enforces the same permissions.
 *
 * tiles: keys of the stat tiles defined in pages/Home.jsx.
 */
export const FULL_DASHBOARD_ROLES = ["Admin", "Hospital Manager"]

export const ROLE_HOMES = {
  Doctor: {
    title: "Your clinic today",
    tiles: ["appointments", "queue", "labPending"],
    showFlow: true,
    actions: [
      { to: "/queue", icon: ListOrdered, label: "Open queue", module: "Queue" },
      { to: "/consultation", icon: Stethoscope, label: "Start consultation", module: "Doctors" },
      { to: "/prescription", icon: FileText, label: "Prescriptions", module: "Prescriptions" },
      { to: "/ai-scribe", icon: Sparkles, label: "AI scribe", module: "AIScribe" },
      { to: "/laboratory", icon: FlaskConical, label: "Lab results", module: "Laboratory" },
    ],
  },
  Nurse: {
    title: "Your ward today",
    tiles: ["admissions", "beds", "queue"],
    actions: [
      { to: "/nurses", icon: HeartPulse, label: "Vitals and nursing", module: "Nurses" },
      { to: "/ipd", icon: BedDouble, label: "Ward and beds", module: "IPD" },
      { to: "/queue", icon: ListOrdered, label: "Open queue", module: "Queue" },
      { to: "/emergency", icon: Siren, label: "Emergency", module: "Emergency" },
    ],
  },
  Receptionist: {
    title: "Front desk today",
    tiles: ["patients", "appointments", "queue"],
    showFlow: true,
    showRecentPatients: true,
    actions: [
      { to: "/patients", icon: UserPlus, label: "Register patient", module: "Patients" },
      { to: "/appointments", icon: CalendarPlus, label: "New appointment", module: "Appointments" },
      { to: "/queue", icon: ListOrdered, label: "Open queue", module: "Queue" },
      { to: "/billing", icon: ReceiptIndianRupee, label: "Create invoice", module: "Billing" },
      { to: "/patients", icon: Search, label: "Find a patient", module: "Patients" },
    ],
  },
  Compounder: {
    title: "Pharmacy today",
    tiles: [],
    actions: [
      { to: "/pharmacy", icon: Pill, label: "Dispense medicines", module: "Pharmacy" },
      { to: "/compounter", icon: Syringe, label: "Compounding", module: "Compounders" },
      { to: "/prescription", icon: FileText, label: "Prescriptions", module: "Prescriptions" },
      { to: "/inventory", icon: Package, label: "Medicine stock", module: "Inventory" },
    ],
  },
  Pharmacist: {
    title: "Pharmacy today",
    tiles: [],
    actions: [
      { to: "/pharmacy", icon: Pill, label: "Dispense medicines", module: "Pharmacy" },
      { to: "/prescription", icon: FileText, label: "Prescriptions", module: "Prescriptions" },
      { to: "/inventory", icon: Package, label: "Medicine stock", module: "Inventory" },
      { to: "/compounter", icon: Syringe, label: "Compounding", module: "Compounders" },
    ],
  },
  "Lab Staff": {
    title: "Laboratory today",
    tiles: ["labPending", "labUrgent", "labCompleted"],
    actions: [{ to: "/laboratory", icon: FlaskConical, label: "Lab worklist", module: "Laboratory" }],
  },
  "Billing Staff": {
    title: "Billing today",
    tiles: ["billingPending", "revenueToday"],
    actions: [
      { to: "/billing", icon: ReceiptIndianRupee, label: "Create invoice", module: "Billing" },
      { to: "/reports", icon: ChartColumn, label: "Reports", module: "Reports" },
    ],
  },
  "Blood Bank Staff": {
    title: "Blood bank today",
    tiles: [],
    actions: [{ to: "/blood-bank", icon: Droplet, label: "Blood stock and requests", module: "BloodBank" }],
  },
  "Inventory Staff": {
    title: "Store today",
    tiles: [],
    actions: [{ to: "/inventory", icon: Package, label: "Inventory", module: "Inventory" }],
  },
}


/** Home configuration for a role, or null for the full dashboard. */
export function roleHomeFor(roleName) {
  if (!roleName || FULL_DASHBOARD_ROLES.includes(roleName)) return null
  return ROLE_HOMES[roleName] || null
}
