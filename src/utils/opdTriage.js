// MF-012: OPD triage. Patients in today's queue who have not yet gone in to
// the doctor, offered to the nurse's vitals form beside the ward patients.
// The server decides who a nurse may record for (today's queue of their
// department); this only builds the choice.
const BEFORE_CONSULTATION = ["Waiting", "Called", "Acknowledged", "Ready"]

export function opdTriagePatients(tokens, today, alreadyListed = []) {
  const listed = new Set(alreadyListed.map((patient) => String(patient.id)))
  const seen = new Set()
  return tokens
    .filter((token) => token.token_date === today && BEFORE_CONSULTATION.includes(token.status))
    .sort((a, b) => a.token_number - b.token_number)
    .filter((token) => {
      const key = String(token.patient)
      if (listed.has(key) || seen.has(key)) return false
      seen.add(key)
      return true
    })
    .map((token) => ({
      id: token.patient,
      admissionId: null,
      hospitalId: token.hospital,
      name: token.patient_name || `Patient #${token.patient}`,
      ward: "OPD",
      bed: "",
      token: token.token_number,
      doctor: token.doctor_name || "",
    }))
}
