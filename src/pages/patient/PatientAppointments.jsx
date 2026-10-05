import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"

function PatientAppointments() {
  const { patient } = useAuth()
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState("all")

  useEffect(() => {
    if (!patient?.id) return

    const fetchAppointments = async () => {
      setLoading(true)
      try {
        const data = await api.appointments.list()
        const allAppointments = data?.results || data || []
        const patientAppointments = allAppointments.filter(
          (a) => String(a.patient) === String(patient.id)
        )
        setAppointments(patientAppointments)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchAppointments()
  }, [patient?.id])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  const filteredAppointments = appointments.filter((appt) => {
    if (filter === "all") return true
    if (filter === "upcoming") return appt.status === "Scheduled" || appt.status === "Confirmed"
    if (filter === "past") return appt.status === "Completed"
    if (filter === "cancelled") return appt.status === "Cancelled"
    return true
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Appointments</h1>
          <p className="text-gray-500 mt-1">Manage your medical appointments</p>
        </div>
        <div className="flex gap-2">
          {["all", "upcoming", "past", "cancelled"].map((f) => (
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
      ) : filteredAppointments.length > 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Date & Time</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Doctor</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Reason</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Status</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredAppointments.map((appt) => (
                  <tr key={appt.id} className="hover:bg-gray-50">
                    <td className="px-5 py-4">
                      <p className="font-medium text-gray-800">{formatDate(appt.appointment_date)}</p>
                      <p className="text-sm text-gray-500">{appt.appointment_time}</p>
                    </td>
                    <td className="px-5 py-4 text-gray-700">{appt.doctor_name || "—"}</td>
                    <td className="px-5 py-4 text-gray-700">{appt.reason || "—"}</td>
                    <td className="px-5 py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        appt.status === "Scheduled" ? "bg-blue-100 text-blue-700" :
                        appt.status === "Confirmed" ? "bg-green-100 text-green-700" :
                        appt.status === "Completed" ? "bg-gray-100 text-gray-700" :
                        "bg-red-100 text-red-700"
                      }`}>
                        {appt.status}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">View Details</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
          <div className="text-4xl mb-3">📅</div>
          <h3 className="font-bold text-gray-800">No appointments found</h3>
          <p className="text-sm text-gray-500 mt-1">You have no appointments matching this filter.</p>
        </div>
      )}
    </div>
  )
}

export default PatientAppointments