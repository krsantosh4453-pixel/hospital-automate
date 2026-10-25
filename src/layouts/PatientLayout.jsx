import { Outlet, NavLink, useLocation } from "react-router-dom"
import { useEffect, useState } from "react"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { useHospitals } from "../assets/context/HospitalsContext.jsx"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { BellIcon, CalendarDaysIcon, CreditCardIcon, DoorOpenIcon, FileTextIcon, FlaskConicalIcon, HospitalIcon, HouseIcon, MenuIcon, PillIcon, TicketIcon, XIcon } from "lucide-react"

const patientRoutes = [
  { path: "/patient", label: "Home", icon: <HouseIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> },
  { path: "/patient/appointments", label: "My Appointments", icon: <CalendarDaysIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> },
  { path: "/patient/queue", label: "My Queue / Token", icon: <TicketIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> },
  { path: "/patient/documents", label: "My Medical Records", icon: <FileTextIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> },
  { path: "/patient/prescriptions", label: "My Prescriptions", icon: <PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> },
  { path: "/patient/lab-results", label: "My Lab Reports", icon: <FlaskConicalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> },
  { path: "/patient/bills", label: "My Bills", icon: <CreditCardIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> },
  { path: "/patient/consent", label: "Notifications / Consent", icon: <BellIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> },
]

export default function PatientLayout() {
  const location = useLocation()
  const { patient, logout } = useAuth()
  const { language, setLanguage, t } = useLanguage()
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

  const closeSidebar = () => setSidebarOpen(false)

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className={`fixed left-0 top-0 h-full w-64 bg-white border-r border-gray-200 z-50 flex flex-col transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      }`}>
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl"><HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
            <div>
              <h2 className="font-bold text-gray-800">{language === "hi" ? "मरीज़ पोर्टल" : "Patient Portal"}</h2>
              <p className="text-xs text-gray-500">{patient?.name || "Patient"}</p>
              {myHospitals.length > 1 ? (
                <select
                  aria-label={t("Select Hospital")}
                  value={selectedHospital?.id || ""}
                  onChange={(e) => selectHospital(myHospitals.find((h) => String(h.id) === e.target.value))}
                  className="hms-input mt-2 w-full"
                >
                  {myHospitals.map((hospital) => (
                    <option key={hospital.id} value={hospital.id}>{hospital.name}</option>
                  ))}
                </select>
              ) : (
                selectedHospital && <p className="text-xs text-blue-600 mt-1">{selectedHospital.name}</p>
              )}
              <div className="mt-2 inline-flex bg-gray-100 rounded-lg p-0.5" role="group" aria-label="Language">
                <button
                  type="button"
                  onClick={() => setLanguage("en")}
                  aria-pressed={language === "en"}
                  className={`px-2 py-0.5 rounded-md text-xs font-semibold ${language === "en" ? "bg-white text-blue-600 shadow-sm" : "text-gray-600"}`}
                >
                  EN
                </button>
                <button
                  type="button"
                  onClick={() => setLanguage("hi")}
                  aria-pressed={language === "hi"}
                  className={`px-2 py-0.5 rounded-md text-xs font-semibold ${language === "hi" ? "bg-white text-blue-600 shadow-sm" : "text-gray-600"}`}
                >
                  हिंदी
                </button>
              </div>
            </div>
          </div>
          <button
            onClick={closeSidebar}
            className="lg:hidden p-2 text-gray-500 hover:text-gray-700"
          >
            <XIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {patientRoutes.map((route) => {
            const isActive = location.pathname === route.path
            return (
              <NavLink
                key={route.path}
                to={route.path}
                onClick={closeSidebar}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition ${
                  isActive
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`}
              >
                <span className="text-lg">{route.icon}</span>
                <span>{t(route.label)}</span>
              </NavLink>
            )
          })}
        </nav>

        <div className="p-4 border-t border-gray-100">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 text-red-600 hover:bg-red-50 rounded-xl text-sm font-medium transition"
          >
            <span className="text-lg"><DoorOpenIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></span>
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-white rounded-lg shadow-md border"
        onClick={() => setSidebarOpen(true)}
        aria-label="Open navigation menu"
      >
        <MenuIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />
      </button>

      {/* Main Content */}
      <main className="flex-1 lg:ml-64 min-h-screen">
        <div className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}