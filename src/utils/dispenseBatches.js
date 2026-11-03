// Choosing which stock batch issues each medicine on a prescription.
// The server re-checks name, hospital, expiry and stock; this only
// pre-selects sensible batches and spots gaps before submitting.

const sameName = (a, b) =>
  String(a || "").trim().toLowerCase() === String(b || "").trim().toLowerCase()

/**
 * First day of the month after a "MM/YYYY" expiry, or null when unknown.
 * @param {string} expiry
 * @returns {Date | null}
 */
const expiryEnd = (expiry) => {
  const [month, year] = String(expiry || "").split("/").map(Number)
  if (!month || !year) return null
  return new Date(year, month, 1)
}

/**
 * Unexpired batches of one medicine, earliest expiry first (undated last).
 * @param {Array<{name: string, expiry: string}>} medicines hospital stock
 * @param {string} name prescribed medicine name
 * @param {Date} [today]
 */
export function usableBatches(medicines, name, today = new Date()) {
  const rank = (medicine) => expiryEnd(medicine.expiry)?.getTime() ?? Number.POSITIVE_INFINITY
  return medicines
    .filter((medicine) => sameName(medicine.name, name))
    .filter((medicine) => {
      const end = expiryEnd(medicine.expiry)
      return end === null || end > today
    })
    .sort((a, b) => rank(a) - rank(b))
}

/**
 * Prescription item id -> batch id ("" when no batch has enough stock).
 * @param {Array<{id: number, name: string, quantity: number}>} items
 * @param {Array<{id: number, name: string, stock: number, expiry: string}>} medicines
 * @param {Date} [today]
 * @returns {Record<number, number | "">}
 */
export function defaultBatches(items, medicines, today = new Date()) {
  return Object.fromEntries(
    items.map((item) => {
      const batch = usableBatches(medicines, item.name, today).find(
        (medicine) => Number(medicine.stock) >= Number(item.quantity)
      )
      return [item.id, batch ? batch.id : ""]
    })
  )
}

/**
 * Names of the prescribed medicines that have no batch chosen.
 * @param {Array<{id: number, name: string}>} items
 * @param {Record<number, number | "">} chosen
 * @returns {string[]}
 */
export function missingBatches(items, chosen) {
  return items.filter((item) => !chosen[item.id]).map((item) => item.name)
}
