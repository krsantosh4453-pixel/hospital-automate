import { useCallback, useEffect, useMemo, useState } from "react"
import { ChevronDown, ChevronRight, Wallet } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Alert, Button, Card, CardHeader, EmptyState, Field, Input, Modal, Select, StatusBadge, TableWrap } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import PatientPicker from "../patients/PatientPicker.jsx"

// Advance payments (H4): money a patient deposits before or during care,
// adjusted against bills or refunded. The server keeps the balance and the
// ledger; this card only sends one movement at a time, each with its own
// idempotency key so a double click cannot count twice.

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const rupees = (value) => `₹${Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
const newKey = () => `adv-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
const METHODS = ["Cash", "UPI", "Card", "Bank Transfer"]
const KIND_LABELS = { deposit: "Deposit", applied: "Applied to bill", returned: "Returned from bill", refund: "Refunded to patient" }

function useAdvanceAccounts(hospitalId, reloadToken) {
  const [accounts, setAccounts] = useState([])
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!hospitalId) return undefined
    let cancelled = false
    setLoading(true)
    api.billing.advances.list(hospitalId)
      .then((data) => !cancelled && (setAccounts(list(data)), setError("")))
      .catch((err) => !cancelled && setError(err.message || "Could not load advance payments."))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [hospitalId, reloadToken])

  return { accounts, error, loading }
}

export default function AdvancePayments({ hospitalId, canRefund, onChanged }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [reloadToken, setReloadToken] = useState(0)
  const { accounts, error, loading } = useAdvanceAccounts(hospitalId, reloadToken)
  const [dialog, setDialog] = useState(null) // { type: "deposit" | "adjust" | "refund", account? }
  const [form, setForm] = useState({})
  const [invoices, setInvoices] = useState([])
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState("")
  const [open, setOpen] = useState(null)

  const set = (name) => (event) => setForm((prev) => ({ ...prev, [name]: event.target.value }))
  const close = () => {
    setDialog(null)
    setFormError("")
  }
  const start = (type, account = null) => {
    setForm({ key: newKey(), amount: "", payment_method: "Cash", reference: "", reason: "", invoice: "", patient: account?.patient ? { id: account.patient, name: account.patient_name } : null })
    setFormError("")
    setDialog({ type, account })
  }

  // Bills of this patient that still have something to pay.
  const loadInvoices = useCallback(async (account) => {
    try {
      const data = await api.billing.invoices.list(hospitalId)
      setInvoices(list(data).filter((inv) => inv.patient === account.patient && inv.status !== "Cancelled" && Number(inv.balance_due) > 0))
    } catch (err) {
      setFormError(err.message || "Could not load this patient's bills.")
    }
  }, [hospitalId])

  useEffect(() => {
    if (dialog?.type === "adjust") loadInvoices(dialog.account)
  }, [dialog, loadInvoices])

  const done = (message) => {
    toast.success(t(message))
    close()
    setReloadToken((n) => n + 1)
    onChanged?.()
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!(Number(form.amount) > 0)) {
      setFormError(t("Enter an amount greater than zero."))
      return
    }
    setSaving(true)
    setFormError("")
    try {
      if (dialog.type === "deposit") {
        if (!form.patient) throw new Error(t("Choose the patient."))
        await api.billing.advances.deposit({ hospital: hospitalId, patient: form.patient.id, amount: form.amount,
          payment_method: form.payment_method, reference: form.reference, idempotency_key: form.key })
        done("Advance received.")
      } else if (dialog.type === "adjust") {
        if (!form.invoice) throw new Error(t("Choose the bill."))
        await api.billing.advances.applyToInvoice(form.invoice, { amount: form.amount, idempotency_key: form.key })
        done("Advance adjusted against the bill.")
      } else {
        await api.billing.advances.refund(dialog.account.id, { amount: form.amount, reason: form.reason,
          payment_method: form.payment_method, idempotency_key: form.key })
        done("Advance refunded.")
      }
    } catch (err) {
      setFormError(err.message || "Could not save.")
    } finally {
      setSaving(false)
    }
  }

  const selectedInvoice = useMemo(() => invoices.find((inv) => String(inv.id) === String(form.invoice)), [invoices, form.invoice])
  const titles = { deposit: "Receive advance", adjust: "Adjust advance against a bill", refund: "Refund advance" }

  return (
    <Card className="mb-6">
      <CardHeader
        title="Advance payments"
        description="Deposits held for patients, adjusted against their bills."
        actions={<Button size="sm" icon={Wallet} onClick={() => start("deposit")}>{t("Receive advance")}</Button>}
      />
      {error && <Alert tone="danger" className="mx-5 mb-4">{error}</Alert>}
      {loading ? (
        <p className="px-5 pb-5 text-sm text-ink-500">{t("Loading…")}</p>
      ) : accounts.length === 0 ? (
        <EmptyState compact icon={Wallet} title={t("No advance payments yet")} />
      ) : (
        <TableWrap>
          <table className="hms-table">
            <thead>
              <tr>
                <th scope="col">{t("Patient")}</th>
                <th scope="col" className="text-right">{t("Balance")}</th>
                <th scope="col"><span className="sr-only">{t("Actions")}</span></th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <AccountRows key={account.id} account={account} expanded={open === account.id}
                  onToggle={() => setOpen(open === account.id ? null : account.id)}
                  onAdjust={() => start("adjust", account)} onRefund={canRefund ? () => start("refund", account) : null} />
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}

      <Modal open={Boolean(dialog)} onClose={close} title={t(titles[dialog?.type] || "")} size="md"
        footer={<><Button variant="secondary" onClick={close}>{t("Cancel")}</Button><Button type="submit" form="advance-form" loading={saving}>{t("Save")}</Button></>}>
        <form id="advance-form" onSubmit={submit} className="space-y-4">
          {dialog?.type === "deposit" ? (
            <Field label="Patient" required>
              <PatientPicker hospitalId={hospitalId} value={form.patient ? String(form.patient.id) : ""} selected={form.patient}
                onChange={(id, patient) => setForm((prev) => ({ ...prev, patient }))} />
            </Field>
          ) : (
            <p className="text-sm text-ink-700">
              {dialog?.account?.patient_name} · {t("Advance balance")}: <strong>{rupees(dialog?.account?.balance)}</strong>
            </p>
          )}
          {dialog?.type === "adjust" && (
            <Field label="Bill" required hint={selectedInvoice ? t("Due on this bill: {due}", { due: rupees(selectedInvoice.balance_due) }) : undefined}>
              <Select value={form.invoice} onChange={set("invoice")}>
                <option value="">{invoices.length ? t("Choose…") : t("No unpaid bills for this patient")}</option>
                {invoices.map((inv) => <option key={inv.id} value={inv.id}>{inv.invoice_number} · {t("due")} {rupees(inv.balance_due)}</option>)}
              </Select>
            </Field>
          )}
          <Field label="Amount (₹)" required><Input type="number" min="0.01" step="0.01" value={form.amount || ""} onChange={set("amount")} /></Field>
          {dialog?.type !== "adjust" && (
            <Field label={dialog?.type === "refund" ? "Paid back by" : "Received by"} required>
              <Select value={form.payment_method || "Cash"} onChange={set("payment_method")}>
                {METHODS.map((method) => <option key={method} value={method}>{t(method)}</option>)}
              </Select>
            </Field>
          )}
          {dialog?.type === "deposit" && <Field label="Reference (optional)"><Input value={form.reference || ""} onChange={set("reference")} placeholder={t("UPI or cheque reference")} /></Field>}
          {dialog?.type === "refund" && <Field label="Reason" required><Input value={form.reason || ""} onChange={set("reason")} placeholder={t("e.g. Discharged, unused advance")} /></Field>}
          {formError && <Alert tone="danger">{formError}</Alert>}
        </form>
      </Modal>
    </Card>
  )
}

