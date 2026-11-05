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

const saltOf = (medicine) => String(medicine?.genericName || "").trim().toLowerCase().split(/\s+/).join(" ")

/**
 * Quantity of a prescription item not yet dispensed.
 * @param {{quantity: number, dispensed?: number}} item
 */
export const remainingOf = (item) => Math.max(Number(item.quantity || 0) - Number(item.dispensed || 0), 0)

/**
 * Unexpired batches of other brands with the same salt as the prescribed
 * medicine (F8). Empty when the prescribed brand's salt is not recorded:
 * the server then refuses any substitute.
 */
export function substituteBatches(medicines, name, today = new Date()) {
  const salts = new Set(medicines.filter((m) => sameName(m.name, name)).map(saltOf).filter(Boolean))
  if (salts.size === 0) return []
  const others = medicines.filter((m) => !sameName(m.name, name) && salts.has(saltOf(m)))
  return [...new Set(others.map((m) => m.name.trim().toLowerCase()))]
    .flatMap((brand) => usableBatches(others, brand, today))
}

/**
 * Item id -> { batch, quantity, reason }: the batch defaultBatches would pick
 * and the whole remaining quantity.
 */
export function defaultLines(items, medicines, today = new Date()) {
  const owed = items.map((item) => ({ ...item, quantity: remainingOf(item) }))
  const batches = defaultBatches(owed, medicines, today)
  return Object.fromEntries(owed.map((item) => [item.id, { batch: batches[item.id], quantity: item.quantity, reason: "" }]))
}

/**
 * The dispense-prescription request body, or { problems } to show instead.
 * Lines with quantity 0 are left for later; anything short of the whole
 * remaining quantity is sent as a partial dispense.
 */
export function buildDispenseRequest(prescriptionId, items, lines, medicines) {
  const problems = []
  const body = []
  let partial = false
  for (const item of items) {
    const owed = remainingOf(item)
    if (owed === 0) continue
    const line = lines[item.id] || {}
    const quantity = Number(line.quantity || 0)
    if (quantity < owed) partial = true
    if (quantity === 0) continue
    if (quantity > owed) problems.push(`${item.name}: at most ${owed}`)
    if (!line.batch) problems.push(`${item.name}: choose a stock batch`)
    const chosen = medicines.find((m) => String(m.id) === String(line.batch))
    const substitute = chosen && !sameName(chosen.name, item.name)
    if (substitute && !String(line.reason || "").trim()) problems.push(`${item.name}: give the reason for the substitute`)
    body.push({ item: item.id, medicine: Number(line.batch), quantity, ...(substitute ? { substitute_reason: line.reason.trim() } : {}) })
  }
  if (body.length === 0) problems.push("Enter a quantity for at least one medicine")
  return problems.length ? { problems } : { body: { prescription: prescriptionId, partial, lines: body } }
}
