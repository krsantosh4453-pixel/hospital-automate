// The appointment reference staff see and search by ("A007"). Patients see the
// same one (audit P5-07) so the front desk can find their booking from it.
export function appointmentRef(id) {
  if (id === null || id === undefined || id === "") return ""
  return `A${String(id).padStart(3, "0")}`
}
