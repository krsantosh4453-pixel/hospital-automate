import { useEffect, useState } from "react"
import { usePatient } from "../../assets/context/PatientContext.jsx"
import api from "../../services/api.js"
import { Alert, PageHeader } from "../../components/ui"

// Roles are fixed in the backend (users.models.StaffRole) and the server
// decides access per hospital membership. This matrix summarises the
// permission classes on each API (e.g. clinical/views.py); it is read-only
// here because changing it in the browser would not change what the server
// allows. "Admin" is included in every clinical role check on the server.
const ROLE_DESCRIPTIONS = {
  Admin: "Full administration of this hospital, including staff and settings",
  "Hospital Manager": "Hospital operations, staff (except Admins), billing and reports",
  Doctor: "Consultations, diagnoses, prescriptions, orders, AI notes, discharge summaries",
  Nurse: "Vitals, nursing notes and assessments, MAR, sample collection, IPD and ER care",
  Receptionist: "Patient registration, appointments, queue and OPD billing",
  Pharmacist: "Medicines, stock, dispensing and pharmacy sales",
  Compounder: "Medicine preparation and dispensing support",
  "Lab Staff": "Sample handling, result entry, verification and release",
  "Billing Staff": "Invoices, payments, refunds and insurance claims",
  "Inventory Staff": "Suppliers, purchase orders, goods receipt and stock",
  "Blood Bank Staff": "Blood inventory, requests and issue",
}

// module -> roles allowed (R = read, W = write)
const MATRIX = [
  ["Patients", { Receptionist: "RW", Doctor: "RW", Nurse: "RW", Admin: "RW" }],
  ["Appointments", { Receptionist: "RW", Doctor: "RW", Admin: "RW", "Hospital Manager": "RW" }],
  ["Visits & Queue", { Receptionist: "RW", Doctor: "RW", Nurse: "RW", Admin: "RW", "Hospital Manager": "RW" }],
  ["Vitals / Allergies / Orders", { Doctor: "RW", Nurse: "RW", Admin: "RW", "Hospital Manager": "RW" }],
  ["Diagnoses / Clinical Notes", { Doctor: "RW", Admin: "RW", "Hospital Manager": "RW" }],
  ["Prescriptions", { Doctor: "RW", Pharmacist: "R", Admin: "RW", "Hospital Manager": "RW" }],
  ["AI Draft Approval", { Doctor: "RW" }],
  ["Laboratory Results", { "Lab Staff": "RW", Doctor: "R", Nurse: "R" }],
  ["Sample Collection", { "Lab Staff": "RW", Nurse: "RW" }],
  ["Nursing / MAR", { Nurse: "RW", Doctor: "RW", Admin: "RW" }],
  ["IPD & Emergency", { Doctor: "RW", Nurse: "RW", Admin: "RW" }],
  ["Discharge Summary", { Doctor: "RW", Admin: "RW" }],
  ["Pharmacy & Stock", { Pharmacist: "RW", Admin: "RW", "Hospital Manager": "RW" }],
  ["Billing & Payments", { "Billing Staff": "RW", Receptionist: "RW", Admin: "RW", "Hospital Manager": "RW" }],
  ["Insurance Claims", { "Billing Staff": "RW", Admin: "RW", "Hospital Manager": "RW" }],
  ["Procurement", { "Inventory Staff": "RW", Admin: "RW", "Hospital Manager": "RW" }],
  ["Blood Bank", { "Blood Bank Staff": "RW", "Lab Staff": "RW", Doctor: "RW", Nurse: "RW", Admin: "RW", "Hospital Manager": "RW" }],
  ["Staff Administration", { Admin: "RW", "Hospital Manager": "RW" }],
  ["Audit Log", { Admin: "R" }],
]

const ROLES = Object.keys(ROLE_DESCRIPTIONS)

function Roles() {
  const { selectedHospital } = usePatient()
  const [counts, setCounts] = useState({})
  const [countError, setCountError] = useState("")

  useEffect(() => {
    if (!selectedHospital) return
    api.users
      .list()
      .then((data) => {
        const next = {}
        for (const member of data.staff || []) {
          if (member.membership?.is_active) {
            next[member.membership.role] = (next[member.membership.role] || 0) + 1
          }
        }
        setCounts(next)
        setCountError("")
      })
      .catch((err) => setCountError(err.message || "Staff counts unavailable."))
  }, [selectedHospital])

  return (
    <div className="space-y-5">
      <PageHeader
        title="Roles"
        description="The server enforces these roles for each hospital membership. Assign roles to people on the Users page."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Administration", to: "/admin" }, { label: "Roles" }]}
      />

      {countError && <Alert tone="warning">{countError}</Alert>}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
        {ROLES.map((role) => (
          <div key={role} className="rounded-2xl border border-line bg-white p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">{role}</h2>
              <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                {counts[role] || 0} active
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-2">{ROLE_DESCRIPTIONS[role]}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow p-5 overflow-x-auto">
        <h2 className="text-lg font-semibold text-gray-800 mb-1">Access Matrix</h2>
        <p className="text-xs text-gray-500 mb-4">R = read, RW = read and write. Patients see only their own released records.</p>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="py-2 pr-3 sticky left-0 bg-white">Module</th>
              {ROLES.map((role) => (
                <th key={role} className="py-2 px-2 whitespace-nowrap">{role}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MATRIX.map(([module, access]) => (
              <tr key={module} className="border-b last:border-0">
                <td className="py-2 pr-3 font-medium text-gray-700 sticky left-0 bg-white whitespace-nowrap">{module}</td>
                {ROLES.map((role) => (
                  <td key={role} className="py-2 px-2 text-center">
                    {access[role] ? (
                      <span className={`px-2 py-0.5 rounded ${access[role] === "RW" ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-700"}`}>
                        {access[role]}
                      </span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Roles
