// How a patient is identified on screen: the UHID issued by this hospital
// (F1) when there is one, otherwise the record number as PAT-<id>. Local
// "PAT-..." ids are kept as they are, so "PAT-PAT-..." never appears.
export const displayPatientId = (patient) => {
  if (patient?.uhid) return patient.uhid
  const value = String(patient?.id ?? "")
  return value.toUpperCase().startsWith("PAT-") ? value : `PAT-${value}`
}
