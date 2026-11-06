import { createContext, useContext } from "react"

// The Pharmacy context and its hook. PharmacyProvider (./PharmacyProvider.jsx) supplies
// the value; they live in separate files so React Fast Refresh can hot-reload it.
export const PharmacyContext = createContext(null)

export function usePharmacy() {
  const context = useContext(PharmacyContext)
  if (!context) {
    throw new Error("usePharmacy must be used inside PharmacyProvider")
  }
  return context
}
