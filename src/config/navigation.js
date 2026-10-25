import {
  ChartColumn,
  BedDouble,
  Hospital,
  CalendarDays,
  ClipboardList,
  Droplet,
  FileText,
  FlaskConical,
  HeartPulse,
  House,
  KeyRound,
  LayoutDashboard,
  ListOrdered,
  Package,
  Pill,
  ReceiptIndianRupee,
  Settings,
  ShieldCheck,
  Siren,
  Sparkles,
  Stethoscope,
  UserRound,
  Users,
  UsersRound,
  Syringe,
} from "lucide-react"

/**
 * Staff navigation. `module` is the RoleContext module name passed to
 * canView(); null means every signed-in staff member sees it. Labels are
 * translation keys for LanguageContext.t().
 */
export const STAFF_NAV = [
  {
    id: "overview",
    label: "Overview",
    items: [{ to: "/", label: "Home", icon: House, module: null, end: true }],
  },
  {
    id: "front-desk",
    label: "Front desk",
    items: [
      { to: "/patients", label: "Patients", icon: UsersRound, module: "Patients" },
      { to: "/appointments", label: "Appointments", icon: CalendarDays, module: "Appointments" },
      { to: "/queue", label: "Queue", icon: ListOrdered, module: "Queue" },
    ],
  },
  {
    id: "clinical",
    label: "Clinical care",
    items: [
      // Consultation reuses the Doctors permission gate (no separate module exists).
      { to: "/consultation", label: "Consultation", icon: Stethoscope, module: "Doctors" },
      { to: "/prescription", label: "Prescription", icon: FileText, module: "Prescriptions" },
      { to: "/nurses", label: "Nurses / Vitals", icon: HeartPulse, module: "Nurses" },
      { to: "/ipd", label: "IPD / Ward / Beds", icon: BedDouble, module: "IPD" },
      { to: "/emergency", label: "Emergency", icon: Siren, module: "Emergency" },
      { to: "/ai-scribe", label: "AI Scribe", icon: Sparkles, module: "AIScribe" },
    ],
  },
  {
    id: "diagnostics",
    label: "Diagnostics & pharmacy",
    items: [
      { to: "/laboratory", label: "Laboratory", icon: FlaskConical, module: "Laboratory" },
      { to: "/pharmacy", label: "Pharmacy", icon: Pill, module: "Pharmacy" },
      { to: "/compounter", label: "Compounder", icon: Syringe, module: "Compounders" },
      { to: "/blood-bank", label: "Blood Bank", icon: Droplet, module: "BloodBank" },
    ],
  },
  {
    id: "operations",
    label: "Finance & operations",
    items: [
      { to: "/billing", label: "Billing", icon: ReceiptIndianRupee, module: "Billing" },
      { to: "/inventory", label: "Inventory", icon: Package, module: "Inventory" },
      { to: "/reports", label: "Reports", icon: ChartColumn, module: "Reports" },
    ],
  },
  {
    id: "people",
    label: "Staff",
    items: [{ to: "/doctors", label: "Doctors", icon: UserRound, module: "Doctors" }],
  },
  {
    id: "admin",
    label: "Administration",
    adminOnly: true,
    items: [
      { to: "/admin", label: "Admin Dashboard", icon: LayoutDashboard, module: null, end: true },
      { to: "/admin/users", label: "Users", icon: Users, module: "Users" },
      { to: "/admin/roles", label: "Roles", icon: ShieldCheck, module: "Roles" },
      { to: "/admin/hospitals", label: "Hospitals", icon: Hospital, module: "Hospitals" },
      { to: "/admin/departments", label: "Departments", icon: ClipboardList, module: "Departments" },
      { to: "/admin/permissions", label: "Permissions", icon: KeyRound, module: "Permissions" },
    ],
  },
  {
    id: "system",
    label: "System",
    items: [{ to: "/settings", label: "Settings", icon: Settings, module: null }],
  },
]

export const ADMIN_MODULES = ["Users", "Roles", "Hospitals", "Departments", "Permissions"]

/** Navigation filtered to what the current role may view. */
export function visibleStaffNav(canView) {
  const hasAdminAccess = ADMIN_MODULES.some((m) => canView(m))
  return STAFF_NAV.filter((group) => !group.adminOnly || hasAdminAccess)
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => item.module === null || canView(item.module)),
    }))
    .filter((group) => group.items.length > 0)
}

/** Title of the current staff route, for breadcrumbs and the document title. */
export function findNavItem(pathname) {
  for (const group of STAFF_NAV) {
    for (const item of group.items) {
      if (item.end ? pathname === item.to : pathname === item.to || pathname.startsWith(`${item.to}/`)) {
        return { group, item }
      }
    }
  }
  return null
}

