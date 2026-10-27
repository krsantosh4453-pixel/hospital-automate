import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { Ticket } from "lucide-react"
import { Alert, Card, EmptyState, SkeletonRows, StatusBadge } from "../../components/ui"

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
          (t) => String(t.patient) === String(patient.id) && !["Completed", "Cancelled", "No Show"].includes(t.status)
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

  const ACTIVE = ["Waiting", "Called", "Acknowledged", "Ready"]

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink-900 sm:text-2xl">Queue / token</h1>
        <p className="mt-1 text-sm text-ink-500">Your place in today&apos;s consultation queue. This page refreshes every 30 seconds.</p>
      </header>

      {error && <Alert tone="danger">{error}</Alert>}

      {loading ? (
        <Card><SkeletonRows rows={2} /></Card>
      ) : queueTokens.length === 0 ? (
        <Card>
          <EmptyState icon={Ticket} title="No active token" description="You don't have a consultation waiting at the moment." />
        </Card>
      ) : (
        <ul className="space-y-4">
          {queueTokens.map((token) => {
            const active = ACTIVE.includes(token.status)
            return (
              <li key={token.id}>
                <Card className="overflow-hidden">
                  <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center">
                    <div className="flex h-24 w-full shrink-0 flex-col items-center justify-center rounded-2xl bg-brand-900 text-white sm:w-32">
                      <span className="text-xs font-medium uppercase tracking-[0.1em] text-brand-200">Token</span>
                      <span className="text-4xl font-semibold tabular-nums">{token.token_number}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge status={token.status} />
                        <span className="text-[13px] text-ink-500">{formatDate(token.token_date)}{token.doctor_name ? ` · ${token.doctor_name}` : ""}</span>
                      </div>
                      {active && (
                        <dl className="mt-3 grid grid-cols-3 gap-3 text-sm">
                          <div>
                            <dt className="text-xs text-ink-500">Position</dt>
                            <dd className="text-lg font-semibold text-ink-900 tabular-nums">{token.queue_position ? `#${token.queue_position}` : "—"}</dd>
                          </div>
                          <div>
                            <dt className="text-xs text-ink-500">Estimated wait</dt>
                            <dd className="text-lg font-semibold text-ink-900 tabular-nums">{token.estimated_wait_minutes ? `${token.estimated_wait_minutes} min` : "—"}</dd>
                          </div>
                          <div>
                            <dt className="text-xs text-ink-500">Expected at</dt>
                            <dd className="text-lg font-semibold text-ink-900 tabular-nums">{token.estimated_start_time ? formatTime(token.estimated_start_time) : "—"}</dd>
                          </div>
                        </dl>
                      )}
                    </div>
                  </div>
                  <div aria-live="polite">
                    {token.status === "Called" && (
                      <Alert tone="info" className="rounded-none border-x-0 border-b-0" title="Your token has been called">
                        Please go to the consultation area now.
                      </Alert>
                    )}
                    {token.status === "Ready" && (
                      <Alert tone="success" className="rounded-none border-x-0 border-b-0">You are next. The doctor will see you shortly.</Alert>
                    )}
                    {(token.status === "Waiting" || token.status === "Acknowledged") && (
                      <p className="border-t border-line bg-ink-50 px-5 py-3 text-[13px] text-ink-600">
                        Estimates are approximate. Please stay nearby so you don&apos;t miss your call.
                      </p>
                    )}
                  </div>
                </Card>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export default PatientQueue
