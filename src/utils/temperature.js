// A body temperature is never shown without its unit (Prompt 4, BUG-005).
//
// Ward readings now carry `temperature_unit` ("C" or "F"). Older ward readings
// (and other clients) stored only the number, and the forms that took them
// were not consistent (the web nurse form said °F, the mobile form gave no
// unit), so those are shown as "unit not recorded", never guessed.

const UNITS = { C: "°C", F: "°F" }

/**
 * "98.6 °F", "37.2 °C", "98.6 (unit not recorded)", or "—" when not measured.
 * @param {string | number | null | undefined} value
 * @param {string | null | undefined} unit "C" | "F"
 */
export function formatTemperature(value, unit) {
  if (value === null || value === undefined || String(value).trim() === "") return "—"
  const suffix = UNITS[String(unit || "").toUpperCase()]
  return suffix ? `${String(value).trim()} ${suffix}` : `${String(value).trim()} (unit not recorded)`
}
