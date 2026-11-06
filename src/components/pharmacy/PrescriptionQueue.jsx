import { useEffect, useState } from "react"
import { ClipboardList } from "lucide-react"
import api from "../../services/api.js"
import Pagination from "../Pagination.jsx"
import { Alert, Badge, Button, EmptyState, SearchInput, SkeletonRows, StatusBadge, TableWrap, Tabs } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { availabilityOf } from "../../utils/dispenseBatches.js"
import { PAPER_SOURCE, mapPrescriptionFromApi } from "../../utils/prescriptionRecord.js"

// F6: prescriptions waiting at the pharmacy, straight from the server, so
// nobody has to type an RX number. Oldest first for the work lists.
const QUEUE_VIEWS = [
  { id: "todo", label: "To dispense", status: "Confirmed,Pending,Partially Dispensed", order: "oldest" },
  { id: "verify", label: "Awaiting verification", status: "Pending Verification", order: "oldest" },
  { id: "done", label: "Dispensed", status: "Dispensed" },
]
const PAGE_SIZE = 50
const SEARCH_DELAY_MS = 300

const AVAILABILITY = {
  "in-stock": { tone: "success", label: "In stock" },
  split: { tone: "warning", label: "Split across batches" },
  short: { tone: "warning", label: "Not enough stock" },
  none: { tone: "danger", label: "Not in stock" },
  done: { tone: "neutral", label: "Given" },
}

const formatWhen = (iso) => {
  const date = new Date(iso)
  if (!iso || Number.isNaN(date.getTime())) return "—"
  return date.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
}

const readPage = (data) => ({
  rows: (Array.isArray(data) ? data : data?.results || []).map(mapPrescriptionFromApi),
  count: Array.isArray(data) ? data.length : Number(data?.count || 0),
})

/**
 * @param {{ hospitalId: number, stock: Array<object>, refreshKey?: unknown,
 *   selectedId?: number|null, onOpen: (prescription: object) => void }} props
 */
export default function PrescriptionQueue({ hospitalId, stock, refreshKey, selectedId, onOpen }) {
  const { t } = useLanguage()
  const [view, setView] = useState(QUEUE_VIEWS[0].id)
  const [query, setQuery] = useState("")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [result, setResult] = useState({ rows: [], count: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query.trim())
      setPage(1)
    }, SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (!hospitalId) return undefined
    const current = QUEUE_VIEWS.find((v) => v.id === view)
    let cancelled = false
    setLoading(true)
    api.prescriptions
      .list({ hospitalId, status: current.status, order: current.order, search, page })
      .then((data) => {
        if (cancelled) return
        setResult(readPage(data))
        setError("")
      })
      .catch((err) => !cancelled && setError(err.message || "Could not load prescriptions."))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [hospitalId, view, search, page, refreshKey, retry])

  const chooseView = (id) => {
    setView(id)
    setPage(1)
  }

  const { rows, count } = result
  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  return (
    <section aria-labelledby="pharmacy-queue-title" className="mt-5">
      <h3 id="pharmacy-queue-title" className="sr-only">{t("Prescription queue")}</h3>
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <Tabs tabs={QUEUE_VIEWS.map(({ id, label }) => ({ id, label }))} value={view} onChange={chooseView}
          label="Prescription queue" />
        <SearchInput value={query} onChange={setQuery} placeholder="RX number, patient, UHID or doctor"
          label="Search prescriptions" className="w-full md:w-80" />
      </div>

      {error && (
        <Alert tone="danger" className="mt-3"
          action={<Button size="sm" variant="secondary" onClick={() => setRetry((n) => n + 1)}>{t("Retry")}</Button>}>
          {error}
        </Alert>
      )}

      {loading && rows.length === 0 ? (
        <SkeletonRows rows={3} />
      ) : rows.length === 0 ? (
        <EmptyState compact icon={ClipboardList}
          title={search ? t("No prescriptions match your search") : t("Nothing waiting here")} />
      ) : (
        <TableWrap>
          <table className="hms-table">
            <caption className="sr-only">{t(QUEUE_VIEWS.find((v) => v.id === view).label)}</caption>
            <thead>
              <tr>
                <th scope="col">{t("Prescription")}</th>
                <th scope="col">{t("Patient")}</th>
                <th scope="col">{t("Doctor")}</th>
                <th scope="col">{t("Medicines")}</th>
                <th scope="col">{t("Status")}</th>
                <th scope="col"><span className="sr-only">{t("Actions")}</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((rx) => (
                <tr key={rx.apiId} onClick={() => onOpen(rx)}
                  className={`cursor-pointer ${String(selectedId) === String(rx.apiId) ? "[&>td]:bg-brand-50/60" : ""}`}>
                  <td className="whitespace-nowrap">
                    <span className="block font-semibold tabular-nums text-brand-700">{rx.id}</span>
                    <span className="block text-xs text-ink-500 tabular-nums">{formatWhen(rx.createdAtIso)}</span>
                  </td>
                  <td>
                    <span className="block font-medium text-ink-900">{rx.patientName}</span>
                    <span className="block text-xs text-ink-500 tabular-nums">{rx.patientUhid || t("No UHID")}</span>
                  </td>
                  <td>
                    {rx.doctor || rx.originalPrescriberName || "—"}
                    {rx.source === PAPER_SOURCE && <span className="block text-xs text-ink-500">{t("Paper prescription")}</span>}
                  </td>
                  <td>
                    <ul className="space-y-1">
                      {rx.medicines.map((item) => {
                        const state = AVAILABILITY[availabilityOf(item, stock)]
                        return (
                          <li key={item.id} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
                            <span>{item.name} × <span className="tabular-nums">{item.quantity}</span></span>
                            <Badge tone={state.tone}>{t(state.label)}</Badge>
                          </li>
                        )
                      })}
                    </ul>
                  </td>
                  <td><StatusBadge status={rx.status} /></td>
                  <td className="text-right">
                    <Button size="sm" variant="subtle" onClick={(event) => { event.stopPropagation(); onOpen(rx) }}
                      aria-label={t("Open {rx} for {patient}", { rx: rx.id, patient: rx.patientName })}>
                      {t("Open")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}

      <Pagination currentPage={page} totalPages={totalPages} totalRecords={count} onPageChange={setPage} />
    </section>
  )
}
