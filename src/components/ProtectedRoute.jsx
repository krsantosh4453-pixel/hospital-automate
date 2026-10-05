import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "../assets/context/AuthContext.jsx"

export function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500">Loading...</p>
        </div>
      </div>
    )
  }

  // TEMPORARY: Bypass authentication in development mode
  if (!isAuthenticated && import.meta.env.DEV) {
    return children
  }

  if (!isAuthenticated) {
    return <Navigate to="/staff-login" state={{ from: location }} replace />
  }

  if (allowedRoles && user?.role && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />
  }

  return children
}

export function PublicRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return children
}