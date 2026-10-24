import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"

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
        const allPrescriptions = data?.results || data || []
        setPrescriptions(allPrescriptions)
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

  const filteredPrescriptions = prescriptions.filter((p) => {
    if (filter === "all") return true
    if (filter === "active") return p.status === "Active"
    if (filter === "completed") return p.status === "Completed"
    if (filter === "cancelled") return p.status === "Cancelled"
    return true
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Prescriptions</h1>
          <p className="text-gray-500 mt-1">View and manage your prescriptions</p>
        </div>
        <div className="flex gap-2">
          {["all", "active", "completed", "cancelled"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
                filter === f
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-200"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">⚠️ {error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : filteredPrescriptions.length > 0 ? (
        <div className="space-y-4">
          {filteredPrescriptions.map((rx) => (
            <div key={rx.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl">💊</span>
                    <div>
                      <h3 className="font-semibold text-gray-800 text-lg">{rx.medicine_name || "Medication"}</h3>
                      <p className="text-sm text-gray-500">Prescribed by {rx.doctor_name || "Doctor"} on {formatDate(rx.prescribed_date)}</p>
                    </div>
                    <span className={`ml-auto px-3 py-1 rounded-full text-xs font-medium ${
                      rx.status === "Active" ? "bg-green-100 text-green-700" :
                      rx.status === "Completed" ? "bg-gray-100 text-gray-700" :
                      "bg-red-100 text-red-700"
                    }`}>
                      {rx.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div><p className="text-gray-500">Dosage</p><p className="font-medium">{rx.dosage || "—"}</p></div>
                    <div><p className="text-gray-500">Frequency</p><p className="font-medium">{rx.frequency || "—"}</p></div>
                    <div><p className="text-gray-500">Duration</p><p className="font-medium">{rx.duration || "—"}</p></div>
                    <div><p className="text-gray-500">Quantity</p><p className="font-medium">{rx.quantity || "—"}</p></div>
                  </div>
                  {rx.instructions && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-xl">
                      <p className="text-sm text-gray-600"><strong>Instructions:</strong> {rx.instructions}</p>
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <button className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">View Details</button>
                  {rx.status === "Active" && (
                    <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50">Request Refill</button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
          <div className="text-4xl mb-3">💊</div>
          <h3 className="font-bold text-gray-800">No prescriptions found</h3>
          <p className="text-sm text-gray-500 mt-1">You don&apos;t have any prescriptions matching this filter.</p>
        </div>
      )}
    </div>
  )
}

export default PatientPrescriptions