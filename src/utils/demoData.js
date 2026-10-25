// Earlier builds seeded browser storage with made-up patients and
// appointments, which then appeared next to real records. These signatures
// match only those seed rows (same id, name and phone/doctor), so a real
// record is never removed.
const DEMO_ROWS = {
  appointments: [
    { id: "A001", patient: "Rahul Kumar", doctor: "Dr. Sharma" },
    { id: "A002", patient: "Priya Singh", doctor: "Dr. Verma" },
    { id: "A003", patient: "Amit Kumar", doctor: "Dr. Singh" },
  ],
  patients: [
    { id: 1, name: "Rahul Kumar", phone: "9876543210" },
    { id: 2, name: "Priya Singh", phone: "9876543211" },
    { id: 3, name: "Amit Kumar", phone: "9876543212" },
    { id: 4, name: "Neha Kumari", phone: "9876543213" },
    { id: 5, name: "Ravi Sharma", phone: "9876543214" },
  ],
}

export function withoutDemoRows(rows, kind) {
  if (!Array.isArray(rows)) return []
  const demo = DEMO_ROWS[kind] || []
  return rows.filter(
    (row) =>
      row?.apiId !== undefined ||
      !demo.some((d) => Object.entries(d).every(([k, v]) => String(row?.[k]) === String(v))),
  )
}
