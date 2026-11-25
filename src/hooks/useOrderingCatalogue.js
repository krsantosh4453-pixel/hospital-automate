import { useEffect, useState } from "react"
import api from "../services/api.js"

const rows = (data) => (Array.isArray(data) ? data : data?.results || [])

/**
 * MF-007: the hospital's orderable services and stocked medicine names, offered
 * as suggestions while a doctor types. Typing anything else still works, and a
 * list that cannot be read (role, network) simply offers nothing.
 */
export function useOrderingCatalogue(hospitalId, { services = false, medicines = false } = {}) {
  const [catalogue, setCatalogue] = useState({ services: [], medicines: [] })

  useEffect(() => {
    if (!hospitalId) return undefined
    let current = true
    const read = (wanted, call) => (wanted ? Promise.resolve().then(call).then(rows).catch(() => []) : Promise.resolve([]))
    Promise.all([
      read(services, () => api.billing.priceList.catalogue(hospitalId)),
      read(medicines, () => api.pharmacy.medicines.formulary(hospitalId)),
    ]).then(([serviceRows, medicineRows]) => {
      if (current) setCatalogue({ services: serviceRows, medicines: medicineRows })
    })
    return () => {
      current = false
    }
  }, [hospitalId, services, medicines])

  return catalogue
}
