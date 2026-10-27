import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  Building,
  ChevronRight,
  ClipboardList,
  History,
  Hospital,
  KeyRound,
  RefreshCw,
  ShieldCheck,
  Stethoscope,
  UserCheck,
  UserCog,
  Users,
  UsersRound,
} from "lucide-react"
import { usePatient } from "../../assets/context/PatientContext.jsx"
import { useRole } from "../../assets/context/RoleContext.jsx"
import api from "../../services/api.js"
import { Alert, Button, Card, CardHeader, EmptyState, PageHeader, StatTile } from "../../components/ui"

const list = (data) => (Array.isArray(data) ? data : data?.results || [])

function timeAgo(value) {
  const then = new Date(value).getTime()
  if (!Number.isFinite(then)) return ""
  const mins = Math.round((Date.now() - then) / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs} h ago`
  return new Date(value).toLocaleDateString("en-IN")
}

// "ipd.discharge_summary.finalize" -> "Discharge summary finalize"
const describeAction = (action) => {
  const parts = String(action || "").split(".")
  const text = (parts.length > 1 ? parts.slice(1) : parts).join(" ").replace(/_/g, " ")
  return text.charAt(0).toUpperCase() + text.slice(1)
}

const MODULES = [
  { to: "/admin/setup", icon: Hospital, title: "Hospital setup", text: "New hospital, wards, beds and staff", module: "Users" },
  { to: "/admin/users", icon: Users, title: "Users", text: "Invite staff and set roles", module: "Users" },
  { to: "/admin/roles", icon: ShieldCheck, title: "Roles", text: "What each role is for", module: "Roles" },
  { to: "/admin/permissions", icon: KeyRound, title: "Permissions", text: "Module access per role", module: "Permissions" },
  { to: "/admin/departments", icon: ClipboardList, title: "Departments", text: "Clinics and their heads", module: "Departments" },
  { to: "/admin/hospitals", icon: Building, title: "Hospitals", text: "Hospital details", module: "Hospitals" },
  { to: "/doctors", icon: Stethoscope, title: "Doctors", text: "Directory and availability", module: "Doctors" },
  { to: "/nurses", icon: UserCog, title: "Nursing", text: "Nurses and ward work", module: "Nurses" },
  { to: "/compounter", icon: UserCog, title: "Compounders", text: "Compounder workspace", module: "Compounders" },
]

function AdminDashboard() {
  const { selectedHospital } = usePatient()
  const { canView } = useRole()
  const [data, setData] = useState(null)
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!selectedHospital) {
      setLoading(false)
      return
    }
    setLoading(true)
    const [users, departments, stats, audit] = await Promise.allSettled([
      api.users.list(),
      api.departments.list(selectedHospital.id),
      api.home.stats(selectedHospital.id),
      api.audit.logs(selectedHospital.id),
    ])
    const value = (r) => (r.status === "fulfilled" ? r.value : null)
    setData({
      staff: value(users)?.staff || [],
      departments: list(value(departments)),
      stats: value(stats)?.statistics || null,
      audit: list(value(audit)).slice(0, 10),
      auditAvailable: audit.status === "fulfilled",
    })
    setErrors(
      [users, departments, stats]
        .filter((r) => r.status === "rejected")
        .map((r) => r.reason?.message)
        .filter(Boolean),
    )
    setLoading(false)
  }, [selectedHospital])

  useEffect(() => {
    load()
  }, [load])

  const activeStaff = data ? data.staff.filter((s) => Boolean(s.membership?.is_active)).length : null
  const invitePending = data ? data.staff.filter((s) => s.invite_pending).length : null
  const num = (v) => (v === null || v === undefined ? null : Number(v).toLocaleString("en-IN"))

  return (
    <div className="space-y-5">
      <PageHeader
        title="Administration"
        description={selectedHospital ? `Staff, structure and activity for ${selectedHospital.name}.` : "Select a hospital to administer."}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Administration" }]}
        actions={selectedHospital && <Button variant="secondary" icon={RefreshCw} onClick={load} disabled={loading}>Refresh</Button>}
      />

      {!selectedHospital ? (
        <Card><EmptyState icon={Hospital} title="Select a hospital" description="Choose a hospital in the header." /></Card>
      ) : (
        <>
          {errors.length > 0 && <Alert tone="warning" title="Some figures could not be loaded">{[...new Set(errors)].join(" ")}</Alert>}

          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <StatTile icon={UsersRound} label="Active staff" value={loading ? null : num(activeStaff)} hint={data ? `${data.staff.length} in total` : undefined} />
            <StatTile icon={UserCheck} tone="warning" label="Invite pending" value={loading ? null : num(invitePending)} hint="Invited, password not set yet" />
            <StatTile icon={ClipboardList} tone="accent" label="Departments" value={loading ? null : num(data?.departments.length)} />
            <StatTile icon={Stethoscope} tone="success" label="Doctors" value={loading ? null : num(data?.stats?.doctors?.total)} hint={data?.stats ? `${num(data.stats.patients?.total)} patients registered` : undefined} />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_26rem]">
            <Card>
              <CardHeader title="Administration areas" />
              <div className="grid grid-cols-1 gap-px bg-line sm:grid-cols-2">
                {MODULES.filter((m) => canView(m.module)).map(({ to, icon: Icon, title, text }) => (
                  <Link key={to} to={to} className="group flex items-center gap-3 bg-white px-5 py-4 hover:bg-ink-50">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                      <Icon size={18} aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-ink-900">{title}</span>
                      <span className="block truncate text-[13px] text-ink-500">{text}</span>
                    </span>
                    <ChevronRight size={16} className="text-ink-300 group-hover:text-ink-500" aria-hidden="true" />
                  </Link>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader icon={History} title="Recent activity" description="From the audit trail" />
              {loading ? (
                <p className="px-5 py-6 text-sm text-ink-500">Loading…</p>
              ) : !data?.auditAvailable ? (
                <EmptyState compact icon={History} title="Audit trail not available" description="Only hospital administrators can read the audit trail." />
              ) : data.audit.length === 0 ? (
                <EmptyState compact icon={History} title="No recorded activity yet" />
              ) : (
                <ol className="divide-y divide-ink-100">
                  {data.audit.map((entry) => (
                    <li key={entry.id} className="px-5 py-3">
                      <p className="text-sm font-medium text-ink-900">{describeAction(entry.action)}</p>
                      <p className="text-xs text-ink-500">
                        {entry.model_name}
                        {entry.object_id ? ` #${entry.object_id}` : ""}
                        {entry.user ? ` · user ${entry.user}` : ""} · {timeAgo(entry.created_at)}
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

export default AdminDashboard
