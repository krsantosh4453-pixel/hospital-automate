import { useEffect, useState } from "react"
import { CircleAlert, CircleCheck, Info, ShieldCheck } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Card, EmptyState, PageHeader, SkeletonRows, TableWrap } from "../../components/ui"

// Effective security configuration (requirement A14). Read only: the values
// are environment variables set on the server, never changed from the browser.

const formatValue = (value) => (typeof value === "boolean" ? (value ? "On" : "Off") : String(value))

function Verdict({ secure }) {
  if (secure === true) return <span className="inline-flex items-center gap-1 text-green-700"><CircleCheck size={15} aria-hidden="true" />Recommended</span>
  if (secure === false) return <span className="inline-flex items-center gap-1 text-amber-700"><CircleAlert size={15} aria-hidden="true" />Not for production</span>
  return <span className="inline-flex items-center gap-1 text-ink-500"><Info size={15} aria-hidden="true" />Information</span>
}

function SecuritySettings() {
  const [data, setData] = useState(null)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    api.securitySettings
      .get()
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(err.status === 403 ? "Only hospital administrators can see the security settings." : err.message))
    return () => {
      cancelled = true
    }
  }, [])

  const weak = (data?.settings || []).filter((row) => row.secure === false).length

  return (
    <div>
      <PageHeader
        title="Security settings"
        description="How sign-in, sessions and rate limits are configured on this server. Read only."
        breadcrumbs={[{ label: "Administration", to: "/admin" }, { label: "Security settings" }]}
      />
      {error && <Alert tone="danger" className="mb-4">{error}</Alert>}
      {data && (
        <Alert tone={weak ? "warning" : "success"} className="mb-4" title={weak ? `${weak} setting(s) are not suitable for production` : "All checked settings are at their recommended values"}>
          {data.how_to_change}
        </Alert>
      )}
      <Card>
        {!data && !error ? (
          <SkeletonRows rows={8} />
        ) : !data ? (
          <EmptyState icon={ShieldCheck} title="Security settings not available" />
        ) : (
          <TableWrap>
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th scope="col">Setting</th>
                  <th scope="col">Value</th>
                  <th scope="col">Assessment</th>
                  <th scope="col">Environment variable</th>
                </tr>
              </thead>
              <tbody>
                {data.settings.map((row) => (
                  <tr key={row.key}>
                    <td>
                      <p className="font-medium text-ink-900">{row.label}</p>
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
        )}
      </Card>
    </div>
  )
}

export default SecuritySettings
