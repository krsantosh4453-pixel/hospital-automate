/** "20 Oct 2026" for printed documents; unparseable values are shown as given. */
export function formatPrintDate(value) {
  if (!value) return ""
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
}
