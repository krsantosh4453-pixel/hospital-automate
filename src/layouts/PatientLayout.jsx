import { Outlet, NavLink, useLocation } from "react-router-dom"
import { useEffect, useState } from "react"
import { Bell, CalendarDays, FileText, FlaskConical, House, Menu, Pill, ReceiptIndianRupee, Ticket, X } from "lucide-react"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { useHospitals } from "../assets/context/HospitalsContext.jsx"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { BrandMark } from "../components/Sidebar.jsx"
import { HeaderActions } from "../components/HeaderMenus.jsx"

const patientRoutes = [
  { path: "/patient", label: "Home", icon: House, end: true },
  { path: "/patient/appointments", label: "My Appointments", icon: CalendarDays },
  { path: "/patient/queue", label: "My Queue / Token", icon: Ticket },
  { path: "/patient/documents", label: "My Medical Records", icon: FileText },
  { path: "/patient/prescriptions", label: "My Prescriptions", icon: Pill },
  { path: "/patient/lab-results", label: "My Lab Reports", icon: FlaskConical },
  { path: "/patient/bills", label: "My Bills", icon: ReceiptIndianRupee },
  { path: "/patient/consent", label: "Notifications / Consent", icon: Bell },
]

export default function PatientLayout() {
  const location = useLocation()
  const { t } = useLanguage()
  const { hospitals } = useHospitals()
  const { selectedHospital, selectHospital } = usePatient()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Records, appointments and consent are per hospital. Keep the selection
  // on a hospital this patient is registered at; pick it automatically when
  // there is only one.
  const myHospitals = hospitals.filter((hospital) => hospital.registered)
  useEffect(() => {
    if (myHospitals.length === 0) return
    const valid = selectedHospital && myHospitals.some((h) => String(h.id) === String(selectedHospital.id))
    if (!valid) selectHospital(myHospitals[0])
  }, [myHospitals, selectedHospital, selectHospital])

  // Close the drawer on navigation and on Escape.
  useEffect(() => setSidebarOpen(false), [location.pathname])
  useEffect(() => {
    if (!sidebarOpen) return undefined
    const onKey = (e) => e.key === "Escape" && setSidebarOpen(false)
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [sidebarOpen])

  const current = patientRoutes.find((r) => (r.end ? location.pathname === r.path : location.pathname.startsWith(r.path)))
  useEffect(() => {
    document.title = current ? `${t(current.label)} · Patient portal` : "Patient portal"
  }, [current, t])

  const sidebar = (
    <>
      <div className="border-b border-line px-5 pb-5 pt-5">
        <BrandMark inverted={false} />
        {myHospitals.length > 1 ? (
          <div className="mt-4">
            <label htmlFor="patient-hospital" className="hms-label">{t("Select Hospital")}</label>
            <select
              id="patient-hospital"
              value={selectedHospital?.id || ""}
              onChange={(e) => selectHospital(myHospitals.find((h) => String(h.id) === e.target.value))}
              className="hms-input w-full"
            >
              {myHospitals.map((hospital) => (
                <option key={hospital.id} value={hospital.id}>{hospital.name}</option>
              ))}
            </select>
          </div>
        ) : (
          selectedHospital && (
            <p className="mt-4 rounded-lg bg-brand-50 px-3 py-2 text-[13px] font-medium text-brand-800">{selectedHospital.name}</p>
          )
        )}
      </div>

      <nav aria-label="Patient portal" className="flex-1 space-y-0.5 overflow-y-auto px-3 py-3">
        {patientRoutes.map((route) => {
          const Icon = route.icon
          return (
            <NavLink
              key={route.path}
              to={route.path}
              end={route.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-50 text-brand-800" : "text-ink-600 hover:bg-ink-50 hover:text-ink-900"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={18} className={isActive ? "text-brand-600" : "text-ink-400"} aria-hidden="true" />
                  <span>{t(route.label)}</span>
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

    </>
  )

  return (
    <div className="min-h-screen">
      <a
        href="#patient-main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-[80] focus:rounded-lg focus:bg-brand-700 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white"
      >
        Skip to main content
      </a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-line bg-white/95 backdrop-blur lg:flex">{sidebar}</aside>

      {/* Top bar: page title, then notifications and the profile menu */}
      <header className="hms-surface-dark sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line px-4 sm:px-6 lg:ml-64 lg:px-8">
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="-ml-1 rounded-lg p-2 text-ink-700 hover:bg-ink-100 lg:hidden"
          aria-label="Open navigation menu"
        >
          <Menu size={20} aria-hidden="true" />
        </button>
        <p className="min-w-0 flex-1 truncate text-sm font-semibold text-ink-900">{current ? t(current.label) : "Patient portal"}</p>
        <HeaderActions hospitalId={selectedHospital?.id} />
      </header>
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-ink-950/45 animate-fade-in" onClick={() => setSidebarOpen(false)} aria-hidden="true" />
          <aside className="absolute inset-y-0 left-0 flex w-[min(18rem,85vw)] flex-col bg-white shadow-2xl animate-fade-in">
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="absolute right-3 top-4 rounded-lg p-2 text-ink-500 hover:bg-ink-100"
              aria-label="Close navigation menu"
            >
              <X size={18} aria-hidden="true" />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <main id="patient-main" tabIndex={-1} className="outline-none lg:pl-64">
        <div className="mx-auto w-full max-w-6xl px-4 py-5 sm:px-6 sm:py-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