function AccountRows({ account, expanded, onToggle, onAdjust, onRefund }) {
  const { t } = useLanguage()
  const hasBalance = Number(account.balance) > 0
  return (
    <>
      <tr>
        <td>
          <button type="button" onClick={onToggle} className="flex items-center gap-1 font-medium text-ink-900" aria-expanded={expanded}>
            {expanded ? <ChevronDown size={14} aria-hidden="true" /> : <ChevronRight size={14} aria-hidden="true" />}
            {account.patient_name}
          </button>
        </td>
        <td className="text-right font-semibold tabular-nums">{rupees(account.balance)}</td>
        <td>
          <div className="flex justify-end gap-1.5">
            {hasBalance && <Button size="sm" variant="subtle" onClick={onAdjust}>{t("Adjust against bill")}</Button>}
            {hasBalance && onRefund && <Button size="sm" variant="ghost" onClick={onRefund}>{t("Refund")}</Button>}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={3} className="bg-ink-50/60">
            <ul className="space-y-1 text-[13px]">
              {account.transactions.map((move) => (
                <li key={move.id} className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
                  <StatusBadge status={t(KIND_LABELS[move.kind] || move.kind)} />
                  <span className="tabular-nums">{rupees(move.amount)}</span>
                  {move.invoice_number && <span className="text-ink-600">{move.invoice_number}</span>}
                  <span className="text-ink-500">{move.receipt_number}</span>
                  <span className="text-ink-500">{new Date(move.created_at).toLocaleString("en-IN")}</span>
                  <span className="text-ink-500">{move.created_by_name}</span>
                  {move.reference && <span className="text-ink-600">— {move.reference}</span>}
                </li>
              ))}
            </ul>
          </td>
        </tr>
      )}
    </>
  )
}
