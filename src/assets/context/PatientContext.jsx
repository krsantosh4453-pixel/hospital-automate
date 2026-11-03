import { createContext, useContext } from "react"

// The Patient context and its hook. PatientProvider (./PatientProvider.jsx) supplies
// the value; they live in separate files so React Fast Refresh can hot-reload it.
export const PatientContext = createContext()

export function usePatient() {

  return useContext(PatientContext)

}
