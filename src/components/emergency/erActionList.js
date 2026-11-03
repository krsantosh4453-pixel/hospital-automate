// The 24 emergency row actions of requirement J3 (spec Part 4 §13).

// kind: "dialog" = existing ER dialog, "panel" = in this hub, "link" = another module.
export const ER_ACTIONS = [
  { group: "Care", id: "vitals", label: "Vitals", kind: "dialog", needsCare: true },
  { group: "Care", id: "notes", label: "Doctor notes", kind: "panel" },
  { group: "Care", id: "allergy", label: "Allergy", kind: "panel" },
  { group: "Care", id: "order", label: "Service order", kind: "dialog", needsCare: true },
  { group: "Care", id: "results", label: "Investigation result", kind: "panel" },
  { group: "Forms", id: "emergency-forms", label: "Emergency forms", kind: "panel" },
  { group: "Forms", id: "consent", label: "Consent forms", kind: "panel" },
  { group: "Forms", id: "generic-consent", label: "Generic consent form", kind: "panel" },
  { group: "Laboratory", id: "sample-collection", label: "Sample collection", kind: "link", to: "/laboratory" },
  { group: "Laboratory", id: "sample-dispatch", label: "Sample dispatch", kind: "link", to: "/laboratory" },
  { group: "Blood bank", id: "blood-request", label: "ER blood request", kind: "link", to: "/blood-bank" },
  { group: "Blood bank", id: "blood-receive", label: "ER blood receive", kind: "link", to: "/blood-bank" },
  { group: "Pharmacy", id: "medication", label: "ER drug / consumable request", kind: "dialog", needsCare: true },
  { group: "Pharmacy", id: "drug-receive", label: "ER drug / consumable receive", kind: "panel" },
  { group: "Transfer", id: "admit", label: "Transfer to in-patient", kind: "panel", needsCare: true },
  { group: "Transfer", id: "bed-transfer", label: "Bed transfer", kind: "link", to: "/ipd" },
  { group: "Billing", id: "charge-slip", label: "Charge slip details", kind: "panel" },
  { group: "Billing", id: "bill-preview", label: "Bill preview", kind: "panel" },
  { group: "Billing", id: "billing", label: "Billing", kind: "link", to: "/billing" },
  { group: "Discharge", id: "discharge", label: "Discharge", kind: "dialog", needsCare: true },
  { group: "Discharge", id: "discharge-summary", label: "Discharge summary", kind: "panel" },
  { group: "Discharge", id: "certificate", label: "Medical certificate", kind: "panel" },
  { group: "Record", id: "update-details", label: "Update details", kind: "link", to: "/patients" },
  { group: "Record", id: "medical-record", label: "Patient medical record", kind: "link", to: "/patients", record: true },
]

// Module constants: an inline array would re-run the consent panel's fetch on every render.
export const EMERGENCY_FORM_CODES = ["general-treatment", "surgery", "anesthesia"]
export const GENERIC_FORM_CODES = ["general-treatment"]

export function patientLink(action, visit) {
  const params = new URLSearchParams({ patient: String(visit.patient), q: visit.patient_name || "" })
  if (action.record) params.set("record", String(visit.patient))
  if (action.id === "update-details") params.set("edit", String(visit.patient))
  return `${action.to}?${params.toString()}`
}
