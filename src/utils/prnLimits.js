// H-10: as-needed (PRN) medicine orders and their dose limits.

// The same words the server reads as "as needed" (backend/nurses/frequency.py).
const PRN_WORD = /\b(PRN|SOS|AS NEEDED|AS REQUIRED)\b/i

/** @param {string | null | undefined} frequency */
export const isPrnFrequency = (frequency) => PRN_WORD.test(frequency || "")

/**
 * The order's limits as one short line, e.g. "at least 4 h apart · max 3 in 24 h".
 * @param {{ prn_min_interval_minutes?: number | null, prn_max_doses_per_24h?: number | null }} order
 * @param {(text: string, values?: object) => string} t
 * @returns {string} empty when the order has no limits
 */
export const prnLimitText = (order, t) => {
  const parts = []
  if (order.prn_min_interval_minutes) {
    const hours = order.prn_min_interval_minutes / 60
    parts.push(t("at least {hours} h apart", { hours: Number.isInteger(hours) ? hours : hours.toFixed(2) }))
  }
  if (order.prn_max_doses_per_24h) parts.push(t("max {count} in 24 h", { count: order.prn_max_doses_per_24h }))
  return parts.join(" · ")
}
