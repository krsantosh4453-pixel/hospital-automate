// Human text for times and audit actions, through the page's t() so Hindi
// readers see Hindi. Unknown audit actions fall back to their words in English.

/** "just now", "5 min ago", "3 h ago", else the date. */
export function timeAgo(value, t = (text, vars) => fill(text, vars), now = Date.now(), locale = "en-IN") {
  const then = new Date(value).getTime()
  if (!Number.isFinite(then)) return ""
  const mins = Math.round((now - then) / 60000)
  if (mins < 1) return t("just now")
  if (mins < 60) return t("{count} min ago", { count: mins })
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return t("{count} h ago", { count: hrs })
  return new Date(value).toLocaleDateString(locale)
}

const fill = (text, vars = {}) => text.replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? `{${key}}`))

// Record types in audit action names ("clinical.vitalsign.create").
const SUBJECTS = {
  patient: "Patient", vitalsign: "Vital signs", diagnosis: "Diagnosis", clinicalnote: "Clinical note",
  serviceorder: "Service order", prescription: "Prescription", sale: "Pharmacy sale", invoice: "Invoice",
  payment: "Payment", refund: "Refund", advance: "Advance", admission: "Admission", appointment: "Appointment",
  visit: "Visit", labtest: "Lab test", labresult: "Lab result", maradministration: "Medicine dose", mar: "Medicine order",
  purchaseorder: "Purchase order", purchaserequisition: "Requisition", stockissue: "Stock issue", document: "Document",
  discharge_summary: "Discharge summary", staff: "Staff", hospital: "Hospital", break_glass: "Emergency access",
  staff_login: "Staff sign-in", record: "Consent", share: "Record share", discharge_draft: "AI discharge draft",
}

// What happened: the last part of the action name.
const VERBS = {
  create: "created", update: "updated", delete: "deleted", entered_in_error: "removed (entered in error)",
  read: "viewed", list: "listed", success: "succeeded", failed: "failed", finalize: "finalized",
  approved: "approved", rejected: "rejected", ordered: "ordered", cancelled: "cancelled", cancel: "cancelled",
  administered: "given", held: "held", refused: "refused", missed: "missed", excluded: "excluded",
  deposit: "received", applied: "applied to bill", returned: "returned", substituted: "substituted",
  open: "opened", end: "ended", review: "reviewed", signed: "signed", revoked: "revoked", granted: "granted",
  generated: "generated", reviewed: "reviewed", discharged: "discharged", accepted: "accepted",
}

const sentence = (text) => text.charAt(0).toUpperCase() + text.slice(1)

/** "ipd.discharge_summary.finalize" -> "Discharge summary finalized". */
export function describeAction(action, t = (text) => text) {
  const parts = String(action || "").split(".").filter(Boolean)
  const verb = parts[parts.length - 1]
  const subject = [...parts.slice(0, -1)].reverse().find((part) => SUBJECTS[part])
  if (subject && VERBS[verb]) return `${t(SUBJECTS[subject])} ${t(VERBS[verb])}`
  const text = (parts.length > 1 ? parts.slice(1) : parts).join(" ").replace(/_/g, " ")
  return sentence(text)
}
