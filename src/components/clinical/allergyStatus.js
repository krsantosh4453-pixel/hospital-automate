// What the clinician may be told about a patient's allergies (BUG-001).
//
// The backend's Patient.allergy_status is "Unknown" (nobody has asked),
// "No known allergies" (asked: none) or, derived, "Has allergies" (one is on
// record at any hospital). The allergy list a page can read is scoped to the
// selected hospital. So an empty list proves nothing: only an explicit
// "No known allergies" may be shown as such, and anything missing, null,
// unexpected or not loaded is unknown, never "none".

export const NO_KNOWN_ALLERGIES = "No known allergies"
export const HAS_ALLERGIES = "Has allergies"

/**
 * @param {{
 *   patient: { state: "loading" | "loaded" | "failed", data?: { allergy_status?: string } | null },
 *   allergies: { state: "loading" | "loaded" | "failed", data?: Array<object> },
 * }} input
 * @returns {{ kind: "loading" | "failed" | "known" | "nka" | "review" | "unknown", allergies?: Array<object> }}
 *   known: allergies recorded here; nka: explicitly recorded as none;
 *   review: on record but not visible here; unknown: nobody has asked.
 */
export function allergySummary({ patient, allergies }) {
  const listed = allergies?.state === "loaded" && Array.isArray(allergies.data) ? allergies.data : []
  // A recorded allergy is shown whatever else failed: it can only add caution.
  if (listed.length > 0) return { kind: "known", allergies: listed }
  if (patient?.state === "loading" || allergies?.state === "loading") return { kind: "loading" }
  if (patient?.state !== "loaded" || allergies?.state !== "loaded") return { kind: "failed" }

  const status = patient.data?.allergy_status
  if (status === NO_KNOWN_ALLERGIES) return { kind: "nka" }
  if (status === HAS_ALLERGIES) return { kind: "review" }
  return { kind: "unknown" }
}
