import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { CalendarDays, ChevronRight, FileText, FlaskConical, History, Pill, ReceiptIndianRupee, Ticket } from "lucide-react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { Alert, Card, CardHeader, EmptyState, SkeletonRows, StatTile, StatusBadge } from "../../components/ui"
import { UPCOMING_STATUSES } from "../../config/appointmentStatus.js"

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const CURRENT_RX = ["Confirmed", "Pending"]

function PatientDashboard() {
  const { patient } = useAuth()
  const [stats, setStats] = useState(null)
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!patient?.id) return

    const fetchData = async () => {
      setLoading(true)
      // The server returns only this patient's own records.
      const [appts, rx, bills] = await Promise.allSettled([
        api.appointments.list(),
        api.clinical.prescriptions.list({ patientId: patient.id }),
        api.billing.invoices.list(),
      ])
      const mine = (r) => (r.status === "fulfilled" ? list(r.value) : [])
      const patientAppointments = mine(appts).filter((a) => String(a.patient) === String(patient.id))
      const prescriptions = mine(rx)
      const invoices = mine(bills).filter((b) => b.patient === undefined || String(b.patient) === String(patient.id))

      setAppointments(
        patientAppointments
          .filter((a) => UPCOMING_STATUSES.includes(a.status))
          .sort((a, b) => `${a.appointment_date} ${a.appointment_time}`.localeCompare(`${b.appointment_date} ${b.appointment_time}`))
          .slice(0, 5),
      )
      setStats({
        upcomingAppointments: appts.status === "fulfilled" ? patientAppointments.filter((a) => UPCOMING_STATUSES.includes(a.status)).length : null,
        pastAppointments: appts.status === "fulfilled" ? patientAppointments.filter((a) => a.status === "Completed").length : null,
        currentPrescriptions: rx.status === "fulfilled" ? prescriptions.filter((p) => CURRENT_RX.includes(p.status)).length : null,
        unpaidBills: bills.status === "fulfilled" ? invoices.filter((b) => b.status === "Unpaid" || b.status === "Partial").length : null,
      })
      const failed = [appts, rx, bills].find((r) => r.status === "rejected")
      setError(failed ? failed.reason?.message || "Some information could not be loaded." : null)
      setLoading(false)
    }

    fetchData()
  }, [patient?.id])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })
  }

  const firstName = (patient?.name || "").split(" ")[0]

  const links = [
    { to: "/patient/appointments", icon: CalendarDays, title: "Appointments", text: "Upcoming and past visits" },
    { to: "/patient/queue", icon: Ticket, title: "Queue / token", text: "Your place in today's queue" },
    { to: "/patient/prescriptions", icon: Pill, title: "Prescriptions", text: "Medicines your doctor prescribed" },
    { to: "/patient/lab-results", icon: FlaskConical, title: "Lab reports", text: "Results released by the lab" },
    { to: "/patient/bills", icon: ReceiptIndianRupee, title: "Bills", text: "Invoices and payments" },
    { to: "/patient/documents", icon: FileText, title: "Medical records", text: "Documents shared with you" },
  ]

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink-900 sm:text-2xl">{firstName ? `Hello, ${firstName}` : "Welcome"}</h1>
        <p className="mt-1 text-sm text-ink-500">Your appointments, medicines, reports and bills in one place.</p>
      </header>

      {error && <Alert tone="warning">{error}</Alert>}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile icon={CalendarDays} label="Upcoming appointments" value={loading ? null : stats?.upcomingAppointments} />
        <StatTile icon={History} tone="neutral" label="Past visits" value={loading ? null : stats?.pastAppointments} />
        <StatTile icon={Pill} tone="accent" label="Current prescriptions" value={loading ? null : stats?.currentPrescriptions} />
        <StatTile icon={ReceiptIndianRupee} tone={stats?.unpaidBills ? "warning" : "success"} label="Bills with balance due" value={loading ? null : stats?.unpaidBills} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <Card>
          <CardHeader
            title="Upcoming appointments"
            actions={<Link to="/patient/appointments" className="text-[13px] font-medium text-brand-700 hover:underline">View all</Link>}
          />
          {loading ? (
            <SkeletonRows rows={3} />
          ) : appointments.length > 0 ? (
            <ul className="divide-y divide-ink-100">
              {appointments.map((appt) => (
                <li key={appt.id} className="flex items-center gap-4 px-5 py-4">
                  <span className="flex h-11 w-11 shrink-0 flex-col items-center justify-center rounded-xl bg-brand-50 text-brand-800">
                    <span className="text-[10px] font-semibold uppercase leading-none">{appt.appointment_date ? new Date(appt.appointment_date).toLocaleDateString("en-GB", { month: "short" }) : ""}</span>
                    <span className="text-base font-semibold leading-tight tabular-nums">{appt.appointment_date ? new Date(appt.appointment_date).getDate() : "—"}</span>
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-ink-900">{appt.doctor_name || "Doctor"}</p>
                    <p className="text-[13px] text-ink-500 tabular-nums">
                      {formatDate(appt.appointment_date)}
                      {appt.appointment_time ? ` · ${String(appt.appointment_time).slice(0, 5)}` : ""}
                    </p>
                  </div>
                  <StatusBadge status={appt.status} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              compact
              icon={CalendarDays}
              title="No upcoming appointments"
              action={<Link to="/patient/appointments" className="text-sm font-medium text-brand-700 hover:underline">See your appointments</Link>}
            />
          )}
        </Card>

        <Card>
          <CardHeader title="Your records" />
          <ul className="divide-y divide-ink-100">
            {links.map(({ to, icon: Icon, title, text }) => (
              <li key={to}>
                <Link to={to} className="group flex items-center gap-3 px-5 py-3 hover:bg-ink-50">
                  <Icon size={18} className="text-brand-600" aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-ink-900">{title}</span>
                    <span className="block truncate text-xs text-ink-500">{text}</span>
                  </span>
                  <ChevronRight size={16} className="text-ink-300 group-hover:text-ink-500" aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}

export default PatientDashboard
