/**
 * Newest answer per notifications_<channel> consent purpose, from rows the
 * server returns newest first: { sms: true, whatsapp: false, ... }.
 */
export function currentChoices(rows) {
  const choices = {}
  for (const row of rows) {
    const channel = String(row.purpose || "").replace(/^notifications_/, "")
    if (!row.purpose?.startsWith("notifications_") || channel in choices) continue
    choices[channel] = Boolean(row.granted)
  }
  return choices
}
