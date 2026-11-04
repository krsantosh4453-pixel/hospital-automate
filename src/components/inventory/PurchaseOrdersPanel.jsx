import { useState } from "react"
import { ClipboardList, PackageCheck, Plus, Trash2 } from "lucide-react"
import api from "../../services/api.js"
import { hospitalToday } from "../../utils/hospitalDate.js"
import { useToast } from "../Toast.jsx"
import { Button, EmptyState, Field, Input, Modal, Select, StatusBadge, TableWrap } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

const RECEIVABLE = ["Draft", "Ordered", "Partial"]
const today = () => hospitalToday()
const money = (value) => `₹${Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const orderTotal = (order) => (order.items || []).reduce((sum, line) => sum + Number(line.line_total || 0), 0)
const emptyLine = () => ({ medicine: "", quantity_ordered: "", unit_cost: "" })

/**
 * Purchase orders of one hospital: raise an order, then receive goods against it (GRN).
 * Receiving goes through the server's atomic receive action, which adds stock and writes the ledger.
 *
 * @param {{ hospital: { id: number, name: string }, orders: object[], suppliers: object[], medicines: object[], canEdit: boolean, onChanged: () => void }} props
 */
export default function PurchaseOrdersPanel({ hospital, orders, suppliers, medicines, canEdit, onChanged }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [creating, setCreating] = useState(false)
  const [receiving, setReceiving] = useState(null)
  const [saving, setSaving] = useState(false)
  const [order, setOrder] = useState({ supplier: "", reference: "", purchase_date: today(), lines: [emptyLine()] })
  const [receipt, setReceipt] = useState({ reference: "", received_by: "", lines: [] })

  const activeSuppliers = suppliers.filter((s) => s.is_active)

  const startOrder = () => {
    setOrder({ supplier: activeSuppliers[0]?.id || "", reference: "", purchase_date: today(), lines: [emptyLine()] })
    setCreating(true)
  }
  const setLine = (index, field, value) =>
    setOrder({ ...order, lines: order.lines.map((line, i) => (i === index ? { ...line, [field]: value } : line)) })

  const createOrder = async (e) => {
    e.preventDefault()
    const lines = order.lines.filter((line) => line.medicine)
    if (!order.supplier || !order.reference.trim() || lines.length === 0) {
      toast.warning("Choose a supplier, enter a reference and add at least one item.")
      return
    }
    if (lines.some((line) => Number(line.quantity_ordered) <= 0 || Number(line.unit_cost) < 0 || line.unit_cost === "")) {
      toast.warning("Every item needs a quantity above 0 and a unit cost.")
      return
    }
    setSaving(true)
    try {
      await api.procurement.purchases.create({
        hospital: hospital.id,
        supplier: Number(order.supplier),
        reference: order.reference.trim(),
        purchase_date: order.purchase_date,
        status: "Ordered",
        items: lines.map((line) => ({
          medicine: Number(line.medicine),
          quantity_ordered: Number(line.quantity_ordered),
          unit_cost: Number(line.unit_cost).toFixed(2),
        })),
      })
      toast.success(t("Purchase order {reference} raised.", { reference: order.reference.trim() }))
      setCreating(false)
      onChanged()
    } catch (err) {
      toast.error(err.message || "Could not raise the purchase order.")
    } finally {
      setSaving(false)
    }
  }

  const startReceipt = (purchase) => {
    setReceipt({
      reference: "",
      received_by: "",
      lines: (purchase.items || []).map((line) => ({
        purchase_item: line.id,
        medicine_name: line.medicine_name,
        remaining: Math.max(0, line.quantity_ordered - line.quantity_received),
        quantity_received: String(Math.max(0, line.quantity_ordered - line.quantity_received)),
        batch: line.batch || "",
        expiry_date: line.expiry_date || "",
      })),
    })
    setReceiving(purchase)
  }
  const setReceiptLine = (index, field, value) =>
    setReceipt({ ...receipt, lines: receipt.lines.map((line, i) => (i === index ? { ...line, [field]: value } : line)) })

  const receiveGoods = async (e) => {
    e.preventDefault()
    const lines = receipt.lines.filter((line) => Number(line.quantity_received) > 0)
    if (!receipt.reference.trim()) {
      toast.warning("Enter the supplier's invoice or delivery note number.")
      return
    }
    if (lines.length === 0) {
      toast.warning("Enter a quantity for at least one item.")
      return
    }
    const over = lines.find((line) => Number(line.quantity_received) > line.remaining)
    if (over) {
      toast.warning(t("{name}: only {remaining} still to receive.", { name: over.medicine_name, remaining: over.remaining }))
      return
    }
    setSaving(true)
    try {
      await api.procurement.purchases.receive(
        receiving.id,
        {
          reference: receipt.reference.trim(),
          receipt_date: today(),
          received_by: receipt.received_by.trim(),
          items: lines.map((line) => ({
            purchase_item: line.purchase_item,
            quantity_received: Number(line.quantity_received),
            batch: line.batch.trim(),
            expiry_date: line.expiry_date || null,
          })),
        },
        hospital.id,
      )
      toast.success(t("Goods received against {reference}. Stock updated.", { reference: receiving.reference }))
      setReceiving(null)
      onChanged()
    } catch (err) {
      toast.error(err.message || "Could not record the receipt.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      {canEdit && orders.length > 0 && (
        <div className="flex justify-end border-b border-line px-4 py-3">
          <Button size="sm" icon={Plus} onClick={startOrder} disabled={activeSuppliers.length === 0}>{t("New purchase order")}</Button>
        </div>
      )}
      {orders.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title={t("No purchase orders yet")}
          description={activeSuppliers.length ? t("Raise an order to a supplier, then receive the goods here.") : t("Add a supplier first.")}
          action={canEdit && activeSuppliers.length > 0 && <Button icon={Plus} onClick={startOrder}>{t("New purchase order")}</Button>}
        />
      ) : (
        <TableWrap>
          <table className="hms-table">
            <caption className="sr-only">{t("Purchase orders of")}{" "}{hospital.name}</caption>
            <thead>
              <tr>
                <th scope="col">{t("Reference")}</th>
                <th scope="col">{t("Supplier")}</th>
                <th scope="col">{t("Date")}</th>
                <th scope="col">{t("Items")}</th>
                <th scope="col" className="num">{t("Total")}</th>
                <th scope="col">{t("Status")}</th>
                {canEdit && <th scope="col"><span className="sr-only">{t("Actions")}</span></th>}
              </tr>
            </thead>
            <tbody>
              {orders.map((purchase) => (
                <tr key={purchase.id}>
                  <td className="font-medium text-ink-900">{purchase.reference}</td>
                  <td className="text-ink-600">{purchase.supplier_name}</td>
                  <td className="whitespace-nowrap tabular-nums text-ink-600">{new Date(purchase.purchase_date).toLocaleDateString("en-IN")}</td>
                  <td className="text-ink-600">
                    {(purchase.items || []).map((line) => `${line.medicine_name} ${line.quantity_received}/${line.quantity_ordered}`).join(", ") || "—"}
                  </td>
                  <td className="num">{money(orderTotal(purchase))}</td>
                  <td><StatusBadge status={purchase.status} /></td>
                  {canEdit && (
                    <td>
                      <div className="flex justify-end">
                        {RECEIVABLE.includes(purchase.status) && (purchase.items || []).length > 0 && (
                          <Button size="sm" variant="subtle" icon={PackageCheck} onClick={() => startReceipt(purchase)}>{t("Receive")}</Button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}

      <Modal
        open={creating}
        onClose={() => setCreating(false)}
        size="lg"
        title={t("New purchase order")}
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreating(false)}>{t("Cancel")}</Button>
            <Button type="submit" form="po-form" loading={saving}>{t("Raise order")}</Button>
          </>
        }
      >
        <form id="po-form" onSubmit={createOrder} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field label="Supplier" required>
              <Select value={order.supplier} onChange={(e) => setOrder({ ...order, supplier: e.target.value })}>
                {activeSuppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </Field>
            <Field label="Order reference" required>
              <Input value={order.reference} onChange={(e) => setOrder({ ...order, reference: e.target.value })} placeholder={t("e.g. PO-2026-014")} />
            </Field>
            <Field label="Order date" required>
              <Input type="date" value={order.purchase_date} onChange={(e) => setOrder({ ...order, purchase_date: e.target.value })} />
            </Field>
          </div>
          <fieldset className="space-y-3">
            <legend className="hms-label">{t("Items")}</legend>
            {order.lines.map((line, index) => (
              <div key={index} className="grid grid-cols-[1fr_6rem_7rem_auto] items-end gap-2">
                <Field label={`Item ${index + 1}`}>
                  <Select value={line.medicine} onChange={(e) => setLine(index, "medicine", e.target.value)}>
                    <option value="">{t("Select item")}</option>
                    {medicines.map((m) => <option key={m.apiId} value={m.apiId}>{m.name}{m.batch ? ` (${m.batch})` : ""}</option>)}
                  </Select>
                </Field>
                <Field label="Qty">
                  <Input type="number" min="1" inputMode="numeric" value={line.quantity_ordered} onChange={(e) => setLine(index, "quantity_ordered", e.target.value)} />
                </Field>
                <Field label="Unit cost (₹)">
                  <Input type="number" min="0" step="0.01" inputMode="decimal" value={line.unit_cost} onChange={(e) => setLine(index, "unit_cost", e.target.value)} />
                </Field>
                <Button
                  variant="danger-ghost"
                  size="icon-sm"
                  icon={Trash2}
                  aria-label={t("Remove item {number}", { number: index + 1 })}
                  disabled={order.lines.length === 1}
                  onClick={() => setOrder({ ...order, lines: order.lines.filter((_, i) => i !== index) })}
                />
              </div>
            ))}
            <Button size="sm" variant="secondary" icon={Plus} onClick={() => setOrder({ ...order, lines: [...order.lines, emptyLine()] })}>{t("Add item")}</Button>
          </fieldset>
        </form>
      </Modal>

      <Modal
        open={Boolean(receiving)}
        onClose={() => setReceiving(null)}
        size="lg"
        title={t("Receive goods — {reference}", { reference: receiving?.reference || "" })}
        description={receiving?.supplier_name}
        footer={
          <>
            <Button variant="secondary" onClick={() => setReceiving(null)}>{t("Cancel")}</Button>
            <Button type="submit" form="grn-form" loading={saving}>{t("Record receipt")}</Button>
          </>
        }
      >
        <form id="grn-form" onSubmit={receiveGoods} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Supplier invoice / delivery note no." required hint="Recording the same number twice is refused, so stock is never added twice.">
              <Input value={receipt.reference} onChange={(e) => setReceipt({ ...receipt, reference: e.target.value })} />
            </Field>
            <Field label="Received by">
              <Input value={receipt.received_by} onChange={(e) => setReceipt({ ...receipt, received_by: e.target.value })} />
            </Field>
          </div>
          {receipt.lines.map((line, index) => (
            <div key={line.purchase_item} className="grid grid-cols-1 gap-2 rounded-lg border border-line p-3 sm:grid-cols-[1fr_6rem_7rem_9rem]">
              <div className="text-sm">
                <span className="block font-medium text-ink-900">{line.medicine_name}</span>
                <span className="text-xs text-ink-500">{line.remaining}{" "}{t("still to receive")}</span>
              </div>
              <Field label="Qty now">
                <Input type="number" min="0" max={line.remaining} inputMode="numeric" value={line.quantity_received} onChange={(e) => setReceiptLine(index, "quantity_received", e.target.value)} />
              </Field>
              <Field label="Batch">
                <Input value={line.batch} onChange={(e) => setReceiptLine(index, "batch", e.target.value)} />
              </Field>
              <Field label="Expiry">
                <Input type="date" value={line.expiry_date} onChange={(e) => setReceiptLine(index, "expiry_date", e.target.value)} />
              </Field>
            </div>
          ))}
        </form>
      </Modal>
    </>
  )
}
