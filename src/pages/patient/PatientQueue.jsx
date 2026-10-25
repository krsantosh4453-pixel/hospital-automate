import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { BellIcon, CircleCheckIcon, TicketIcon, TriangleAlertIcon } from "lucide-react"

function PatientQueue() {
  const { patient } = useAuth()
  const [queueTokens, setQueueTokens] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!patient?.id) return

    const fetchQueue = async () => {
      setLoading(true)
      try {
        const data = await api.queue.list()
        const allTokens = data?.results || data || []
        const patientTokens = allTokens.filter(
          (t) => String(t.patient) === String(patient.id) && t.status !== "Completed"
        )
        setQueueTokens(patientTokens)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchQueue()
    const interval = setInterval(fetchQueue, 30000)
    return () => clearInterval(interval)
  }, [patient?.id])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  const formatTime = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
  }

  const getStatusClass = (status) => {
    if (status === "Waiting") return "bg-orange-100 text-orange-700"
    if (status === "Called") return "bg-purple-100 text-purple-700"
    if (status === "Acknowledged") return "bg-indigo-100 text-indigo-700"
    if (status === "Ready") return "bg-teal-100 text-teal-700"
    if (status === "In Consultation") return "bg-blue-100 text-blue-700"
    if (status === "Completed") return "bg-green-100 text-green-700"
    if (status === "Skipped") return "bg-gray-100 text-gray-700"
    if (status === "No Show") return "bg-red-100 text-red-700"
    if (status === "Cancelled") return "bg-slate-100 text-slate-700"
    return "bg-gray-100 text-gray-700"
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Queue Status</h1>
        <p className="text-gray-500 mt-1">Track your position in the consultation queue</p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm"><TriangleAlertIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> {error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : queueTokens.length > 0 ? (
        <div className="space-y-4">
          {queueTokens.map((token) => (
            <div key={token.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-purple-100 rounded-xl flex items-center justify-center text-3xl"><TicketIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
                  <div>
                    <p className="text-sm text-gray-500">Token Number</p>
                    <h2 className="text-3xl font-bold text-gray-800">#{token.token_number}</h2>
                    <p className="text-sm text-gray-500 mt-1">{formatDate(token.token_date)} • {token.doctor_name || "Doctor"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <p className="text-sm text-gray-500">Status</p>
                    <span className={`inline-flex px-4 py-2 rounded-xl text-lg font-bold ${getStatusClass(token.status)}`}>
                      {token.status}
                    </span>
                  </div>
                  {(token.status === "Waiting" || token.status === "Called" || token.status === "Acknowledged" || token.status === "Ready") && (
                    <div className="text-center">
                      <p className="text-sm text-gray-500">Queue Position</p>
                      <p className="text-2xl font-bold text-blue-600">#{token.queue_position || "—"}</p>
                    </div>
                  )}
                  {(token.status === "Waiting" || token.status === "Called" || token.status === "Acknowledged" || token.status === "Ready") && token.estimated_wait_minutes && (
                    <div className="text-center">
                      <p className="text-sm text-gray-500">Est. Wait</p>
                      <p className="text-2xl font-bold text-green-600">{token.estimated_wait_minutes} min</p>
                    </div>
                  )}
                  {token.estimated_start_time && (
                    <div className="text-center">
                      <p className="text-sm text-gray-500">Est. Start</p>
                      <p className="text-lg font-bold text-blue-600">{formatTime(token.estimated_start_time)}</p>
                    </div>
                  )}
                </div>
              </div>
              {(token.status === "Waiting" || token.status === "Called" || token.status === "Acknowledged" || token.status === "Ready") && (
                <div className="mt-4 p-4 bg-blue-50 rounded-xl">
                  <p className="text-sm text-blue-700">
                    You are <strong>#{token.queue_position || "next"}</strong> in queue.
                    {token.estimated_wait_minutes && ` Estimated wait: ${token.estimated_wait_minutes} min.`}
                    Please wait for your token to be called.
                  </p>
                </div>
              )}
              {token.status === "Called" && (
                <div className="mt-4 p-4 bg-purple-50 rounded-xl">
                  <p className="text-sm text-purple-700 font-medium">
                    <BellIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> Your token has been called! Please proceed to the consultation area.
                  </p>
                </div>
              )}
              {token.status === "Ready" && (
                <div className="mt-4 p-4 bg-teal-50 rounded-xl">
                  <p className="text-sm text-teal-700 font-medium">
                    <CircleCheckIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> You are ready. The doctor will see you shortly.
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
          <div className="text-4xl mb-3"><TicketIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <h3 className="font-bold text-gray-800">No active queue tokens</h3>
          <p className="text-sm text-gray-500 mt-1">You don&apos;t have any pending consultations at the moment.</p>
        </div>
      )}
    </div>
  )
}

export default PatientQueue