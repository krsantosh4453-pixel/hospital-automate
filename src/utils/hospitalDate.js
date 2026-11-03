// The hospital's calendar day (India), as YYYY-MM-DD. The server counts days
// in the same zone (config/hospital_time.py); a UTC date would be yesterday
// between midnight and 05:30.
export const HOSPITAL_TIME_ZONE = "Asia/Kolkata"

export function hospitalToday(now = new Date()) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: HOSPITAL_TIME_ZONE }).format(now)
}
