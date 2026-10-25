import { Link } from "react-router-dom"
import { useState, useEffect, useCallback } from "react"
import {
  BedDouble,
  CalendarCheck,
  CalendarDays,
  CalendarPlus,
  ChevronRight,
  ClipboardCheck,
  FlaskConical,
  Hospital,
  ListOrdered,
  LogIn,
  Pill,
  ReceiptIndianRupee,
  Search,
  ShieldCheck,
  Siren,
  Stethoscope,
  UserPlus,
  UsersRound,
} from "lucide-react"

import { usePatient } from "../assets/context/PatientContext.jsx"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import api from "../services/api.js"
import {
  Alert,
  Avatar,
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  StatTile,
} from "../components/ui"

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })
const num = new Intl.NumberFormat("en-IN")

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return "Good morning"
  if (h < 17) return "Good afternoon"
  return "Good evening"
}

/* One horizontal bar split into labelled parts, from real counts only. */
function SplitBar({ parts, total, label }) {
  const sum = total ?? parts.reduce((s, p) => s + (p.value || 0), 0)
  return (
    <div>
      <div className="flex h-2.5 overflow-hidden rounded-full bg-ink-100" role="img" aria-label={label}>
        {sum > 0 &&
          parts.map((p) =>
            p.value > 0 ? <span key={p.label} className={p.cls} style={{ width: `${(p.value / sum) * 100}%` }} /> : null,
          )}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5">
        {parts.map((p) => (
          <li key={p.label} className="flex items-center gap-2 text-[13px] text-ink-600">
            <span className={`h-2 w-2 rounded-full ${p.cls}`} aria-hidden="true" />
            {p.label}
            <span className="font-semibold text-ink-900 tabular-nums">{num.format(p.value || 0)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function FlowRow({ icon: Icon, title, to, children }) {
  return (
    <div className="px-5 py-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="flex items-center gap-2 text-sm font-semibold text-ink-800">
          <Icon size={16} className="text-ink-400" aria-hidden="true" />
          {title}
        </p>
        {to && (
          <Link to={to} className="inline-flex items-center gap-0.5 text-[13px] font-medium text-brand-700 hover:underline">
            Open <ChevronRight size={14} aria-hidden="true" />
          </Link>
        )}
      </div>
      {children}
    </div>
  )
}

/* ---------------- Guest landing (development builds only) ---------------- */
function GuestHome() {
  const services = [
    { to: "/appointments", icon: CalendarDays, title: "Book an appointment", text: "Choose a hospital, doctor, date and available slot." },
    { to: "/doctors", icon: Stethoscope, title: "Find a doctor", text: "Browse doctors by department." },
    { to: "/laboratory", icon: FlaskConical, title: "Laboratory", text: "See the tests and services offered." },
    { to: "/pharmacy", icon: Pill, title: "Pharmacy", text: "Medicines and pharmacy services." },
  ]
  const steps = [
    { icon: Hospital, title: "Select hospital", text: "Pick where you want to be seen." },
    { icon: Stethoscope, title: "Select doctor", text: "Choose a department and doctor." },
    { icon: CalendarCheck, title: "Choose a slot", text: "Pick a date and an available time." },
    { icon: ShieldCheck, title: "Confirm", text: "Sign in only when you confirm the booking." },
  ]

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-2xl bg-brand-900 px-6 py-10 text-white sm:px-10 sm:py-14">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-brand-200">Hospital services</p>
        <h1 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          Your care, organised in one place
        </h1>
        <p className="mt-4 max-w-xl text-[15px] leading-7 text-brand-100/90">
          Find doctors, book appointments and keep track of your visits, prescriptions and reports.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link
            to="/appointments"
            className="inline-flex h-11 items-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-brand-800 hover:bg-brand-50"
          >
            <CalendarPlus size={17} aria-hidden="true" /> Book appointment
          </Link>
          <Link
            to="/patient-login"
            className="inline-flex h-11 items-center gap-2 rounded-lg border border-white/30 px-5 text-sm font-semibold text-white hover:bg-white/10"
          >
            <LogIn size={17} aria-hidden="true" /> Sign in
          </Link>
        </div>
      </section>

      <section aria-labelledby="guest-services">
        <h2 id="guest-services" className="mb-4 text-base font-semibold text-ink-900">
          Explore without signing in
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {services.map(({ to, icon: Icon, title, text }) => (
            <Link key={title} to={to} className="group rounded-2xl border border-line bg-white p-5 transition-colors hover:border-brand-300">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                <Icon size={20} aria-hidden="true" />
              </span>
              <p className="mt-4 font-semibold text-ink-900 group-hover:text-brand-800">{title}</p>
              <p className="mt-1 text-sm text-ink-500">{text}</p>
            </Link>
          ))}
        </div>
      </section>

      <Card>
        <CardHeader title="How booking works" description="You can explore the process before signing in." />
        <ol className="grid grid-cols-1 gap-6 px-5 py-6 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map(({ icon: Icon, title, text }, i) => (
            <li key={title} className="flex gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                {i + 1}
              </span>
              <div>
                <p className="flex items-center gap-1.5 font-medium text-ink-900">
                  <Icon size={15} className="text-ink-400" aria-hidden="true" /> {title}
                </p>
                <p className="mt-0.5 text-sm text-ink-500">{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  )
}

/* ---------------- Staff dashboard ---------------- */
function Home() {
  const { isLoggedIn, patient, user } = useAuth()
  const { selectedHospital } = usePatient()
  const { canView, activeRoleName } = useRole()

  const [dashboardStats, setDashboardStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStats = useCallback(async () => {
    if (!selectedHospital) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.home.stats(selectedHospital.id)
      setDashboardStats(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [selectedHospital])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  if (!isLoggedIn) return <GuestHome />

  if (!selectedHospital) {
    return (
      <Card className="mx-auto mt-10 max-w-lg">
        <EmptyState
          icon={Hospital}
          title={`Welcome${patient?.name ? `, ${patient.name}` : ""}`}
          description="Select a hospital from the header to see its dashboard."
          action={
            <Link
              to="/hospital-selection"
              className="inline-flex h-10 items-center rounded-lg bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700"
            >
              Select hospital
            </Link>
          }
        />
      </Card>
    )
  }

  // All figures come from /api/home/stats/; nothing is estimated here.
  const stats = dashboardStats?.statistics || {}
  const v = (obj, key) => (dashboardStats ? obj?.[key] ?? 0 : null)
  const totalBeds = v(stats.beds, "total")
  const availableBeds = v(stats.beds, "available")
  const occupiedBeds = dashboardStats ? stats.beds?.occupied ?? Math.max((totalBeds || 0) - (availableBeds || 0), 0) : null
  const recentPatients = dashboardStats?.recent_patients || []

  const firstName = user?.first_name || user?.user?.first_name || user?.username || user?.user?.username
  const today = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })

  const attention = dashboardStats
    ? [
        canView("Emergency") && stats.emergency?.active > 0 && {
          tone: "danger", icon: Siren, to: "/emergency",
          text: `${stats.emergency.active} active emergency case${stats.emergency.active === 1 ? "" : "s"}`,
        },
        canView("Laboratory") && stats.laboratory?.urgent > 0 && {
          tone: "danger", icon: FlaskConical, to: "/laboratory",
          text: `${stats.laboratory.urgent} urgent lab test${stats.laboratory.urgent === 1 ? "" : "s"}`,
        },
        canView("Queue") && stats.queue?.waiting > 0 && {
          tone: "warning", icon: ListOrdered, to: "/queue",
          text: `${stats.queue.waiting} patient${stats.queue.waiting === 1 ? "" : "s"} waiting in the queue`,
        },
        canView("Laboratory") && stats.laboratory?.pending > 0 && {
          tone: "warning", icon: ClipboardCheck, to: "/laboratory",
          text: `${stats.laboratory.pending} lab test${stats.laboratory.pending === 1 ? "" : "s"} pending`,
        },
        canView("Billing") && stats.billing?.pending > 0 && {
          tone: "neutral", icon: ReceiptIndianRupee, to: "/billing",
          text: `${stats.billing.pending} invoice${stats.billing.pending === 1 ? "" : "s"} awaiting payment`,
        },
        canView("IPD") && totalBeds > 0 && availableBeds === 0 && {
          tone: "warning", icon: BedDouble, to: "/ipd", text: "No beds available",
        },
      ].filter(Boolean)
    : []

  const quickActions = [
    { to: "/patients", icon: UserPlus, label: "Register patient", module: "Patients" },
    { to: "/appointments", icon: CalendarPlus, label: "New appointment", module: "Appointments" },
    { to: "/queue", icon: ListOrdered, label: "Open queue", module: "Queue" },
    { to: "/consultation", icon: Stethoscope, label: "Start consultation", module: "Doctors" },
    { to: "/pharmacy", icon: Pill, label: "Dispense medicines", module: "Pharmacy" },
    { to: "/laboratory", icon: FlaskConical, label: "Lab worklist", module: "Laboratory" },
    { to: "/billing", icon: ReceiptIndianRupee, label: "Create invoice", module: "Billing" },
    { to: "/patients", icon: Search, label: "Find a patient", module: "Patients" },
  ].filter((a) => canView(a.module))

  const toneCls = {
    danger: "bg-red-50 text-red-700",
    warning: "bg-amber-50 text-amber-700",
    neutral: "bg-ink-100 text-ink-600",
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${greeting()}${firstName ? `, ${firstName}` : ""}`}
        description={
          <>
            {today} · <span className="font-medium text-ink-700">{selectedHospital.name}</span>
            {activeRoleName ? ` · ${activeRoleName}` : ""}
          </>
        }
        actions={
          <>
            {canView("Appointments") && (
              <Link
                to="/appointments"
                className="inline-flex h-10 items-center gap-2 rounded-lg border border-line-strong bg-white px-4 text-sm font-medium text-ink-800 shadow-sm hover:bg-ink-50"
              >
                <CalendarPlus size={17} aria-hidden="true" /> New appointment
              </Link>
            )}
            {canView("Patients") && (
              <Link
                to="/patients"
                className="inline-flex h-10 items-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-medium text-white shadow-sm hover:bg-brand-700"
              >
                <UserPlus size={17} aria-hidden="true" /> Register patient
              </Link>
            )}
          </>
        }
      />

      {error && (
        <Alert
          tone="danger"
          title="Dashboard figures could not be loaded"
          action={<Button size="sm" variant="secondary" onClick={fetchStats}>Retry</Button>}
        >
          {error}
        </Alert>
      )}

      <section aria-label="Today at a glance" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading && !dashboardStats ? (
          Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton h-[88px] rounded-2xl" />)
        ) : (
          <>
            <StatTile
              icon={UsersRound}
              label="Patients registered today"
              value={v(stats.patients, "today") === null ? null : num.format(v(stats.patients, "today"))}
              hint={dashboardStats ? `${num.format(stats.patients?.total || 0)} registered in total` : undefined}
            />
            <StatTile
              icon={CalendarDays}
              tone="accent"
              label="Appointments today"
              value={v(stats.appointments, "today") === null ? null : num.format(v(stats.appointments, "today"))}
              hint={dashboardStats ? `${num.format(stats.appointments?.pending || 0)} pending` : undefined}
            />
            <StatTile
              icon={ListOrdered}
              tone="warning"
              label="Waiting in queue"
              value={v(stats.queue, "waiting") === null ? null : num.format(v(stats.queue, "waiting"))}
              hint={dashboardStats && stats.queue?.current_token ? `Now serving token ${stats.queue.current_token}` : "No token being served"}
            />
            <StatTile
              icon={BedDouble}
              tone="success"
              label="Beds available"
              value={availableBeds === null ? null : num.format(availableBeds)}
              hint={dashboardStats ? `${num.format(occupiedBeds || 0)} occupied of ${num.format(totalBeds || 0)}` : undefined}
            />
          </>
        )}
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <Card>
            <CardHeader title="Today's patient flow" description="Live counts for the selected hospital." />
            <div className="divide-y divide-line">
              <FlowRow icon={ListOrdered} title="OPD queue" to={canView("Queue") ? "/queue" : null}>
                <SplitBar
                  label="Queue status"
                  parts={[
                    { label: "Waiting", value: stats.queue?.waiting || 0, cls: "bg-amber-500" },
                    { label: "In consultation", value: stats.queue?.in_consultation || 0, cls: "bg-brand-500" },
                    { label: "Completed", value: stats.queue?.completed || 0, cls: "bg-green-500" },
                  ]}
                />
              </FlowRow>
              <FlowRow icon={CalendarDays} title="Appointments" to={canView("Appointments") ? "/appointments" : null}>
                <SplitBar
                  label="Appointment status"
                  parts={[
                    { label: "Pending", value: stats.appointments?.pending || 0, cls: "bg-amber-500" },
                    { label: "Completed", value: stats.appointments?.completed || 0, cls: "bg-green-500" },
                  ]}
                />
              </FlowRow>
              {canView("Laboratory") && (
                <FlowRow icon={FlaskConical} title="Laboratory" to="/laboratory">
                  <SplitBar
                    label="Lab test status"
                    parts={[
                      { label: "Pending", value: stats.laboratory?.pending || 0, cls: "bg-amber-500" },
                      { label: "Completed", value: stats.laboratory?.completed || 0, cls: "bg-green-500" },
                      { label: "Urgent", value: stats.laboratory?.urgent || 0, cls: "bg-red-500" },
                    ]}
                    total={(stats.laboratory?.pending || 0) + (stats.laboratory?.completed || 0) + (stats.laboratory?.urgent || 0)}
                  />
                </FlowRow>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Recently registered patients"
              actions={
                canView("Patients") && (
                  <Link to="/patients" className="text-[13px] font-medium text-brand-700 hover:underline">
                    View all
                  </Link>
                )
              }
            />
            {recentPatients.length > 0 ? (
              <ul className="divide-y divide-ink-100">
                {recentPatients.slice(0, 6).map((p) => (
                  <li key={p.id} className="flex items-center gap-3 px-5 py-3">
                    <Avatar name={p.name} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink-900">{p.name}</p>
                      <p className="text-xs text-ink-500 tabular-nums">
                        {p.uhid || p.patient_id || `ID ${p.id}`}
                        {p.gender ? ` · ${p.gender}` : ""}
                        {p.age ? ` · ${p.age} y` : ""}
                      </p>
                    </div>
                    {p.created_at && (
                      <span className="text-xs text-ink-400 tabular-nums">{new Date(p.created_at).toLocaleDateString("en-IN")}</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState compact icon={UsersRound} title={loading ? "Loading…" : "No patients registered yet"} />
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Needs attention" />
            {attention.length > 0 ? (
              <ul className="divide-y divide-ink-100">
                {attention.map((a) => (
                  <li key={a.text}>
                    <Link to={a.to} className="flex items-center gap-3 px-5 py-3 hover:bg-ink-50">
                      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${toneCls[a.tone]}`}>
                        <a.icon size={16} aria-hidden="true" />
                      </span>
                      <span className="flex-1 text-sm text-ink-800">{a.text}</span>
                      <ChevronRight size={16} className="text-ink-300" aria-hidden="true" />
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState
                compact
                icon={ShieldCheck}
                title={loading && !dashboardStats ? "Checking…" : "Nothing needs attention"}
                description={dashboardStats ? "No waiting patients, urgent tests or active emergencies right now." : undefined}
              />
            )}
          </Card>

          {quickActions.length > 0 && (
            <Card>
              <CardHeader title="Quick actions" />
              <div className="grid grid-cols-2 gap-2 p-3">
                {quickActions.map(({ to, icon: Icon, label }) => (
                  <Link
                    key={label}
                    to={to}
                    className="flex flex-col gap-2 rounded-xl border border-transparent p-3 text-[13px] font-medium text-ink-800 hover:border-line hover:bg-ink-50"
                  >
                    <Icon size={18} className="text-brand-600" aria-hidden="true" />
                    {label}
                  </Link>
                ))}
              </div>
            </Card>
          )}

          {(canView("Billing") || canView("IPD")) && dashboardStats && (
            <Card>
              <CardHeader title="Operations" />
              <dl className="divide-y divide-ink-100 text-sm">
                {canView("IPD") && (
                  <div className="flex items-center justify-between px-5 py-3">
                    <dt className="text-ink-600">Current admissions</dt>
                    <dd className="font-semibold text-ink-900 tabular-nums">{num.format(stats.admissions?.current || 0)}</dd>
                  </div>
                )}
                {canView("Emergency") && (
                  <div className="flex items-center justify-between px-5 py-3">
                    <dt className="text-ink-600">Emergency visits today</dt>
                    <dd className="font-semibold text-ink-900 tabular-nums">{num.format(stats.emergency?.today || 0)}</dd>
                  </div>
                )}
                {canView("Billing") && (
                  <>
                    <div className="flex items-center justify-between px-5 py-3">
                      <dt className="text-ink-600">Collected today</dt>
                      <dd className="font-semibold text-ink-900 tabular-nums">{inr.format(Number(stats.billing?.today_revenue || 0))}</dd>
                    </div>
                    <div className="flex items-center justify-between px-5 py-3">
                      <dt className="text-ink-600">Invoices paid / total</dt>
                      <dd className="font-semibold text-ink-900 tabular-nums">
                        {num.format(stats.billing?.paid || 0)} / {num.format(stats.billing?.total_invoices || 0)}
                      </dd>
                    </div>
                  </>
                )}
              </dl>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

export default Home
