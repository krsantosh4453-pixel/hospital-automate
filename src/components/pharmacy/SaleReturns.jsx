import { useEffect, useState } from "react"
import { Undo2 } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Alert, Button, Card, CardHeader, EmptyState, Field, Input, Modal, SearchInput, TableWrap } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// Medicine handed back by OPD/IPD patients (F5). The server caps returns at
// what was sold, puts stock back only when the pharmacist confirms it is fit
// and the batch has not expired, and records the refund amount.

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const rupees = (value) => `₹${Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
const EMPTY = { quantity: "", reason: "", restock: false }

export default function SaleReturns({ hospitalId, canReturn, onReturned, refreshKey }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [sales, setSales] = useState([])
  const [error, setError] = useState("")
  const [query, setQuery] = useState("")
  const [reloadToken, setReloadToken] = useState(0)
  const [returning, setReturning] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState("")

  useEffect(() => {
    if (!hospitalId) return undefined
    let cancelled = false
    api.pharmacy.sales.list(hospitalId)
      .then((data) => !cancelled && (setSales(list(data)), setError("")))
      .catch((err) => !cancelled && setError(err.message || "Could not load sales."))
    return () => {
      cancelled = true
    }
  }, [hospitalId, reloadToken, refreshKey])

  const needle = query.trim().toLowerCase()
  const shown = sales
    .filter((sale) => !needle || `${sale.patient_name} ${sale.medicine_name} SALE-${sale.id}`.toLowerCase().includes(needle))
    .slice(0, 20)

  const open = (sale) => {
    setReturning(sale)
    setForm(EMPTY)
    setFormError("")
  }

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setFormError("")
    try {
      const result = await api.pharmacy.sales.returnSale(returning.id, {
        quantity: Number(form.quantity), reason: form.reason, restock: form.restock,
      })
      toast.success(t("Return recorded. Refund {amount}.", { amount: rupees(result.refund_amount) }))
      setReturning(null)
      setReloadToken((n) => n + 1)
      onReturned?.()
    } catch (err) {
      setFormError(err.message || "Could not record the return.")
    } finally {
      setSaving(false)
    }
  }

  const left = returning ? returning.quantity - (returning.returned_quantity || 0) : 0

  return (
    <Card className="mt-6">
      <CardHeader title="Medicine returns" description="Medicine handed back by a patient. Only sealed, unexpired stock goes back on the shelf." />
      <div className="px-5 pt-4"><SearchInput value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("Search patient, medicine or SALE-number")} /></div>
      {error && <Alert tone="danger" className="mx-5 mt-4">{error}</Alert>}
      {shown.length === 0 ? (
        <EmptyState compact icon={Undo2} title={t("No sales to show")} />
      ) : (
        <TableWrap>
          <table className="hms-table">
            <thead>
              <tr>
                <th scope="col">{t("Sale")}</th>
                <th scope="col">{t("Patient")}</th>
                <th scope="col">{t("Medicine")}</th>
                <th scope="col" className="text-right">{t("Sold")}</th>
                <th scope="col" className="text-right">{t("Returned")}</th>
                {canReturn && <th scope="col"><span className="sr-only">{t("Actions")}</span></th>}
              </tr>
            </thead>
            <tbody>
              {shown.map((sale) => (
                <tr key={sale.id}>
                  <td className="tabular-nums text-ink-600">SALE-{sale.id}</td>
                  <td>{sale.patient_name}</td>
                  <td>
                    {sale.medicine_name}
                    {sale.substituted_for && <span className="block text-xs text-ink-500">{t("Instead of {name}", { name: sale.substituted_for })}</span>}
                  </td>
                  <td className="text-right tabular-nums">{sale.quantity}</td>
                  <td className="text-right tabular-nums">{sale.returned_quantity || 0}</td>
                  {canReturn && (
                    <td className="text-right">
                      {sale.quantity > (sale.returned_quantity || 0) && (
                        <Button size="sm" variant="subtle" onClick={() => open(sale)}>{t("Return")}</Button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}

      <Modal open={Boolean(returning)} onClose={() => setReturning(null)} title={t("Return medicine")} size="sm"
        footer={<><Button variant="secondary" onClick={() => setReturning(null)}>{t("Cancel")}</Button><Button type="submit" form="sale-return" loading={saving}>{t("Record return")}</Button></>}>
        <form id="sale-return" onSubmit={submit} className="space-y-4">
          <p className="text-sm text-ink-700">{returning?.medicine_name} · {returning?.patient_name} · {t("up to {left}", { left })}</p>
          <Field label="Quantity returned" required><Input type="number" min="1" max={left} value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></Field>
          <Field label="Reason" required><Input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} placeholder={t("e.g. Course stopped by doctor")} /></Field>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" checked={form.restock} onChange={(e) => setForm({ ...form, restock: e.target.checked })} />
            {t("Sealed and fit to give again: put back in stock")}
          </label>
          {formError && <Alert tone="danger">{formError}</Alert>}
        </form>
      </Modal>
    </Card>
  )
}
