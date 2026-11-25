import { useMemo, useState } from "react"
import api from "../../services/api.js"
import { Alert, Button, Field, Input, Modal, Select } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { AMOUNT_FORMAT_ERROR, fromPaise, toPaise } from "../../utils/money.js"

// Money returned on a bill (POST /api/billing/invoices/{id}/refund/). The
// server checks the amount against what was paid and needs a reason; one
// idempotency key per dialog, so a double click never refunds twice.
const METHODS = ["Cash", "UPI", "Card", "Bank Transfer"]

const newKey = () => (globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : `refund-${Date.now()}-${Math.random()}`)

/** Paise to refund, or an error message. `paid` is the bill's net amount received. */
export function refundToRecord(entered, paid) {
  const amount = toPaise(String(entered ?? "").trim())
  const received = toPaise(String(paid ?? "0"))
  if (Number.isNaN(amount) || amount <= 0) return { error: AMOUNT_FORMAT_ERROR }
  if (amount > received) return { error: `At most ₹${fromPaise(received)} can be refunded on this bill.` }
  return { amount: fromPaise(amount) }
}

export default function RefundDialog({ invoice, onClose, onRefunded }) {
  const { t } = useLanguage()
  const [amount, setAmount] = useState("")
  const [reason, setReason] = useState("")
  const [method, setMethod] = useState("Cash")
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)
  const key = useMemo(newKey, [])

  const submit = async (event) => {
    event.preventDefault()
    setError("")
    const checked = refundToRecord(amount, invoice.total_paid)
    if (checked.error) return setError(t(checked.error))
    if (!reason.trim()) return setError(t("Give the reason for the refund."))
    setSaving(true)
    try {
      const refund = await api.billing.invoices.refund(invoice.id, {
        amount: checked.amount, reason: reason.trim(), payment_method: method, idempotency_key: key,
      })
      onRefunded?.(refund)
      onClose()
    } catch (err) {
      setError(err.message || t("The refund was not recorded."))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t("Refund")}
      description={`${invoice.invoice_number} · ${t("received")} ₹${invoice.total_paid}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>{t("Cancel")}</Button>
          <Button type="submit" form="refund-form" variant="danger" loading={saving}>{t("Record refund")}</Button>
        </>
      }
    >
      <form id="refund-form" onSubmit={submit} className="space-y-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="Amount (₹)" htmlFor="refund-amount" required>
          <Input id="refund-amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" />
        </Field>
        <Field label="Reason" htmlFor="refund-reason" required>
          <Input id="refund-reason" value={reason} maxLength={255} onChange={(e) => setReason(e.target.value)} />
        </Field>
        <Field label="Paid back by" htmlFor="refund-method">
          <Select id="refund-method" value={method} onChange={(e) => setMethod(e.target.value)}>
            {METHODS.map((m) => <option key={m} value={m}>{t(m)}</option>)}
          </Select>
        </Field>
      </form>
    </Modal>
  )
}
