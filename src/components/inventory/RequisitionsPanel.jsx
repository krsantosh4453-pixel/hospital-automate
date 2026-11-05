import { useCallback, useEffect, useState } from "react"
import { ClipboardCheck, Plus, Trash2 } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Alert, Button, EmptyState, Field, Input, Modal, Select, StatusBadge, TableWrap, usePrompt } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// Purchase requisitions (I2): raised by the store or pharmacy, approved or
// rejected by an admin or manager other than the requester (the server
// checks), then ordered from a supplier directly or by accepting a quotation.

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const money = (value) => `₹${Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
const emptyLine = () => ({ medicine: "", quantity: "" })

function NewRequisition({ open, onClose, hospital, medicines, onSaved }) {
  const { t } = useLanguage()
  const [departments, setDepartments] = useState([])
  const [form, setForm] = useState({ department: "", reason: "", lines: [emptyLine()] })
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setForm({ department: "", reason: "", lines: [emptyLine()] })
    setError("")
    api.departments.list(hospital.id).then((data) => setDepartments(list(data))).catch(() => setDepartments([]))
  }, [open, hospital.id])

  const setLine = (index, field) => (event) =>
    setForm((prev) => ({ ...prev, lines: prev.lines.map((line, i) => (i === index ? { ...line, [field]: event.target.value } : line)) }))

  const submit = async (event) => {
    event.preventDefault()
    const items = form.lines.filter((line) => line.medicine && Number(line.quantity) > 0)
      .map((line) => ({ medicine: Number(line.medicine), quantity: Number(line.quantity) }))
    if (items.length === 0) {
      setError(t("Add at least one item with a quantity."))
      return
    }
    setSaving(true)
    try {
      await api.procurement.requisitions.create({ department: form.department ? Number(form.department) : null, reason: form.reason, items }, hospital.id)
      onSaved(t("Requisition raised for approval."))
    } catch (err) {
      setError(err.message || "Could not raise the requisition.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t("New requisition")} size="lg"
      footer={<><Button variant="secondary" onClick={onClose}>{t("Cancel")}</Button><Button type="submit" form="requisition-form" loading={saving}>{t("Raise requisition")}</Button></>}>
      <form id="requisition-form" onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Department">
            <Select value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>
              <option value="">{t("Store (no department)")}</option>
              {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </Select>
          </Field>
          <Field label="Reason"><Input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} placeholder={t("e.g. Monthly ward stock")} /></Field>
        </div>
        {form.lines.map((line, index) => (
          <div key={index} className="grid grid-cols-[minmax(0,1fr)_7rem_auto] items-end gap-2">
            <Field label={index === 0 ? "Item" : ""}>
              <Select value={line.medicine} onChange={setLine(index, "medicine")} aria-label={t("Item")}>
                <option value="">{t("Choose…")}</option>
                {medicines.map((m) => <option key={m.apiId} value={m.apiId}>{m.name}{m.batch ? ` · ${m.batch}` : ""}</option>)}
              </Select>
            </Field>
            <Field label={index === 0 ? "Quantity" : ""}><Input type="number" min="1" value={line.quantity} onChange={setLine(index, "quantity")} aria-label={t("Quantity")} /></Field>
            <Button variant="ghost" size="icon-sm" icon={Trash2} aria-label={t("Remove line")} disabled={form.lines.length === 1}
              onClick={() => setForm({ ...form, lines: form.lines.filter((_, i) => i !== index) })} />
          </div>
        ))}
        <Button variant="subtle" size="sm" icon={Plus} onClick={() => setForm({ ...form, lines: [...form.lines, emptyLine()] })}>{t("Add item")}</Button>
        {error && <Alert tone="danger">{error}</Alert>}
      </form>
    </Modal>
  )
}

function OrderDialog({ requisition, hospital, suppliers, onClose, onSaved }) {
  const { t } = useLanguage()
  const [quotes, setQuotes] = useState([])
  const [mode, setMode] = useState("direct")
  const [supplier, setSupplier] = useState("")
  const [costs, setCosts] = useState({})
  const [quoteRef, setQuoteRef] = useState("")
  const [validUntil, setValidUntil] = useState("")
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)
  const active = suppliers.filter((s) => s.is_active)

  const loadQuotes = useCallback(() => {
    api.procurement.quotations.list(hospital.id, requisition.id).then((data) => setQuotes(list(data))).catch(() => setQuotes([]))
  }, [hospital.id, requisition.id])
  useEffect(() => loadQuotes(), [loadQuotes])

  const run = async (action, message) => {
    setSaving(true)
    setError("")
    try {
      await action()
      onSaved(t(message))
    } catch (err) {
      setError(err.message || "Could not save.")
    } finally {
      setSaving(false)
    }
  }
  const rows = requisition.items.map((item) => ({ item: item.id, unit_cost: costs[item.id] }))
  const complete = supplier && rows.every((row) => row.unit_cost !== undefined && row.unit_cost !== "")

  const placeOrder = () => run(() => api.procurement.requisitions.order(requisition.id, { supplier: Number(supplier), unit_costs: rows }, hospital.id), "Purchase order placed.")
  // A saved quotation stays in this dialog so several can be compared before accepting one.
  const addQuote = async () => {
    setSaving(true)
    setError("")
    try {
      await api.procurement.quotations.create({ requisition: requisition.id, supplier: Number(supplier), reference: quoteRef || `Q-${Date.now()}`,
        valid_until: validUntil || null, items: rows.map((row) => ({ requisition_item: row.item, unit_cost: row.unit_cost })) }, hospital.id)
      setSupplier("")
      setCosts({})
      setQuoteRef("")
      setValidUntil("")
      loadQuotes()
    } catch (err) {
      setError(err.message || "Could not save the quotation.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open onClose={onClose} title={t("Order {reference}", { reference: requisition.reference })} size="lg"
      footer={<Button variant="secondary" onClick={onClose}>{t("Close")}</Button>}>
      <div className="space-y-4">
        {quotes.length > 0 && (
          <TableWrap>
            <table className="hms-table">
              <thead><tr><th scope="col">{t("Supplier")}</th><th scope="col">{t("Valid until")}</th><th scope="col" className="text-right">{t("Total")}</th><th scope="col">{t("Status")}</th><th scope="col"><span className="sr-only">{t("Actions")}</span></th></tr></thead>
              <tbody>
                {quotes.map((quote) => (
                  <tr key={quote.id}>
                    <td>{quote.supplier_name}</td>
                    <td>{quote.valid_until || "—"}</td>
                    <td className="text-right tabular-nums">{money(quote.total)}</td>
                    <td><StatusBadge status={quote.status} /></td>
                    <td className="text-right">{quote.status === "Received" && (
                      <Button size="sm" loading={saving} onClick={() => run(() => api.procurement.quotations.accept(quote.id, hospital.id), "Quotation accepted; purchase order placed.")}>{t("Accept")}</Button>
                    )}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
        <div className="flex gap-2">
          <Button size="sm" variant={mode === "direct" ? "primary" : "secondary"} onClick={() => setMode("direct")}>{t("Order directly")}</Button>
          <Button size="sm" variant={mode === "quote" ? "primary" : "secondary"} onClick={() => setMode("quote")}>{t("Record a quotation")}</Button>
        </div>
        <Field label="Supplier" required>
          <Select value={supplier} onChange={(e) => setSupplier(e.target.value)}>
            <option value="">{t("Choose…")}</option>
            {active.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </Select>
        </Field>
        {mode === "quote" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Quotation reference"><Input value={quoteRef} onChange={(e) => setQuoteRef(e.target.value)} /></Field>
            <Field label="Valid until"><Input type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} /></Field>
          </div>
        )}
        {requisition.items.map((item) => (
          <Field key={item.id} label={t("{name} × {quantity}: unit cost (₹)", { name: item.medicine_name, quantity: item.quantity })} required>
            <Input type="number" min="0" step="0.01" value={costs[item.id] ?? ""} onChange={(e) => setCosts({ ...costs, [item.id]: e.target.value })} />
          </Field>
        ))}
        {error && <Alert tone="danger">{error}</Alert>}
        <div className="flex justify-end">
          {mode === "direct"
            ? <Button disabled={!complete} loading={saving} onClick={placeOrder}>{t("Place purchase order")}</Button>
            : <Button disabled={!complete} loading={saving} onClick={addQuote}>{t("Save quotation")}</Button>}
        </div>
      </div>
    </Modal>
  )
}

export default function RequisitionsPanel({ hospital, medicines, suppliers, canRaise, canApprove, canOrder, onChanged }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [promptText, promptDialog] = usePrompt()
  const [rows, setRows] = useState([])
  const [error, setError] = useState("")
  const [reloadToken, setReloadToken] = useState(0)
  const [creating, setCreating] = useState(false)
  const [ordering, setOrdering] = useState(null)

  useEffect(() => {
    let cancelled = false
    api.procurement.requisitions.list(hospital.id)
      .then((data) => !cancelled && (setRows(list(data)), setError("")))
      .catch((err) => !cancelled && setError(err.message || "Could not load requisitions."))
    return () => {
      cancelled = true
    }
  }, [hospital.id, reloadToken])

  const saved = (message) => {
    if (message) toast.success(message)
    setCreating(false)
    setOrdering(null)
    setReloadToken((n) => n + 1)
    onChanged?.()
  }

  const decide = async (row, approve) => {
    const note = approve ? "" : await promptText({ title: t("Reject {reference}", { reference: row.reference }), label: t("Reason"), confirmLabel: "Reject" })
    if (!approve && !note?.trim()) return
    try {
      await (approve ? api.procurement.requisitions.approve : api.procurement.requisitions.reject)(row.id, { note }, hospital.id)
      saved(approve ? t("Requisition approved.") : t("Requisition rejected."))
    } catch (err) {
      toast.error(err.message || "Could not save the decision.")
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-3 px-5 py-4">
        <p className="text-sm text-ink-600">{t("Requests for stock, approved by an administrator or manager before ordering.")}</p>
        {canRaise && <Button size="sm" icon={Plus} onClick={() => setCreating(true)}>{t("New requisition")}</Button>}
      </div>
      {error && <Alert tone="danger" className="mx-5 mb-4">{error}</Alert>}
      {rows.length === 0 ? (
        <EmptyState compact icon={ClipboardCheck} title={t("No requisitions yet")} />
      ) : (
        <TableWrap>
          <table className="hms-table">
            <thead>
              <tr>
                <th scope="col">{t("Requisition")}</th>
                <th scope="col">{t("Department")}</th>
                <th scope="col">{t("Items")}</th>
                <th scope="col">{t("Requested by")}</th>
                <th scope="col">{t("Status")}</th>
                <th scope="col"><span className="sr-only">{t("Actions")}</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className="tabular-nums">{row.reference}</td>
                  <td>{row.department_name || t("Store")}</td>
                  <td className="text-ink-600">{row.items.map((item) => `${item.medicine_name} × ${item.quantity}`).join(", ")}</td>
                  <td>{row.requested_by_name}</td>
                  <td>
                    <StatusBadge status={row.status} />
                    {row.decision_note && <span className="block text-xs text-ink-500">{row.decision_note}</span>}
                    {row.purchase_reference && <span className="block text-xs text-ink-500">{row.purchase_reference}</span>}
                  </td>
                  <td>
                    <div className="flex justify-end gap-1.5">
                      {row.status === "Submitted" && canApprove && (
                        <>
                          <Button size="sm" onClick={() => decide(row, true)}>{t("Approve")}</Button>
                          <Button size="sm" variant="ghost" onClick={() => decide(row, false)}>{t("Reject")}</Button>
                        </>
                      )}
                      {row.status === "Approved" && canOrder && <Button size="sm" variant="subtle" onClick={() => setOrdering(row)}>{t("Order")}</Button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}
      <NewRequisition open={creating} onClose={() => setCreating(false)} hospital={hospital} medicines={medicines} onSaved={saved} />
      {ordering && <OrderDialog requisition={ordering} hospital={hospital} suppliers={suppliers} onClose={() => setOrdering(null)} onSaved={saved} />}
      {promptDialog}
    </div>
  )
}
