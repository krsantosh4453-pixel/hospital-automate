import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { backendRoleCanView } from "../assets/context/RoleContext.jsx"
import { getAuthenticatedStaffRole, mapBackendRoleToUi, staffModuleForPath } from "../utils/roleRouting.js"
import GuestHome from "../pages/GuestHome.jsx"

function AuthLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-500">Loading...</p>
      </div>
    </div>
  )
}

export function ProtectedRoute({ audience = "staff" }) {
  const { isStaff, isPatient, isLoading, user } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <AuthLoading />
  }

  if (audience === "patient") {
    if (isStaff && !isPatient) {
      return <Navigate to="/" replace />
    }
    if (!isPatient) {
      return <Navigate to="/patient-login" state={{ from: location }} replace />
    }
    return <Outlet />
  }

  if (isPatient && !isStaff) {
    return <Navigate to="/patient" replace />
  }

  if (!isStaff) {
    // Visitors who have not signed in see the public home page (no figures,
    // no add actions); every other staff page asks them to sign in.
    if (location.pathname === "/") return <GuestHome />
    return <Navigate to="/staff-login" state={{ from: location }} replace />
  }

  const moduleName = staffModuleForPath(location.pathname)
  const rawRoles = user?.user?.roles || user?.roles || []
  const roleNames = rawRoles.map((role) => mapBackendRoleToUi(role)).filter(Boolean)
  const primaryRole = getAuthenticatedStaffRole(user)
  if (primaryRole && !roleNames.includes(primaryRole)) roleNames.unshift(primaryRole)
  if (moduleName && !roleNames.some((roleName) => backendRoleCanView(roleName, moduleName))) {
    // Another department's page: back to this role's home, which says why.
    return <Navigate to="/" replace state={{ denied: moduleName }} />
  }

  return <Outlet />
}

export function PublicRoute({ children }) {
  const { isStaff, isPatient, isLoading } = useAuth()

  if (isLoading) {
    return <AuthLoading />
  }

  if (isStaff) {
    return <Navigate to="/" replace />
  }

  if (isPatient) {
    return <Navigate to="/patient" replace />
  }

  return children
}
