// BUG-013: a doctor placing an order or writing a prescription is the
// default doctor on it, instead of "Not specified". Doctor records carry
// the id of the login they belong to (`user`); the signed-in staff user's id
// is `user.id` (or `user.user.id`, depending on where it was loaded).

/** The id (as a string) of the signed-in user's own doctor record in `doctors`, or "". */
export function ownDoctorId(doctors, signedInUser) {
  const userId = signedInUser?.user?.id ?? signedInUser?.id
  if (userId == null) return ""
  const own = (doctors || []).find((doctor) => doctor?.user != null && String(doctor.user) === String(userId))
  return own ? String(own.id) : ""
}
