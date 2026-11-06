// A prescription from /api/clinical/prescriptions/ in the shape the
// Prescription, Pharmacy and Reports screens use. `id` is the display number
// (RX-0001); every write uses `apiId`. Medicine instructions are passed on
// exactly as saved: nothing is filled in when the doctor left them blank.

const formatDate = (value) => {
  if (!value) return ""
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleDateString("en-IN")
}

/** @param {number|string} id @returns {string} */
export const rxNumber = (id) => `RX-${String(id).padStart(4, "0")}`

export const mapPrescriptionFromApi = (record) => ({
  id: rxNumber(record.id),
  apiId: record.id,
  hospitalId: record.hospital,
  patientId: record.patient,
  patientName: record.patient_name || "",
  patientUhid: record.patient_uhid || "",
  doctor: record.doctor_name || record.doctor || "",
  doctorId: record.doctor,
  visitId: record.visit,
  status: record.status,
  dispensedAt: record.dispensed_at || null,
  createdAt: formatDate(record.created_at),
  createdAtIso: record.created_at || "",
  // F13: a paper prescription transcribed by the pharmacy, and who checked it.
  source: record.source || "Electronic",
  originalPrescriberName: record.original_prescriber_name || "",
  originalPrescriberRegistration: record.original_prescriber_registration || "",
  originalPrescriptionDate: record.original_prescription_date || "",
  transcribedBy: record.transcribed_by ?? null,
  transcribedByName: record.transcribed_by_name || "",
  verifiedByName: record.verified_by_name || "",
  verifiedAt: record.verified_at || null,
  medicines: (record.items || []).map((item) => ({
    id: item.id,
    name: item.name,
    dosage: item.dosage,
    frequency: item.frequency,
    duration: item.duration,
    quantity: item.quantity,
    dispensed: item.dispensed_quantity || 0,
    instructions: item.instructions || "",
  })),
})

export const PAPER_SOURCE = "Paper transcription"
export const PENDING_VERIFICATION = "Pending Verification"
