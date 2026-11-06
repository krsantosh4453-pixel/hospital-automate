// Tabs of the Hospital services page. Roles mirror hospital_services/views.py;
// the server enforces them, these only decide what is shown.

const MANAGERS = ["Admin", "Hospital Manager"]
const when = (...statuses) => (row) => statuses.includes(row.status)
const dateTime = (key) => ({ key, label: "", render: (row) => (row[key] ? new Date(row[key]).toLocaleString("en-IN") : "—") })
const reason = [{ name: "reason", label: "Reason", required: true, wide: true }]
const patientField = (required = true) => ({
  name: "patient", label: "Patient", required, wide: true,
  source: { kind: "patients", label: (p) => `${p.name} · P${String(p.id).padStart(3, "0")}` },
})
const departmentField = (name = "department", label = "Department") => ({
  name, label, required: true, source: { kind: "departments", label: (d) => d.name },
})

export const SERVICE_TABS = [
  {
    id: "ot", label: "Operation theatre", roles: [...MANAGERS, "Doctor", "Nurse"],
    panels: [
      {
        resource: "ot-bookings", description: "Theatre schedule. A theatre cannot be booked twice for the same time.",
        createLabel: "Book theatre", createRoles: [...MANAGERS, "Doctor"],
        columns: [{ ...dateTime("scheduled_start"), label: "Starts" }, { key: "theatre_name", label: "Theatre" },
          { key: "patient_name", label: "Patient" }, { key: "procedure_name", label: "Procedure" },
          { key: "surgeon_name", label: "Surgeon" }, { key: "status", label: "Status" }],
        fields: [
          { name: "theatre", label: "Theatre", required: true, source: { kind: "service", resource: "theatres", label: (o) => o.name, filter: (o) => o.is_active } },
          { name: "surgeon", label: "Surgeon", required: true, source: { kind: "doctors", label: (d) => d.name } },
          patientField(),
          { name: "procedure_name", label: "Procedure", required: true, wide: true },
          { name: "scheduled_start", label: "Starts", type: "datetime-local", required: true },
          { name: "scheduled_end", label: "Ends", type: "datetime-local", required: true },
          { name: "anaesthesia", label: "Anaesthesia", options: ["General", "Spinal", "Regional", "Local", "Sedation"] },
          { name: "notes", label: "Notes", type: "textarea" },
        ],
        actions: [
          { verb: "start", label: "Start", when: when("Scheduled") },
          { verb: "complete", label: "Complete", when: when("In progress") },
          { verb: "cancel", label: "Cancel", when: when("Scheduled"), fields: reason, roles: [...MANAGERS, "Doctor"] },
        ],
      },
      {
        resource: "theatres", description: "Theatres and procedure rooms of this hospital.",
        createLabel: "Add theatre", createRoles: MANAGERS,
        columns: [{ key: "name", label: "Theatre" }, { key: "is_active", label: "In use" }],
        fields: [{ name: "name", label: "Name", required: true, wide: true }],
      },
    ],
  },
  {
    id: "ambulance", label: "Ambulance", roles: [...MANAGERS, "Receptionist", "Nurse"],
    panels: [
      {
        resource: "ambulance-trips", description: "Calls for an ambulance. One ambulance goes on one trip at a time.",
        createLabel: "New call",
        columns: [{ ...dateTime("requested_at"), label: "Called" }, { key: "caller_name", label: "Caller" },
          { key: "pickup", label: "Pickup" }, { key: "destination", label: "Destination" },
          { key: "vehicle_number", label: "Ambulance" }, { key: "status", label: "Status" }],
        fields: [
          { name: "caller_name", label: "Caller name", required: true }, { name: "caller_phone", label: "Caller phone", required: true },
          { name: "pickup", label: "Pickup address", required: true, wide: true }, { name: "destination", label: "Destination", required: true, wide: true },
          patientField(false),
        ],
        actions: [
          { verb: "dispatch_trip", label: "Dispatch", when: when("Requested"), fields: [
            { name: "ambulance", label: "Ambulance", required: true, source: { kind: "service", resource: "ambulances", label: (a) => `${a.vehicle_number} · ${a.kind}`, filter: (a) => a.status === "Available" } },
            { name: "crew", label: "Crew" }] },
          { verb: "complete", label: "Complete", when: when("Dispatched") },
          { verb: "cancel", label: "Cancel", when: when("Requested", "Dispatched") },
        ],
      },
      {
        resource: "ambulances", description: "The hospital's ambulances.", createLabel: "Add ambulance", createRoles: MANAGERS,
        columns: [{ key: "vehicle_number", label: "Vehicle" }, { key: "kind", label: "Type" }, { key: "status", label: "Status" }],
        fields: [{ name: "vehicle_number", label: "Vehicle number", required: true }, { name: "kind", label: "Type", options: ["BLS", "ALS"], required: true }],
      },
    ],
  },
  {
    id: "mortuary", label: "Mortuary", roles: [...MANAGERS, "Doctor", "Nurse"],
    panels: [{
      resource: "mortuary", description: "Bodies in the hospital's custody. Release needs a doctor or manager and, in a police case, the clearance reference.",
      createLabel: "Receive body",
      columns: [{ key: "deceased_name", label: "Name" }, { ...dateTime("time_of_death"), label: "Time of death" },
        { key: "storage_unit", label: "Unit" }, { key: "police_case", label: "Police case" }, { key: "status", label: "Status" },
        { key: "released_to_name", label: "Released to" }],
      fields: [
        patientField(false), { name: "deceased_name", label: "Name of the deceased", required: true, wide: true },
        { name: "time_of_death", label: "Time of death", type: "datetime-local", required: true },
        { name: "storage_unit", label: "Storage unit", required: true },
        { name: "certified_cause", label: "Cause as certified", wide: true },
        { name: "police_case", label: "Medico-legal (police) case", type: "checkbox" },
        { name: "police_reference", label: "Police reference" },
      ],
      actions: [{ verb: "release", label: "Release", when: when("In custody"), roles: [...MANAGERS, "Doctor"], fields: [
        { name: "released_to_name", label: "Released to", required: true }, { name: "released_to_relation", label: "Relation", required: true },
        { name: "released_to_id_last4", label: "ID last 4 digits", required: true }, { name: "police_reference", label: "Police clearance reference" }] }],
    }],
  },
  {
    id: "cssd", label: "CSSD", roles: [...MANAGERS, "Nurse", "Inventory Staff"],
    panels: [
      {
        resource: "sterilization-cycles", description: "Sterilization cycles. Only sterile, unexpired sets with a passed indicator are issued.",
        createLabel: "Record cycle",
        columns: [{ key: "set_code", label: "Set" }, { key: "set_name", label: "Name" }, { key: "method", label: "Method" },
          { key: "load_number", label: "Load" }, { ...dateTime("expires_at"), label: "Sterile until" },
          { key: "indicator_passed", label: "Indicator passed" }, { key: "issued_to_name", label: "Issued to" }, { key: "status", label: "Status" }],
        fields: [
          { name: "sterile_set", label: "Set", required: true, source: { kind: "service", resource: "sterile-sets", label: (s) => `${s.code} · ${s.name}` } },
          { name: "method", label: "Method", options: ["Autoclave", "ETO", "Plasma"], required: true },
          { name: "load_number", label: "Load number", required: true },
          { name: "sterilized_at", label: "Sterilized at", type: "datetime-local", required: true },
          { name: "expires_at", label: "Sterile until", type: "datetime-local", required: true },
          { name: "indicator_passed", label: "Indicator passed", type: "checkbox" },
        ],
        actions: [
          { verb: "issue", label: "Issue", when: when("Sterile"), fields: [departmentField("issued_to", "Issue to")] },
          { verb: "return", label: "Returned", when: when("Issued") },
        ],
      },
      {
        resource: "sterile-sets", description: "Instrument sets.", createLabel: "Add set",
        columns: [{ key: "code", label: "Code" }, { key: "name", label: "Name" }],
        fields: [{ name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }],
      },
    ],
  },
  {
    id: "laundry", label: "Laundry", roles: [...MANAGERS, "Nurse", "Inventory Staff"],
    panels: [{
      resource: "laundry", description: "Linen sent to the laundry and what came back.", createLabel: "Send linen",
      columns: [{ ...dateTime("sent_at"), label: "Sent" }, { key: "department_name", label: "Department" }, { key: "item_type", label: "Item" },
        { key: "quantity_sent", label: "Sent" }, { key: "quantity_returned", label: "Returned" }, { key: "shortfall", label: "Short" }, { key: "status", label: "Status" }],
      fields: [departmentField(), { name: "item_type", label: "Item", required: true, placeholder: "e.g. Bedsheets" },
        { name: "quantity_sent", label: "Quantity", type: "number", required: true }],
      actions: [{ verb: "returned", label: "Received back", when: when("Sent"), fields: [
        { name: "quantity_returned", label: "Quantity back", type: "number", required: true }, { name: "note", label: "Note" }] }],
    }],
  },
  {
    id: "leave", label: "Leave", roles: null,
    panels: [{
      resource: "leave", description: "Your leave requests. Administrators and managers see everyone's and decide.", createLabel: "Apply for leave",
      columns: [{ key: "staff_name", label: "Staff" }, { key: "kind", label: "Type" }, { key: "start_date", label: "From" },
        { key: "end_date", label: "To" }, { key: "status", label: "Status" }, { key: "decision_note", label: "Note" }],
      fields: [{ name: "kind", label: "Type", options: ["Casual", "Sick", "Earned", "Other"], required: true },
        { name: "start_date", label: "From", type: "date", required: true }, { name: "end_date", label: "To", type: "date", required: true },
        { name: "reason", label: "Reason", wide: true }],
      actions: [
        { verb: "approve", label: "Approve", when: when("Pending"), roles: MANAGERS },
        { verb: "reject", label: "Reject", when: when("Pending"), roles: MANAGERS, fields: [{ name: "note", label: "Reason", required: true, wide: true }] },
      ],
    }],
  },
  {
    id: "feedback", label: "Feedback", roles: [...MANAGERS, "Receptionist", "Nurse", "Doctor"],
    panels: [{
      resource: "feedback", description: "Patients' feedback, answered by an administrator or manager.", createLabel: "Record feedback",
      columns: [{ ...dateTime("created_at"), label: "When" }, { key: "patient_name", label: "Patient" }, { key: "rating", label: "Rating" },
        { key: "category", label: "About" }, { key: "comments", label: "Comments" }, { key: "status", label: "Status" }, { key: "response", label: "Response" }],
      fields: [patientField(false), { name: "rating", label: "Rating (1–5)", type: "number", required: true },
        { name: "category", label: "About", options: ["Care", "Cleanliness", "Waiting time", "Staff behaviour", "Billing", "Other"], required: true },
        { name: "comments", label: "Comments", type: "textarea" }],
      actions: [{ verb: "respond", label: "Respond", when: when("New", "Reviewed"), roles: MANAGERS, fields: [
        { name: "response", label: "Response or action taken", type: "textarea", required: true }, { name: "close", label: "Close it", type: "checkbox" }] }],
    }],
  },
  {
    id: "templates", label: "Templates", roles: [...MANAGERS, "Doctor", "Nurse"],
    panels: [{
      resource: "templates", description: "Reusable text: notes, discharge advice, letters and messages. {placeholders} are filled in when used.",
      createLabel: "New template", createRoles: [...MANAGERS, "Doctor"],
      columns: [{ key: "name", label: "Name" }, { key: "kind", label: "Kind" }, { key: "body", label: "Text", render: (row) => String(row.body).slice(0, 120) }],
      fields: [{ name: "name", label: "Name", required: true }, { name: "kind", label: "Kind", options: ["Clinical note", "Discharge advice", "Letter", "Message"], required: true },
        { name: "body", label: "Text", type: "textarea", required: true }],
    }],
  },
]
