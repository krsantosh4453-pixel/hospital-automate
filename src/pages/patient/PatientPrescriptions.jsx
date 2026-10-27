import { useEffect, useState } from "react"
import { Pill } from "lucide-react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { Alert, Card, EmptyState, SegmentedControl, SkeletonRows, StatusBadge, TableWrap } from "../../components/ui"

// Prescription.status is free text; these are the values the staff pages set.
const FILTERS = {
  all: () => true,
  current: (p) => p.status === "Confirmed" || p.status === "Pending",
  dispensed: (p) => p.status === "Dispensed",
  cancelled: (p) => p.status === "Cancelled",
}

function PatientPrescriptions() {
  const { patient } = useAuth()
  const [prescriptions, setPrescriptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState("all")

  useEffect(() => {
    if (!patient?.id) return

    const fetchPrescriptions = async () => {
      setLoading(true)
      try {
        const data = await api.clinical.prescriptions.list({ patientId: patient.id })
        setPrescriptions(data?.results || data || [])
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchPrescriptions()
  }, [patient?.id])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  const filteredPrescriptions = prescriptions.filter(FILTERS[filter] || FILTERS.all)

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink-900 sm:text-2xl">Prescriptions</h1>
          <p className="mt-1 text-sm text-ink-500">Medicines your doctors have prescribed.</p>
        </div>
        <SegmentedControl
          label="Filter prescriptions"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: "All" },
            { value: "current", label: "Current" },
            { value: "dispensed", label: "Dispensed" },
            { value: "cancelled", label: "Cancelled" },
          ]}
        />
      </header>

      {error && <Alert tone="danger">{error}</Alert>}

      {loading ? (
        <Card><SkeletonRows rows={3} /></Card>
      ) : filteredPrescriptions.length === 0 ? (
        <Card>
          <EmptyState
            icon={Pill}
            title={prescriptions.length ? "No prescriptions match this filter" : "No prescriptions yet"}
            description={prescriptions.length ? undefined : "Prescriptions from your visits will appear here."}
          />
        </Card>
      ) : (
        <ul className="space-y-4">
          {filteredPrescriptions.map((rx) => (
            <li key={rx.id}>
              <Card className="overflow-hidden">
                <div className="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
                  <div>
                    <p className="font-semibold text-ink-900">
                      {rx.doctor_name ? `Dr. ${rx.doctor_name.replace(/^Dr\.?\s*/i, "")}` : "Prescription"}
                    </p>
                    <p className="text-[13px] text-ink-500">
                      {formatDate(rx.created_at)}
                      {rx.hospital_name ? ` · ${rx.hospital_name}` : ""}
                      {rx.dispensed_at ? ` · dispensed ${formatDate(rx.dispensed_at)}` : ""}
                    </p>
                  </div>
                  <StatusBadge status={rx.status} />
                </div>
                {(rx.items || []).length > 0 ? (
                  <TableWrap className="border-t border-line">
                    <table className="hms-table">
                      <thead>
                        <tr>
                          <th scope="col">Medicine</th>
                          <th scope="col">Dose</th>
                          <th scope="col">How often</th>
                          <th scope="col">For</th>
                          <th scope="col" className="num">Qty</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rx.items.map((item, i) => (
                          <tr key={item.id || i}>
                            <td>
                              <span className="block font-medium text-ink-900">{item.name}</span>
                              {item.instructions && <span className="block text-xs text-ink-500">{item.instructions}</span>}
                            </td>
                            <td>{item.dosage || "—"}</td>
                            <td className="tabular-nums">{item.frequency || "—"}</td>
                            <td>{item.duration || "—"}</td>
                            <td className="num">{item.quantity ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </TableWrap>
                ) : (
                  <p className="border-t border-line px-5 py-3 text-sm text-ink-500">No medicines listed.</p>
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default PatientPrescriptions
