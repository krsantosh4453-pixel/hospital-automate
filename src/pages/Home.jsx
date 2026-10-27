import { Link, useLocation } from "react-router-dom"
import { useState, useEffect, useCallback, useRef } from "react"
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
import { eligibleRolesFor, useRole } from "../assets/context/RoleContext.jsx"
import { roleHomeFor } from "../config/roleHomes.js"
import GuestHome from "./GuestHome.jsx"
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
/* ---------------- Staff dashboard ---------------- */
function Home() {
  const { isLoggedIn, patient, user } = useAuth()
  const { selectedHospital } = usePatient()
  const { canView, activeRoleName } = useRole()
  // null for Admin / Hospital Manager: they keep the full hospital dashboard.
  const roleHome = roleHomeFor(activeRoleName)
  // Set by ProtectedRoute when this role opened another department's page.
  const denied = useLocation().state?.denied

  const [dashboardStats, setDashboardStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Only the latest request may update the page: after sign-in the stored
  // hospital can be stale and its late 403 must not overwrite fresh figures.
  const latestRequest = useRef(0)

  const fetchStats = useCallback(async () => {
    // Visitors get no figures, so there is nothing to fetch for them.
    if (!isLoggedIn || !selectedHospital) return
    const requestId = ++latestRequest.current
    const isLatest = () => requestId === latestRequest.current
    setLoading(true)
    setError(null)
    try {
      const data = await api.home.stats(selectedHospital.id)
      if (isLatest()) setDashboardStats(data)
    } catch (err) {
      if (isLatest()) setError(err.message)
    } finally {
      if (isLatest()) setLoading(false)
    }
  }, [isLoggedIn, selectedHospital])

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

  const fmt = (n) => (n === null ? null : num.format(n))
  const tiles = {
    patients: { icon: UsersRound, label: "Patients registered today", value: fmt(v(stats.patients, "today")),
      hint: dashboardStats ? `${num.format(stats.patients?.total || 0)} registered in total` : undefined },
    appointments: { icon: CalendarDays, tone: "accent", label: "Appointments today", value: fmt(v(stats.appointments, "today")),
      hint: dashboardStats ? `${num.format(stats.appointments?.pending || 0)} pending` : undefined },
    queue: { icon: ListOrdered, tone: "warning", label: "Waiting in queue", value: fmt(v(stats.queue, "waiting")),
      hint: dashboardStats && stats.queue?.current_token ? `Now serving token ${stats.queue.current_token}` : "No token being served" },
    beds: { icon: BedDouble, tone: "success", label: "Beds available", value: fmt(availableBeds),
      hint: dashboardStats ? `${num.format(occupiedBeds || 0)} occupied of ${num.format(totalBeds || 0)}` : undefined },
    admissions: { icon: BedDouble, label: "Current admissions", value: fmt(v(stats.admissions, "current")) },
    labPending: { icon: FlaskConical, tone: "warning", label: "Lab tests pending", value: fmt(v(stats.laboratory, "pending")) },
    labUrgent: { icon: FlaskConical, tone: "warning", label: "Urgent lab tests", value: fmt(v(stats.laboratory, "urgent")) },
    labCompleted: { icon: ClipboardCheck, tone: "success", label: "Lab tests completed", value: fmt(v(stats.laboratory, "completed")) },
    billingPending: { icon: ReceiptIndianRupee, tone: "warning", label: "Invoices awaiting payment", value: fmt(v(stats.billing, "pending")) },
    revenueToday: { icon: ReceiptIndianRupee, tone: "success", label: "Collected today",
      value: dashboardStats ? inr.format(Number(stats.billing?.today_revenue || 0)) : null },
  }
  const tileKeys = roleHome ? roleHome.tiles : ["patients", "appointments", "queue", "beds"]
  const showFlow = !roleHome || roleHome.showFlow
  const showRecentPatients = !roleHome || roleHome.showRecentPatients

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

  const allQuickActions = [
    { to: "/patients", icon: UserPlus, label: "Register patient", module: "Patients" },
    { to: "/appointments", icon: CalendarPlus, label: "New appointment", module: "Appointments" },
    { to: "/queue", icon: ListOrdered, label: "Open queue", module: "Queue" },
    { to: "/consultation", icon: Stethoscope, label: "Start consultation", module: "Doctors" },
    { to: "/pharmacy", icon: Pill, label: "Dispense medicines", module: "Pharmacy" },
    { to: "/laboratory", icon: FlaskConical, label: "Lab worklist", module: "Laboratory" },
    { to: "/billing", icon: ReceiptIndianRupee, label: "Create invoice", module: "Billing" },
    { to: "/patients", icon: Search, label: "Find a patient", module: "Patients" },
  ]
  const quickActions = (roleHome ? roleHome.actions : allQuickActions).filter((a) => canView(a.module))

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
            {roleHome ? `${roleHome.title} · ` : ""}{today} · <span className="font-medium text-ink-700">{selectedHospital.name}</span>
            {activeRoleName ? ` · ${activeRoleName}` : ""}
          </>
        }
        actions={
          <>
            {!roleHome && canView("Appointments") && (
              <Link
                to="/appointments"
                className="inline-flex h-10 items-center gap-2 rounded-lg border border-line-strong bg-white px-4 text-sm font-medium text-ink-800 shadow-sm hover:bg-ink-50"
              >
                <CalendarPlus size={17} aria-hidden="true" /> New appointment
              </Link>
            )}
            {!roleHome && canView("Patients") && (
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

      {denied && (
        <Alert tone="warning" title="You are not eligible for that page">
          {denied} work is only for {eligibleRolesFor(denied).join(", ")}. You are signed in as {activeRoleName}.
        </Alert>
      )}

      {tileKeys.length > 0 && (
      <section aria-label="Today at a glance" className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {loading && !dashboardStats ? (
          tileKeys.map((key) => <div key={key} className="skeleton h-[88px] rounded-2xl" />)
        ) : (
          <>
            {tileKeys.map((key) => (
              <StatTile key={key} {...tiles[key]} />
            ))}
          </>
        )}
      </section>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          {showFlow && (
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
          )}

          {showRecentPatients && (
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
          )}
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

          {!roleHome && (canView("Billing") || canView("IPD")) && dashboardStats && (
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
