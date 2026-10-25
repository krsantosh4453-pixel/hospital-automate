import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { CalendarDays } from "lucide-react"
import { Alert, Card, EmptyState, SegmentedControl, SkeletonRows, StatusBadge } from "../../components/ui"

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
    if (filter === "upcoming") return ["Scheduled", "Confirmed", "Waiting"].includes(appt.status)
    if (filter === "past") return appt.status === "Completed"
    if (filter === "cancelled") return appt.status === "Cancelled"
    return true
  })

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink-900 sm:text-2xl">Appointments</h1>
          <p className="mt-1 text-sm text-ink-500">Your bookings at the hospital.</p>
        </div>
        <SegmentedControl
          label="Filter appointments"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: "All" },
            { value: "upcoming", label: "Upcoming" },
            { value: "past", label: "Past" },
            { value: "cancelled", label: "Cancelled" },
          ]}
        />
      </header>

      {error && <Alert tone="danger">{error}</Alert>}

      {loading ? (
        <Card><SkeletonRows rows={4} /></Card>
      ) : filteredAppointments.length === 0 ? (
        <Card>
          <EmptyState
            icon={CalendarDays}
            title={appointments.length ? "No appointments match this filter" : "No appointments yet"}
            description={appointments.length ? undefined : "Appointments booked at the hospital will appear here."}
          />
        </Card>
      ) : (
        <Card>
          <ul className="divide-y divide-ink-100">
            {filteredAppointments.map((appt) => (
              <li key={appt.id} className="flex items-center gap-4 px-5 py-4">
                <span className="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-xl bg-brand-50 text-brand-800">
                  <span className="text-[10px] font-semibold uppercase leading-none">
                    {appt.appointment_date ? new Date(appt.appointment_date).toLocaleDateString("en-GB", { month: "short" }) : ""}
                  </span>
                  <span className="text-lg font-semibold leading-tight tabular-nums">
                    {appt.appointment_date ? new Date(appt.appointment_date).getDate() : "—"}
                  </span>
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink-900">{appt.doctor_name || "Doctor"}</p>
                  <p className="text-[13px] text-ink-500 tabular-nums">
                    {formatDate(appt.appointment_date)}
                    {appt.appointment_time ? ` · ${String(appt.appointment_time).slice(0, 5)}` : ""}
                  </p>
                  {appt.reason && <p className="mt-0.5 truncate text-[13px] text-ink-600">{appt.reason}</p>}
                </div>
                <StatusBadge status={appt.status} />
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}

export default PatientAppointments
