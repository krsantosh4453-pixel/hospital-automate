// How a patient is identified on screen: the UHID issued by this hospital
// (F1) when there is one, otherwise the record number as PAT-<id>. Local
// "PAT-..." ids are kept as they are, so "PAT-PAT-..." never appears.
export const displayPatientId = (patient) => {
  if (patient?.uhid) return patient.uhid
  const value = String(patient?.id ?? "")
  return value.toUpperCase().startsWith("PAT-") ? value : `PAT-${value}`
}

/** Last four digits only, enough to tell patients apart at a counter; "" for short numbers. */
export const maskedPhone = (phone) => {
  const digits = String(phone || "").replace(/\D/g, "")
  return digits.length > 4 ? `••••${digits.slice(-4)}` : ""
}
