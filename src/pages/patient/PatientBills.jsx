import { useEffect, useState } from "react"
import { Printer, ReceiptIndianRupee } from "lucide-react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { Alert, Button, Card, EmptyState, PrintSheet, SegmentedControl, SkeletonRows, StatusBadge } from "../../components/ui"
import { InvoiceDocument } from "../../components/documents/ClinicalDocuments.jsx"

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 })
// Money arrives as decimal strings calculated by the server.
const money = (v) => inr.format(Number(v || 0))

function PatientBills() {
  const { patient } = useAuth()
  const [bills, setBills] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState("all")
  const [printing, setPrinting] = useState(null)

  useEffect(() => {
    if (!patient?.id) return

    const fetchBills = async () => {
      setLoading(true)
      try {
        const data = await api.billing.invoices.list()
        const allBills = data?.results || data || []
        setBills(allBills.filter((b) => String(b.patient) === String(patient.id)))
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchBills()
  }, [patient?.id])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  const filteredBills = bills.filter((bill) => {
    if (filter === "paid") return bill.status === "Paid"
    if (filter === "due") return bill.status === "Unpaid" || bill.status === "Partial"
    return true
  })

  const totalDue = bills
    .filter((b) => b.status === "Unpaid" || b.status === "Partial")
    .reduce((sum, b) => sum + Number(b.balance_due || 0), 0)

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink-900 sm:text-2xl">Bills</h1>
          <p className="mt-1 text-sm text-ink-500">Your invoices, what has been paid and what is still due.</p>
        </div>
        <SegmentedControl
          label="Filter bills"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: "All" },
            { value: "due", label: "Balance due" },
            { value: "paid", label: "Paid" },
          ]}
        />
      </header>

      {error && <Alert tone="danger">{error}</Alert>}

      {!loading && totalDue > 0 && (
        <Alert tone="warning" title={`Total balance due: ${inr.format(totalDue)}`}>
          Please pay at the hospital billing counter. Online payment is not available yet.
        </Alert>
      )}

      {loading ? (
        <Card><SkeletonRows rows={3} /></Card>
      ) : filteredBills.length === 0 ? (
        <Card>
          <EmptyState
            icon={ReceiptIndianRupee}
            title={bills.length ? "No bills match this filter" : "No bills yet"}
          />
        </Card>
      ) : (
        <ul className="space-y-4">
          {filteredBills.map((bill) => (
            <li key={bill.id}>
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
                  <div>
                    <p className="font-semibold text-ink-900 tabular-nums">Invoice {bill.invoice_number || bill.id}</p>
                    <p className="text-[13px] text-ink-500">
                      {formatDate(bill.created_at)}
                      {bill.hospital_name ? ` · ${bill.hospital_name}` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={bill.status} />
                    <Button size="sm" variant="secondary" icon={Printer} onClick={() => setPrinting(bill)}>Print</Button>
                  </div>
                </div>
                <dl className="grid grid-cols-3 gap-px border-t border-line bg-line text-sm">
                  <div className="bg-white px-5 py-3">
                    <dt className="text-xs text-ink-500">Total</dt>
                    <dd className="mt-0.5 font-semibold text-ink-900 tabular-nums">{money(bill.total_amount ?? bill.total)}</dd>
                  </div>
                  <div className="bg-white px-5 py-3">
                    <dt className="text-xs text-ink-500">Paid</dt>
                    <dd className="mt-0.5 font-semibold text-green-700 tabular-nums">{money(bill.total_paid)}</dd>
                  </div>
                  <div className="bg-white px-5 py-3">
                    <dt className="text-xs text-ink-500">Balance due</dt>
                    <dd className={`mt-0.5 font-semibold tabular-nums ${Number(bill.balance_due) > 0 ? "text-red-700" : "text-ink-900"}`}>{money(bill.balance_due)}</dd>
                  </div>
                </dl>
                {(bill.items || []).length > 0 && (
                  <details className="group border-t border-line">
                    <summary className="cursor-pointer list-none px-5 py-3 text-[13px] font-medium text-brand-700 hover:underline">
                      Show {bill.items.length} item{bill.items.length === 1 ? "" : "s"}
                    </summary>
                    <ul className="divide-y divide-ink-100 px-5 pb-3 text-sm">
                      {bill.items.map((item, i) => (
                        <li key={item.id || i} className="flex justify-between gap-4 py-2">
                          <span className="text-ink-700">{item.description || item.name || "Item"}{item.quantity > 1 ? ` × ${item.quantity}` : ""}</span>
                          <span className="font-medium text-ink-900 tabular-nums">{money(item.subtotal ?? Number(item.unit_price || 0) * Number(item.quantity || 1))}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}

      <PrintSheet open={Boolean(printing)} onClose={() => setPrinting(null)} title="Invoice">
        {printing && <InvoiceDocument invoice={printing} />}
      </PrintSheet>
    </div>
  )
}

export default PatientBills
