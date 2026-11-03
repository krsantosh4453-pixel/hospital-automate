import { createContext, useContext } from "react"

// The Auth context and its hook. AuthProvider (./AuthProvider.jsx) supplies
// the value; they live in separate files so React Fast Refresh can hot-reload it.
export const AuthContext = createContext()

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
