import { NavLink, useLocation } from "react-router-dom"

function Sidebar() {
  const location = useLocation()

  const menuClass = ({ isActive }) =>
    `block px-4 py-3 rounded-lg transition ${isActive
      ? "bg-blue-600 text-white"
      : "text-gray-300 hover:bg-slate-800 hover:text-white"
    }`

  return (
    <aside className="fixed left-0 top-16 h-[calc(100vh-4rem)] w-64 bg-slate-900 text-white overflow-y-auto">

      {/* Logo */}
      <div className="p-6 border-b border-slate-700">
        <h2 className="text-xl font-bold">
          HMS
        </h2>

        <p className="text-xs text-slate-400 mt-1">
          Hospital Management
        </p>
      </div>


      {/* Navigation */}
      <nav className="p-4 space-y-2">

        {/* Home */}
        <NavLink
          to="/"
          className={menuClass}
        >
          🏠 Home
        </NavLink>


        {/* Dashboard */}
        <NavLink
          to="/dashboard"
          className={menuClass}
        >
          📊 Dashboard
        </NavLink>


        {/* Patients */}
        <NavLink
          to="/patients"
          className={menuClass}
        >
          👤 Patients
        </NavLink>


        {/* Appointments */}
        <NavLink
          to="/appointments"
          className={menuClass}
        >
          📅 Appointments
        </NavLink>


        {/* Queue */}
        <NavLink
          to="/queue"
          className={menuClass}
        >
          🎫 Queue
        </NavLink>


        {/* Doctors */}
        <NavLink
          to="/doctors"
          className={menuClass}
        >
          👨‍⚕️ Doctors
        </NavLink>


        {/* Pharmacy */}
        <NavLink
          to="/pharmacy"
          className={menuClass}
        >
          💊 Pharmacy
        </NavLink>


        {/* Laboratory */}
        <NavLink
          to="/laboratory"
          className={menuClass}
        >
          🧪 Laboratory
        </NavLink>


        {/* Billing */}
        <NavLink
          to="/billing"
          className={menuClass}
        >
          💳 Billing
        </NavLink>


        {/* Inventory */}
        <NavLink
          to="/inventory"
          className={menuClass}
        >
          📦 Inventory
        </NavLink>


        {/* Reports */}
        <NavLink
          to="/reports"
          className={menuClass}
        >
          📊 Reports
        </NavLink>


        {/* Settings */}
        <NavLink
          to="/settings"
          className={menuClass}
        >
          ⚙️ Settings
        </NavLink>

      </nav>

    </aside>
  )
}

export default Sidebar