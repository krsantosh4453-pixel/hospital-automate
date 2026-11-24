// Indian rupees handled as whole paise (BUG-002). Amounts typed by a person
// or sent by the API are strings and are read exactly: more than two decimal
// places is refused, never rounded. Comparisons and sums use integer paise,
// so ₹33.60 stays ₹33.60 (no 33.599999… or silent ₹34).

const RUPEES = /^(-)?(\d+)(?:\.(\d{1,2}))?$/

/**
 * Paise in `value` ("33.60", "1,000.99", "100"), or NaN when it is not a
 * rupee amount with at most two decimals. A JavaScript number is taken to be
 * an already computed rupee amount and is rounded to the nearest paisa.
 * @param {string | number | null | undefined} value
 * @returns {number}
 */
export function toPaise(value) {
  if (typeof value === "number") return Number.isFinite(value) ? Math.round(value * 100) : NaN
  if (typeof value !== "string") return NaN
  const match = RUPEES.exec(value.trim().replace(/,/g, ""))
  if (!match) return NaN
  const [, minus, whole, fraction = ""] = match
  const paise = Number(whole) * 100 + Number(fraction.padEnd(2, "0"))
  return minus ? -paise : paise
}

/** "33.60" for 3360 paise: the exact string the API expects. */
export function fromPaise(paise) {
  const sign = paise < 0 ? "-" : ""
  const abs = Math.abs(paise)
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, "0")}`
}

/** "1,000.99" for 100099 paise (Indian digit grouping, always two decimals). */
export function formatRupees(paise) {
  const sign = paise < 0 ? "-" : ""
  const abs = Math.abs(paise)
  const rupees = Math.floor(abs / 100).toLocaleString("en-IN")
  return `${sign}${rupees}.${String(abs % 100).padStart(2, "0")}`
}

// Invoice statuses as the server writes them (billing.models.Invoice.Status).
const OWING = ["Unpaid", "Partially Paid"]

/**
 * Whether a bill still has money owing: the server's balance when it sent
 * one, else its status. A partially paid bill counts (BUG-002 / BUG-004).
 * @param {{ status?: string, balance_due?: string | number }} invoice
 */
export function hasBalanceDue(invoice) {
  if (!invoice || !OWING.includes(invoice.status)) return false
  if (invoice.balance_due === undefined || invoice.balance_due === null) return true
  return toPaise(invoice.balance_due) > 0
}

export const AMOUNT_FORMAT_ERROR = "Enter a valid amount in rupees, with at most 2 decimal places (for example 33.60)."

/**
 * The payment to record when the cashier sets the bill's total amount paid.
 * The form holds the running total paid; only the new money is sent.
 * @param {{ total: string | number, alreadyPaid: string | number, enteredPaid: string }} input
 * @returns {{ amount: string } | { error: string } | { info: string, alreadyPaid: string }}
 */
export function paymentToRecord({ total, alreadyPaid, enteredPaid }) {
  const entered = toPaise(String(enteredPaid ?? "").trim())
  if (Number.isNaN(entered) || entered < 0) return { error: AMOUNT_FORMAT_ERROR }
  if (entered === 0) return { error: "The amount paid must be greater than ₹0.00." }

  const totalPaise = toPaise(total)
  const paidPaise = toPaise(alreadyPaid || "0")
  if (Number.isNaN(totalPaise) || Number.isNaN(paidPaise)) return { error: "This bill's amounts could not be read. Reload and try again." }
  if (entered > totalPaise) return { error: `The amount paid cannot be more than the bill (₹${formatRupees(totalPaise)}).` }

  const additional = entered - paidPaise
  if (additional <= 0) {
    return {
      info: "₹{alreadyPaid} has already been received. To return money, record a refund instead of lowering the paid amount.",
      alreadyPaid: fromPaise(paidPaise),
    }
  }
  return { amount: fromPaise(additional) }
}
