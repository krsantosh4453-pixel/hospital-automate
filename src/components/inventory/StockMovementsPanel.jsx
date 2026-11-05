import { useEffect, useState } from "react"
import { ArrowRightLeft, Undo2 } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Alert, Badge, Button, EmptyState, Field, Input, Modal, Select, TableWrap } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// Stock leaving the store other than by sale (I4): issue to a department,
// return to the supplier, and consignment stock settled as used. The server
// refuses anything that would take stock below zero or return more than was
// received, and records each movement in the stock ledger.

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const money = (value) => `₹${Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
const newKey = () => `iss-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
const EMPTY_ISSUE = { department: "", medicine: "", quantity: "", received_by_name: "" }

export default function StockMovementsPanel({ hospital, medicines, canEdit, onChanged }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [departments, setDepartments] = useState([])
  const [issues, setIssues] = useState([])
  const [receiptLines, setReceiptLines] = useState([])
  const [error, setError] = useState("")
  const [reloadToken, setReloadToken] = useState(0)
  const [issue, setIssue] = useState({ ...EMPTY_ISSUE, key: newKey() })
  const [saving, setSaving] = useState(false)
  const [lineAction, setLineAction] = useState(null) // { type: "return" | "settle", line }
  const [lineForm, setLineForm] = useState({ quantity: "", reason: "", reference: "" })

  useEffect(() => {
    let cancelled = false
    Promise.all([
      api.departments.list(hospital.id),
      api.procurement.stockIssues.list(hospital.id),
      api.procurement.grnItems.list(hospital.id),
    ])
      .then(([deps, iss, lines]) => {
        if (cancelled) return
        setDepartments(list(deps))
        setIssues(list(iss))
        setReceiptLines(list(lines).filter((line) => line.open_quantity > 0))
        setError("")
      })
      .catch((err) => !cancelled && setError(err.message || "Could not load store movements."))
    return () => {
      cancelled = true
    }
  }, [hospital.id, reloadToken])

  const done = (message) => {
    toast.success(t(message))
    setReloadToken((n) => n + 1)
    onChanged?.()
  }

  const submitIssue = async (event) => {
    event.preventDefault()
    if (!issue.department || !issue.medicine || !(Number(issue.quantity) > 0)) {
      toast.warning(t("Choose the department and item and enter a quantity."))
      return
    }
    setSaving(true)
    try {
      await api.procurement.stockIssues.create({ department: Number(issue.department), medicine: Number(issue.medicine),
        quantity: Number(issue.quantity), received_by_name: issue.received_by_name, idempotency_key: issue.key }, hospital.id)
      setIssue({ ...EMPTY_ISSUE, key: newKey() })
      done("Stock issued.")
    } catch (err) {
      toast.error(err.message || "Could not issue the stock.")
    } finally {
      setSaving(false)
    }
  }

  const submitLine = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const { type, line } = lineAction
      if (type === "return") {
        await api.procurement.supplierReturns.create({ receipt_item: line.id, quantity: Number(lineForm.quantity), reason: lineForm.reason }, hospital.id)
        done("Returned to the supplier.")
      } else {
        await api.procurement.consignmentSettlements.create({ receipt_item: line.id, quantity: Number(lineForm.quantity), reference: lineForm.reference }, hospital.id)
        done("Consignment use recorded.")
      }
      setLineAction(null)
    } catch (err) {
      toast.error(err.message || "Could not save.")
    } finally {
      setSaving(false)
    }
  }

  const openLine = (type, line) => {
    setLineAction({ type, line })
    setLineForm({ quantity: "", reason: "", reference: "" })
  }

  return (
    <div className="space-y-6 px-5 py-4">
      {error && <Alert tone="danger">{error}</Alert>}

      <section>
        <h3 className="mb-3 text-sm font-semibold text-ink-900">{t("Issue to a department")}</h3>
        {canEdit && (
          <form onSubmit={submitIssue} className="mb-4 grid gap-3 md:grid-cols-[1fr_1fr_7rem_1fr_auto] md:items-end">
            <Field label="Department">
              <Select value={issue.department} onChange={(e) => setIssue({ ...issue, department: e.target.value })}>
                <option value="">{t("Choose…")}</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </Select>
            </Field>
            <Field label="Item">
              <Select value={issue.medicine} onChange={(e) => setIssue({ ...issue, medicine: e.target.value })}>
                <option value="">{t("Choose…")}</option>
                {medicines.filter((m) => m.quantity > 0).map((m) => <option key={m.apiId} value={m.apiId}>{m.name}{m.batch ? ` · ${m.batch}` : ""} · {m.quantity}</option>)}
              </Select>
            </Field>
            <Field label="Quantity"><Input type="number" min="1" value={issue.quantity} onChange={(e) => setIssue({ ...issue, quantity: e.target.value })} /></Field>
            <Field label="Received by"><Input value={issue.received_by_name} onChange={(e) => setIssue({ ...issue, received_by_name: e.target.value })} /></Field>
            <Button type="submit" icon={ArrowRightLeft} loading={saving}>{t("Issue")}</Button>
          </form>
        )}
        {issues.length === 0 ? <EmptyState compact icon={ArrowRightLeft} title={t("Nothing issued yet")} /> : (
          <TableWrap>
            <table className="hms-table">
              <thead><tr><th scope="col">{t("When")}</th><th scope="col">{t("Department")}</th><th scope="col">{t("Item")}</th><th scope="col" className="text-right">{t("Quantity")}</th><th scope="col">{t("Issued by")}</th></tr></thead>
              <tbody>
                {issues.slice(0, 15).map((row) => (
                  <tr key={row.id}>
                    <td className="whitespace-nowrap text-ink-600">{new Date(row.created_at).toLocaleString("en-IN")}</td>
                    <td>{row.department_name}</td>
                    <td>{row.medicine_name}{row.batch ? ` · ${row.batch}` : ""}</td>
                    <td className="text-right tabular-nums">{row.quantity}</td>
                    <td>{row.issued_by_name}{row.received_by_name ? ` → ${row.received_by_name}` : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold text-ink-900">{t("Received stock: return or settle")}</h3>
        {receiptLines.length === 0 ? <EmptyState compact icon={Undo2} title={t("No received stock open for return")} /> : (
          <TableWrap>
            <table className="hms-table">
              <thead><tr><th scope="col">{t("Receipt")}</th><th scope="col">{t("Supplier")}</th><th scope="col">{t("Item")}</th><th scope="col" className="text-right">{t("Open")}</th><th scope="col"><span className="sr-only">{t("Actions")}</span></th></tr></thead>
              <tbody>
                {receiptLines.map((line) => (
                  <tr key={line.id}>
                    <td className="tabular-nums">{line.receipt_reference}{line.is_consignment && <Badge tone="info" className="ml-2">{t("Consignment")}</Badge>}</td>
                    <td>{line.supplier_name}</td>
                    <td>{line.medicine_name}{line.batch ? ` · ${line.batch}` : ""}</td>
                    <td className="text-right tabular-nums">{line.open_quantity} / {line.quantity_received}</td>
                    <td>
                      {canEdit && (
                        <div className="flex justify-end gap-1.5">
                          <Button size="sm" variant="ghost" onClick={() => openLine("return", line)}>{t("Return to supplier")}</Button>
                          {line.is_consignment && <Button size="sm" variant="subtle" onClick={() => openLine("settle", line)}>{t("Record use")}</Button>}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </section>

      <Modal open={Boolean(lineAction)} onClose={() => setLineAction(null)} size="sm"
        title={lineAction?.type === "return" ? t("Return to supplier") : t("Record consignment use")}
        footer={<><Button variant="secondary" onClick={() => setLineAction(null)}>{t("Cancel")}</Button><Button type="submit" form="receipt-line-form" loading={saving}>{t("Save")}</Button></>}>
        <form id="receipt-line-form" onSubmit={submitLine} className="space-y-4">
          <p className="text-sm text-ink-700">
            {lineAction?.line.medicine_name} · {lineAction?.line.receipt_reference} · {t("up to {left}", { left: lineAction?.line.open_quantity })} · {money(lineAction?.line.unit_cost)} {t("each")}
          </p>
          <Field label="Quantity" required><Input type="number" min="1" max={lineAction?.line.open_quantity} value={lineForm.quantity} onChange={(e) => setLineForm({ ...lineForm, quantity: e.target.value })} /></Field>
          {lineAction?.type === "return"
            ? <Field label="Reason" required><Input value={lineForm.reason} onChange={(e) => setLineForm({ ...lineForm, reason: e.target.value })} placeholder={t("e.g. Damaged packs")} /></Field>
            : <Field label="Supplier bill reference"><Input value={lineForm.reference} onChange={(e) => setLineForm({ ...lineForm, reference: e.target.value })} /></Field>}
        </form>
      </Modal>
    </div>
  )
}
