const TONES = {
  neutral: "bg-ink-100 text-ink-700 ring-ink-200",
  brand: "bg-brand-50 text-brand-700 ring-brand-200",
  accent: "bg-accent-50 text-accent-700 ring-accent-200",
  success: "bg-green-50 text-green-700 ring-green-200",
  warning: "bg-amber-50 text-amber-800 ring-amber-200",
  danger: "bg-red-50 text-red-700 ring-red-200",
}

const DOTS = {
  neutral: "bg-ink-400",
  brand: "bg-brand-500",
  accent: "bg-accent-500",
  success: "bg-green-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
}

export function Badge({ tone = "neutral", dot = false, icon: Icon, className = "", children }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap ${TONES[tone] || TONES.neutral} ${className}`}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${DOTS[tone] || DOTS.neutral}`} aria-hidden="true" />}
      {Icon && <Icon size={12} aria-hidden="true" strokeWidth={2.25} />}
      {children}
    </span>
  )
}

// Maps the status words used across the HMS API to a tone. The label itself is
// always shown, so status never relies on colour alone.
const STATUS_TONES = {
  success: [
    "active", "completed", "complete", "paid", "available", "administered", "released",
    "verified", "approved", "discharged", "confirmed", "in stock", "signed", "done",
    "normal", "resolved", "dispensed", "received", "finalized", "granted", "sent", "delivered",
  ],
  warning: [
    "pending", "partially paid", "partial", "waiting", "scheduled", "held", "in progress",
    "in_progress", "low stock", "draft", "on hold", "processing", "sample collected",
    "collected", "ordered", "due", "occupied", "under review", "pending review", "expiring",
  ],
  danger: [
    "cancelled", "canceled", "refused", "missed", "failed", "overdue", "critical",
    "out of stock", "expired", "rejected", "revoked", "inactive", "no show", "no-show",
    "unpaid", "abnormal", "urgent", "emergency", "vomited", "blocked",
  ],
  brand: ["called", "acknowledged", "ready", "in consultation", "admitted", "booked", "checked in", "checked-in", "new", "open"],
  accent: ["ai draft", "ai draft — pending review", "excluded", "prn", "maintenance", "reserved"],
}

export function statusTone(status) {
  const s = String(status || "").trim().toLowerCase()
  for (const [tone, words] of Object.entries(STATUS_TONES)) {
    if (words.includes(s)) return tone
  }
  return "neutral"
}

export function StatusBadge({ status, label, className = "" }) {
  if (status === null || status === undefined || status === "") return null
  const text = label || String(status).replace(/_/g, " ")
  return (
    <Badge tone={statusTone(status)} dot className={`capitalize ${className}`}>
      {text}
    </Badge>
  )
}

export default Badge
