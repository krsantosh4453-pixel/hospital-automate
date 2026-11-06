import { createContext, useContext } from "react"

// The Prescription context and its hook. PrescriptionProvider (./PrescriptionProvider.jsx) supplies
// the value; they live in separate files so React Fast Refresh can hot-reload it.
export const PrescriptionContext = createContext()

export function usePrescription() {

  const context =
    useContext(
      PrescriptionContext
    )


  if (!context) {

    throw new Error(
      "usePrescription must be used inside PrescriptionProvider"
    )

  }


  return context
}
