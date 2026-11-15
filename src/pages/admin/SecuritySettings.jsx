import { useEffect, useState } from "react"
import { CircleAlert, CircleCheck, Info, ShieldCheck } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Card, EmptyState, PageHeader, SkeletonRows, TableWrap } from "../../components/ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// Security page (decision 3, 2026-11-09). A hospital Admin sees their own
// hospital's overview, read only. The server-wide configuration (A14) is
// shown to platform staff only; for everyone else that block stays hidden.

const formatValue = (value) => (typeof value === "boolean" ? (value ? "On" : "Off") : String(value))
const formatTime = (value) => (value ? new Date(value).toLocaleString() : "—")

function Verdict({ secure }) {
  const { t } = useLanguage()
  if (secure === true) return <span className="inline-flex items-center gap-1 text-green-700"><CircleCheck size={15} aria-hidden="true" />{t("Recommended")}</span>
  if (secure === false) return <span className="inline-flex items-center gap-1 text-amber-700"><CircleAlert size={15} aria-hidden="true" />{t("Not for production")}</span>
  return <span className="inline-flex items-center gap-1 text-ink-500"><Info size={15} aria-hidden="true" />{t("Information")}</span>
}

function Section({ title, empty, rows, columns, render }) {
  const { t } = useLanguage()
  return (
    <Card className="mb-4">
      <h2 className="px-4 pt-4 text-base font-semibold text-ink-900">{t(title)}</h2>
      {rows.length === 0 ? (
        <p className="px-4 py-4 text-sm text-ink-500">{t(empty)}</p>
      ) : (
        <TableWrap>
          <table className="w-full text-sm">
            <thead>
              <tr>{columns.map((column) => <th key={column} scope="col">{t(column)}</th>)}</tr>
            </thead>
            <tbody>{rows.map(render)}</tbody>
          </table>
        </TableWrap>
      )}
    </Card>
  )
}

function HospitalOverview({ data }) {
  const { t } = useLanguage()
  return (
    <>
      <Alert tone={data.alerts.length ? "warning" : "success"} className="mb-4"
        title={data.alerts.length ? t("{count} security alert(s)", { count: data.alerts.length }) : t("No security alerts")}>
        {data.settings.require_verified_doctors
          ? t("Doctors sign only after their registration is verified.")
          : t("{count} doctor(s) not yet verified; verification is not required yet.", { count: data.settings.unverified_doctors })}
      </Alert>
      <Section title="Security alerts" empty="Nothing needs attention." rows={data.alerts}
        columns={["Alert", "Staff member", "When"]}
        render={(alert, index) => (
          <tr key={`${alert.kind}-${alert.user_id}-${index}`}>
            <td>{t(alert.detail)}</td><td>{alert.name}</td><td>{formatTime(alert.at)}</td>
          </tr>
        )} />
      <Section title="Active sessions" empty="No staff member is signed in." rows={data.sessions}
        columns={["Staff member", "Device", "Signed in", "Last used"]}
        render={(row, index) => (
          <tr key={`${row.user_id}-${index}`}>
            <td>{row.name}</td><td>{row.platform}{row.app_version ? ` ${row.app_version}` : ""}</td>
            <td>{formatTime(row.created_at)}</td><td>{formatTime(row.last_used_at)}</td>
          </tr>
        )} />
      <Section title="Sign-in history (30 days)" empty="No sign-ins recorded." rows={data.sign_in_history}
        columns={["Staff member", "Event", "When"]}
        render={(row, index) => (
          <tr key={`${row.user_id}-${row.at}-${index}`}>
            <td>{row.name}</td><td><code className="text-xs">{row.action}</code></td><td>{formatTime(row.at)}</td>
          </tr>
        )} />
      <Section title="Staff permissions" empty="No staff." rows={data.staff}
        columns={["Staff member", "Role", "Status", "Permissions"]}
        render={(row) => (
          <tr key={row.user_id}>
            <td>{row.name}</td><td>{t(row.role)}</td><td>{row.is_active ? t("Active") : t("Inactive")}</td>
            <td className="text-xs text-ink-600">{row.permissions.length ? row.permissions.join(", ") : "—"}</td>
          </tr>
        )} />
    </>
  )
}

function ServerSettings({ data }) {
  const { t } = useLanguage()
  const weak = data.settings.filter((row) => row.secure === false).length
  return (
    <Card>
      <h2 className="px-4 pt-4 text-base font-semibold text-ink-900">{t("Server configuration (platform staff)")}</h2>
      <p className="px-4 pb-2 text-sm text-ink-500">
        {weak ? t("{weak} setting(s) are not suitable for production", { weak }) : t("All checked settings are at their recommended values")}
        {" "}{data.how_to_change}
      </p>
      <TableWrap>
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th scope="col">{t("Setting")}</th>
              <th scope="col">{t("Value")}</th>
              <th scope="col">{t("Assessment")}</th>
              <th scope="col">{t("Environment variable")}</th>
            </tr>
          </thead>
          <tbody>
            {data.settings.map((row) => (
              <tr key={row.key}>
                <td>
                  <p className="font-medium text-ink-900">{t(row.label)}</p>
                  {row.note && <p className="text-xs text-ink-500">{row.note}</p>}
                </td>
                <td className="tabular-nums">{formatValue(row.value)}</td>
                <td><Verdict secure={row.secure} /></td>
                <td><code className="text-xs text-ink-600">{row.key}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
    </Card>
  )
}

function SecuritySettings() {
  const { t } = useLanguage()
  const [overview, setOverview] = useState(null)
  const [server, setServer] = useState(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([api.securityOverview.get(), api.securitySettings.get()]).then(([hospital, platform]) => {
      if (cancelled) return
      if (hospital.status === "fulfilled") setOverview(hospital.value)
      if (platform.status === "fulfilled") setServer(platform.value)
      if (hospital.status === "rejected" && platform.status === "rejected") {
        const reason = hospital.reason
        setError(reason?.status === 403 ? "Only this hospital's Admin can see its security overview." : reason?.message || "")
      }
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div>
      <PageHeader
        title={t("Security settings")}
        description="Sessions, sign-ins, permissions and alerts for this hospital. Read only."
        breadcrumbs={[{ label: "Administration", to: "/admin" }, { label: "Security settings" }]}
      />
      {error && <Alert tone="danger" className="mb-4">{error}</Alert>}
      {loading ? (
        <Card><SkeletonRows rows={8} /></Card>
      ) : !overview && !server ? (
        <Card><EmptyState icon={ShieldCheck} title={t("Security settings not available")} /></Card>
      ) : (
        <>
          {overview && <HospitalOverview data={overview} />}
          {server && <ServerSettings data={server} />}
        </>
      )}
    </div>
  )
}

export default SecuritySettings
