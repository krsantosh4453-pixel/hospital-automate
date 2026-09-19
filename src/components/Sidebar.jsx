import { NavLink, useLocation } from "react-router-dom"
import { useSidebar } from "../assets/context/SidebarContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"

function Sidebar() {
  const location = useLocation()
  const { isSidebarOpen, toggleSidebar } = useSidebar()
  const { canView, activeRole, activeRoleName } = useRole()

  const menuClass = ({ isActive }) =>
    `block px-4 py-2 rounded-xl text-sm font-medium transition ${isActive
      ? "bg-blue-600 text-white shadow-sm"
      : "text-slate-300 hover:bg-slate-800 hover:text-white"
    }`

  const hasAdminAccess =
    canView("Users") ||
    canView("Roles") ||
    canView("Hospitals") ||
    canView("Departments") ||
    canView("Permissions")

  return (
    <aside
      className={`fixed left-0 top-16 h-[calc(100vh-4rem)] w-64 bg-slate-900 text-white overflow-y-auto z-30 transition-transform duration-300 ease-in-out shadow-xl flex flex-col justify-between ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
    >
      <div>
        {/* Sidebar Header & Collapse Toggle */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold tracking-wide text-white">
              HMS Portal
            </h2>
            <p className="text-[10px] text-slate-400">
              Hospital Management
            </p>
          </div>

          {/* Close Button matching user's icon */}
          <button
            type="button"
            onClick={toggleSidebar}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition cursor-pointer"
            title="Close sidebar"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="3" />
              <line x1="9" y1="3" x2="9" y2="21" strokeWidth="2.5" />
            </svg>
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1">

          {/* Home */}
          <NavLink to="/" className={menuClass}>
            🏠 Home
          </NavLink>

          {/* Dashboard */}
          {canView("Dashboard") && (
            <NavLink to="/dashboard" className={menuClass}>
              📊 Dashboard
            </NavLink>
          )}

          {/* Patients */}
          {canView("Patients") && (
            <NavLink to="/patients" className={menuClass}>
              👤 Patients
            </NavLink>
          )}

          {/* Appointments */}
          {canView("Appointments") && (
            <NavLink to="/appointments" className={menuClass}>
              📅 Appointments
            </NavLink>
          )}

          {/* Queue */}
          {canView("Queue") && (
            <NavLink to="/queue" className={menuClass}>
              🎫 Queue
            </NavLink>
          )}

          {/* Consultation
              The clinical consultation screen is a doctor-facing workflow.
              There is no dedicated "Consultation" module in ALL_MODULES, so it
              reuses the existing Doctors permission gate (Doctor + Admin roles
              already have it) instead of changing the permissions architecture. */}
          {canView("Doctors") && (
            <NavLink to="/consultation" className={menuClass}>
              🩺 Consultation
            </NavLink>
          )}

          {/* Prescription
              Prescription creation/management follows the same clinical
              workflow as Consultation, so it reuses the existing Doctors
              permission gate instead of adding a new module/permission. */}
          {canView("Doctors") && (
            <NavLink to="/prescription" className={menuClass}>
              💊 Prescription
            </NavLink>
          )}

          {/* Doctors */}
          {canView("Doctors") && (
            <NavLink to="/doctors" className={menuClass}>
              👨‍⚕️ Doctors
            </NavLink>
          )}

          {/* Nurses */}
          {canView("Nurses") && (
            <NavLink to="/nurses" className={menuClass}>
              👩‍⚕️ Nurses
            </NavLink>
          )}

          {/* Compounder */}
          {canView("Compounders") && (
            <NavLink to="/compounter" className={menuClass}>
              🧑‍💼 Compounder
            </NavLink>
          )}

          {/* Pharmacy */}
          {canView("Pharmacy") && (
            <NavLink to="/pharmacy" className={menuClass}>
              💊 Pharmacy
            </NavLink>
          )}

          {/* Laboratory */}
          {canView("Laboratory") && (
            <NavLink to="/laboratory" className={menuClass}>
              🧪 Laboratory
            </NavLink>
          )}

          {/* Billing */}
          {canView("Billing") && (
            <NavLink to="/billing" className={menuClass}>
              💳 Billing
            </NavLink>
          )}

          {/* Inventory */}
          {canView("Inventory") && (
            <NavLink to="/inventory" className={menuClass}>
              📦 Inventory
            </NavLink>
          )}

          {/* Reports */}
          {canView("Reports") && (
            <NavLink to="/reports" className={menuClass}>
              📊 Reports
            </NavLink>
          )}

          {/* Administration Section */}
          {hasAdminAccess && (
            <div className="pt-4 mt-2 border-t border-slate-800">
              <p className="px-4 mb-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Administration
              </p>

              <NavLink to="/admin" className={menuClass}>
                🛠️ Admin Dashboard
              </NavLink>

              {canView("Users") && (
                <NavLink to="/admin/users" className={menuClass}>
                  👥 Users
                </NavLink>
              )}

              {canView("Roles") && (
                <NavLink to="/admin/roles" className={menuClass}>
                  🔐 Roles
                </NavLink>
              )}

              {canView("Hospitals") && (
                <NavLink to="/admin/hospitals" className={menuClass}>
                  🏥 Hospitals
                </NavLink>
              )}

              {canView("Departments") && (
                <NavLink to="/admin/departments" className={menuClass}>
                  🏢 Departments
                </NavLink>
              )}

              {canView("Permissions") && (
                <NavLink to="/admin/permissions" className={menuClass}>
                  🔑 Permissions
                </NavLink>
              )}
            </div>
          )}

          {/* Settings */}
          <NavLink to="/settings" className={menuClass}>
            ⚙️ Settings
          </NavLink>

        </nav>
      </div>

      {/* Role Footer Badge */}
      <div className="p-3 m-3 rounded-xl bg-slate-800/90 border border-slate-700">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-semibold text-slate-200 truncate">
            Role: {activeRoleName}
          </span>
        </div>
        <p className="text-[10px] text-slate-400 mt-0.5 truncate">
          {activeRole?.description}
        </p>
      </div>

    </aside>
  )
}

export default Sidebar
