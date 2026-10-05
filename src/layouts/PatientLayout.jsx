import { Outlet, NavLink, useLocation } from "react-router-dom"
import { useAuth } from "../assets/context/AuthContext.jsx"

const patientRoutes = [
  { path: "/patient", label: "Home", icon: "🏠" },
  { path: "/patient/appointments", label: "My Appointments", icon: "📅" },
  { path: "/patient/queue", label: "My Queue / Token", icon: "🎫" },
  { path: "/patient/documents", label: "My Medical Records", icon: "📄" },
  { path: "/patient/prescriptions", label: "My Prescriptions", icon: "💊" },
  { path: "/patient/lab-results", label: "My Lab Reports", icon: "🧪" },
  { path: "/patient/bills", label: "My Bills", icon: "💳" },
  { path: "/patient/consent", label: "Notifications / Consent", icon: "🔔" },
]

export default function PatientLayout() {
  const location = useLocation()
  const { patient, logout } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-white border-r border-gray-200 hidden lg:block flex flex-col">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">🏥</div>
            <div>
              <h2 className="font-bold text-gray-800">Patient Portal</h2>
              <p className="text-xs text-gray-500">{patient?.name || "Patient"}</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {patientRoutes.map((route) => {
            const isActive = location.pathname === route.path
            return (
              <NavLink
                key={route.path}
                to={route.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition ${
                  isActive
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`}
              >
                <span className="text-lg">{route.icon}</span>
                <span>{route.label}</span>
              </NavLink>
            )
          })}
        </nav>

        <div className="p-4 border-t border-gray-100">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 text-red-600 hover:bg-red-50 rounded-xl text-sm font-medium transition"
          >
            <span className="text-lg">🚪</span>
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Mobile sidebar overlay */}
      <div className="lg:hidden fixed inset-0 bg-black/50 z-40" />

      {/* Main Content */}
      <main className="flex-1 lg:ml-64 min-h-screen">
        <div className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}