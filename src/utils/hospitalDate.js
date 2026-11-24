// The hospital's calendar day (India), as YYYY-MM-DD. The server counts days
// in the same zone (config/hospital_time.py); a UTC date would be yesterday
// between midnight and 05:30.
export const HOSPITAL_TIME_ZONE = "Asia/Kolkata"

export function hospitalToday(now = new Date()) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: HOSPITAL_TIME_ZONE }).format(now)
}

// BUG-003 (Prompt 4): start a booking on a day the doctor works. The server's
// `working_days` use 0 = Monday … 6 = Sunday; null means no rule (any day).
// The server still checks every booking; this only avoids offering a day off.
const serverWeekday = (iso) => (new Date(`${iso}T12:00:00Z`).getUTCDay() + 6) % 7

/** The first date on or after `iso` (not after `lastIso`) the doctor works, else `iso`. */
export function nextWorkingDate(iso, workingDays, lastIso) {
  if (!Array.isArray(workingDays) || workingDays.length === 0) return iso
  const start = new Date(`${iso}T12:00:00Z`)
  for (let step = 0; step < 7; step += 1) {
    const candidate = new Date(start.getTime() + step * 86400000).toISOString().slice(0, 10)
    if (lastIso && candidate > lastIso) break
    if (workingDays.includes(serverWeekday(candidate))) return candidate
  }
  return iso
}
