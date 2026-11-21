// Bill lines on the web Billing page (BUG-07, B-1).

// Charged automatically from the work itself (backend billing/charges.py and
// ipd/discharge.py); the server refuses these on a hand-added line.
export const AUTOMATIC_CATEGORIES = ["consultation", "laboratory", "bed"]

export const CATEGORY_LABELS = {
  consultation: "Consultation",
  laboratory: "Laboratory investigation",
  bed: "Bed charge per day",
  inpatient: "Inpatient service",
  procedure: "Procedure",
  other: "Other service",
}

// The four typed amounts of the invoice form, by the line names it writes.
export const FORM_LINE_NAMES = ["Doctor Consultation", "Laboratory Services", "Pharmacy / Medicines", "Other Services"]

const money = (value) => Number(value || 0)

/** A price-list line's amount with its GST, as the server will bill it. */
export const pricedAmount = (line) =>
  Math.round(money(line.unit_price) * (line.quantity || 1) * (1 + money(line.tax_rate) / 100) * 100) / 100

/** Price-list entries a person may add to a bill by hand (not the automatic ones). */
export const pickablePrices = (prices) =>
  (prices || []).filter((p) => !AUTOMATIC_CATEGORIES.includes(p.category) && p.is_current !== false)

/**
 * Lines of an existing bill the form's four amounts do not cover: priced
 * lines and other hand-typed lines. They are kept on save, never dropped.
 * @returns {{ priced: object[], kept: object[] }}
 */
export const otherLinesOf = (items) => {
  const priced = []
  const kept = []
  for (const item of items || []) {
    if (item.service_price) {
      priced.push({ id: item.service_price, name: item.description, unit_price: item.unit_price,
        tax_rate: item.tax_rate, quantity: item.quantity || 1 })
    } else if (!FORM_LINE_NAMES.includes(item.description)) {
      kept.push({ description: item.description, quantity: item.quantity || 1, unit_price: item.unit_price,
        tax_rate: item.tax_rate })
    }
  }
  return { priced, kept }
}

/** items_data for the server: typed amounts, priced lines, and kept lines. */
export const itemsData = (services, priced = [], kept = []) => [
  ...services.map((s) => ({ description: s.name, quantity: 1, unit_price: s.amount })),
  ...priced.map((p) => ({ service_price: p.id, quantity: p.quantity || 1 })),
  ...kept,
]
