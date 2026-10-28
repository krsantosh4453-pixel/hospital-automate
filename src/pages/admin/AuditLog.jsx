import { useEffect, useState } from "react"
import { History, RefreshCw } from "lucide-react"
import { usePatient } from "../../assets/context/PatientContext.jsx"
import api from "../../services/api.js"
import Pagination from "../../components/Pagination.jsx"
import { Alert, Button, Card, EmptyState, Field, Input, PageHeader, SkeletonRows, TableWrap, Toolbar } from "../../components/ui"

// Audit trail viewer (requirement A15). The server scopes rows to the selected
// hospital and allows only that hospital's Admin; this page only filters.

const PAGE_SIZE = 50
const EMPTY_FILTERS = { action: "", model: "", user: "", from: "", to: "" }

function formatWhen(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })
}

// The service writes details as JSON text; show it compactly when it is.
function formatDetails(details) {
  if (!details) return ""
  try {
    const parsed = JSON.parse(details)
    return typeof parsed === "object" ? JSON.stringify(parsed) : String(parsed)
  } catch {
    return details
  }
}

function AuditLog() {
  const { selectedHospital } = usePatient()
  const [draft, setDraft] = useState(EMPTY_FILTERS)
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    if (!selectedHospital?.id) {
      setLoading(false)
      return undefined
    }
    let cancelled = false
    setLoading(true)
    setError("")
    api.audit
      .search(selectedHospital.id, { ...filters, page })
      .then((data) => {
        if (cancelled) return
        setRows(Array.isArray(data) ? data : data?.results || [])
        setCount(Array.isArray(data) ? data.length : data?.count || 0)
      })
      .catch((err) => !cancelled && setError(err.status === 403 ? "Only this hospital's administrators can read the audit trail." : err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [selectedHospital?.id, filters, page, reloadToken])

  const apply = (event) => {
    event.preventDefault()
    setPage(1)
    setFilters(draft)
  }

  const clear = () => {
    setDraft(EMPTY_FILTERS)
    setFilters(EMPTY_FILTERS)
    setPage(1)
  }

  const set = (field) => (event) => setDraft({ ...draft, [field]: event.target.value })

  return (
    <div>
      <PageHeader
        title="Audit log"
        description={`Every recorded change${selectedHospital?.name ? ` at ${selectedHospital.name}` : ""}, newest first. Read only.`}
        breadcrumbs={[{ label: "Administration", to: "/admin" }, { label: "Audit log" }]}
        actions={<Button variant="secondary" icon={RefreshCw} onClick={() => setReloadToken((n) => n + 1)}>Refresh</Button>}
      />

      {error && <Alert tone="danger" className="mb-4">{error}</Alert>}

      <Card>
        <form onSubmit={apply}>
          <Toolbar
            actions={
              <>
                <Button variant="ghost" onClick={clear}>Clear</Button>
                <Button type="submit">Apply filters</Button>
              </>
            }
          >
            <div className="grid w-full grid-cols-2 gap-3 md:grid-cols-5">
              <Field label="Action"><Input value={draft.action} onChange={set("action")} placeholder="e.g. delete" /></Field>
              <Field label="Record type"><Input value={draft.model} onChange={set("model")} placeholder="e.g. Patient" /></Field>
              <Field label="User"><Input value={draft.user} onChange={set("user")} placeholder="username" /></Field>
              <Field label="From"><Input type="date" value={draft.from} onChange={set("from")} /></Field>
              <Field label="To"><Input type="date" min={draft.from || undefined} value={draft.to} onChange={set("to")} /></Field>
            </div>
          </Toolbar>
        </form>

        {loading ? (
          <SkeletonRows rows={6} />
        ) : rows.length === 0 ? (
          <EmptyState icon={History} title={error ? "Audit trail not available" : "No matching activity"} />
        ) : (
          <TableWrap>
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">User</th>
                  <th scope="col">Action</th>
                  <th scope="col">Record</th>
                  <th scope="col">Details</th>
                  <th scope="col">IP address</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className="whitespace-nowrap tabular-nums">{formatWhen(row.created_at)}</td>
                    <td>{row.username || (row.user ? `user ${row.user}` : "system")}</td>
                    <td className="font-medium text-ink-900">{row.action}</td>
                    <td>{row.model_name}{row.object_id ? ` #${row.object_id}` : ""}</td>
                    <td className="max-w-xs truncate text-ink-600" title={formatDetails(row.details)}>{formatDetails(row.details) || "—"}</td>
                    <td className="tabular-nums text-ink-600">{row.ip_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
        <Pagination
          currentPage={page}
          totalPages={Math.max(1, Math.ceil(count / PAGE_SIZE))}
          totalRecords={count}
          onPageChange={setPage}
        />
      </Card>
    </div>
  )
}

export default AuditLog
