import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { CalendarDaysIcon, CreditCardIcon, FlaskConicalIcon, HospitalIcon, PillIcon, TriangleAlertIcon } from "lucide-react"

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
      try {
        const [apptsData] = await Promise.all([
          api.appointments.list().catch(() => ({ results: [] })),
        ])

        const allAppointments = apptsData?.results || apptsData || []
        const patientAppointments = allAppointments.filter(
          (a) => String(a.patient) === String(patient.id)
        )

        setAppointments(patientAppointments.slice(0, 5))
        setStats({
          upcomingAppointments: patientAppointments.filter(a => a.status === "Scheduled" || a.status === "Confirmed").length,
          pastAppointments: patientAppointments.filter(a => a.status === "Completed").length,
          pendingPrescriptions: 0,
          unpaidBills: 0,
        })
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [patient?.id])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Welcome back, {patient?.name || "Patient"}!</h1>
        <p className="text-gray-500 mt-1">Here&apos;s an overview of your health information.</p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
          <TriangleAlertIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Upcoming Appointments" value={stats?.upcomingAppointments || 0} icon={<CalendarDaysIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />} color="bg-blue-100" />
        <StatCard title="Past Visits" value={stats?.pastAppointments || 0} icon={<HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />} color="bg-green-100" />
        <StatCard title="Active Prescriptions" value={stats?.pendingPrescriptions || 0} icon={<PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />} color="bg-purple-100" />
        <StatCard title="Unpaid Bills" value={stats?.unpaidBills || 0} icon={<CreditCardIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />} color="bg-orange-100" />
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Upcoming Appointments</h2>
          <a href="/patient/appointments" className="text-sm text-blue-600 hover:text-blue-700 font-medium">View All →</a>
        </div>
        <div className="divide-y divide-gray-100">
          {appointments.length > 0 ? (
            appointments.map((appt) => (
              <div key={appt.id} className="p-5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-xl"><CalendarDaysIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
                  <div>
                    <p className="font-medium text-gray-800">{appt.doctor_name || "Doctor"}</p>
                    <p className="text-sm text-gray-500">{formatDate(appt.appointment_date)} at {appt.appointment_time}</p>
                  </div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  appt.status === "Scheduled" ? "bg-blue-100 text-blue-700" :
                  appt.status === "Confirmed" ? "bg-green-100 text-green-700" :
                  appt.status === "Completed" ? "bg-gray-100 text-gray-700" :
                  "bg-red-100 text-red-700"
                }`}>
                  {appt.status}
                </span>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-gray-500">
              <p className="text-lg mb-2">No upcoming appointments</p>
              <a href="/patient/appointments" className="text-blue-600 hover:text-blue-700 font-medium">Book an appointment →</a>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <QuickActionCard
          icon={<CalendarDaysIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          title="Book Appointment"
          description="Schedule a new appointment with your doctor"
          href="/patient/appointments"
        />
        <QuickActionCard
          icon={<PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          title="View Prescriptions"
          description="Check your current and past prescriptions"
          href="/patient/prescriptions"
        />
        <QuickActionCard
          icon={<FlaskConicalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          title="Lab Results"
          description="View your laboratory test results"
          href="/patient/lab-results"
        />
        <QuickActionCard
          icon={<CreditCardIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          title="Pay Bills"
          description="View and pay your medical bills online"
          href="/patient/bills"
        />
      </div>
    </div>
  )
}

function StatCard({ title, value, icon, color }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <h3 className="text-3xl font-bold text-gray-800 mt-1">{value}</h3>
        </div>
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${color}`}>{icon}</div>
      </div>
    </div>
  )
}

function QuickActionCard({ icon, title, description, href }) {
  return (
    <a href={href} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 hover:border-blue-200 hover:shadow-md transition flex items-center gap-4">
      <div className="w-14 h-14 bg-gray-100 rounded-xl flex items-center justify-center text-2xl">{icon}</div>
      <div>
        <h3 className="font-semibold text-gray-800">{title}</h3>
        <p className="text-sm text-gray-500 mt-1">{description}</p>
      </div>
    </a>
  )
}

export default PatientDashboard