// Appointment.Status on the server (backend/appointments/models.py). A new
// booking is Scheduled; issuing, calling and finishing its queue token move it
// on, and the server does that itself.
export const APPOINTMENT_STATUSES = ["Scheduled", "Checked In", "In Consultation", "Completed", "Cancelled", "No Show"]

// Still ahead of the patient.
export const UPCOMING_STATUSES = ["Scheduled", "Checked In", "In Consultation"]

// Finished: cannot be edited or cancelled any more.
export const CLOSED_STATUSES = ["Completed", "Cancelled", "No Show"]
