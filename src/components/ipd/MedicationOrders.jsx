import { useCallback, useEffect, useMemo, useState } from "react"
import { Pill, Plus } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Alert, Button, EmptyState, Field, Input, Modal, Select, StatusBadge, TableWrap, useConfirm } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { hospitalToday } from "../../utils/hospitalDate.js"

// Medicine orders (MAR) of one admission. Only a doctor orders or stops one;
// nurses give doses under active orders from the Nurses page (owner decision,
// 2026-11-05). Each order comes from the patient's own prescription.

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const ROUTES = ["Oral", "IV", "IM", "SC", "Topical", "Inhaled", "Rectal", "Other"]
const EMPTY_FORM = { item: "", dose: "", route: "Oral", frequency: "", end_date: "" }

function useAdmissionOrders(admission, hospitalId, open) {
  const [orders, setOrders] = useState([])
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    if (!open || !admission) return
    setLoading(true)
    setError("")
    try {
      const [marRes, rxRes] = await Promise.all([
        api.nurses.mar.list(hospitalId, null, admission.id),
        api.prescriptions.list({ hospitalId, patientId: admission.patient }),
      ])
      setOrders(list(marRes))
      setItems(list(rxRes).flatMap((rx) => (rx.items || []).map((item) => ({ ...item, prescription: rx.id }))))
    } catch (err) {
      setError(err.message || "Could not load medicine orders.")
    } finally {
      setLoading(false)
    }
  }, [open, admission, hospitalId])

  useEffect(() => {
    load()
  }, [load])

  return { orders, items, loading, error, reload: load }
}

export default function MedicationOrders({ open, onClose, admission, hospitalId, canOrder }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()
  const { orders, items, loading, error, reload } = useAdmissionOrders(admission, hospitalId, open)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState("")

  const itemsById = useMemo(() => Object.fromEntries(items.map((item) => [String(item.id), item])), [items])
  const set = (name) => (event) => setForm((prev) => ({ ...prev, [name]: event.target.value }))

  const pickItem = (event) => {
    const item = itemsById[event.target.value]
    setForm((prev) => ({ ...prev, item: event.target.value, dose: item?.dosage || "", frequency: item?.frequency || "" }))
  }

  const close = () => {
    setForm(EMPTY_FORM)
    setFormError("")
    onClose()
  }

  const submit = async (event) => {
    event.preventDefault()
    const item = itemsById[form.item]
    if (!item || !form.dose.trim() || !form.frequency.trim()) {
      setFormError(t("Choose a medicine and fill in dose and frequency."))
      return
    }
    setSaving(true)
    setFormError("")
    try {
      const order = await api.nurses.mar.create({
        patient: admission.patient, admission: admission.id, hospital: hospitalId,
        prescription: item.prescription, prescription_item: item.id, medicine_name: item.name,
        dose: form.dose.trim(), route: form.route, frequency: form.frequency.trim(),
        start_date: hospitalToday(), end_date: form.end_date || null,
      })
      if (!form.frequency.toUpperCase().includes("PRN")) await api.nurses.mar.generateSchedule(order.id)
      toast.success(t("Medicine ordered. Nurses can now give it."))
      setForm(EMPTY_FORM)
      reload()
    } catch (err) {
      setFormError(err.message || "Could not save the order.")
    } finally {
      setSaving(false)
    }
  }

  const stop = async (order) => {
    const ok = await confirm({
      title: t("Stop this medicine?"),
      message: t("Nurses will not be able to give {medicine} after this.", { medicine: order.medicine_name }),
      confirmLabel: "Stop medicine",
      destructive: true,
    })
    if (!ok) return
    try {
      await api.nurses.mar.stop(order.id)
      toast.success(t("Medicine stopped."))
      reload()
    } catch (err) {
      toast.error(err.message || "Could not stop the medicine.")
    }
  }

  return (
    <Modal open={open} onClose={close} title={t("Medicine orders — {patient}", { patient: admission?.patient_name || "" })} size="lg">
      {error && <Alert tone="danger">{error}</Alert>}
      {!canOrder && (
        <Alert tone="info">{t("Only a doctor can order or stop a medicine. Nurses give doses under active orders from the MAR tab.")}</Alert>
      )}

      {loading ? (
        <p className="py-6 text-sm text-ink-500">{t("Loading…")}</p>
      ) : orders.length === 0 ? (
        <EmptyState icon={Pill} title={t("No medicine ordered yet")} />
      ) : (
        <TableWrap>
          <table className="hms-table">
            <thead>
              <tr>
                <th scope="col">{t("Medicine")}</th>
                <th scope="col">{t("Dose")}</th>
                <th scope="col">{t("Frequency")}</th>
                <th scope="col">{t("Dates")}</th>
                <th scope="col">{t("Ordered by")}</th>
                <th scope="col">{t("Status")}</th>
                {canOrder && <th scope="col"><span className="sr-only">{t("Actions")}</span></th>}
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td className="font-medium text-ink-900">{order.medicine_name}</td>
                  <td className="whitespace-nowrap">{order.dose} · {order.route}</td>
                  <td>{order.frequency}</td>
                  <td className="whitespace-nowrap tabular-nums text-ink-600">{order.start_date}{order.end_date ? ` → ${order.end_date}` : ""}</td>
                  <td>{order.ordered_by_name || <span className="text-ink-400">—</span>}</td>
                  <td><StatusBadge status={order.is_active ? "Active" : "Stopped"} /></td>
                  {canOrder && (
                    <td className="text-right">
                      {order.is_active && <Button size="sm" variant="danger-ghost" onClick={() => stop(order)}>{t("Stop")}</Button>}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}

      {canOrder && (
        <form onSubmit={submit} className="mt-6 space-y-4 border-t border-line pt-5">
          <p className="text-sm font-semibold text-ink-900">{t("Order a medicine")}</p>
          {items.length === 0 ? (
            <p className="text-sm text-ink-500">{t("Write a prescription for this patient first; orders are made from its medicines.")}</p>
          ) : (
            <>
              <Field label="Medicine (from the patient's prescriptions)" required>
                <Select value={form.item} onChange={pickItem}>
                  <option value="">{t("Choose…")}</option>
                  {items.map((item) => (
                    <option key={item.id} value={item.id}>
                      {[item.name, item.dosage, item.frequency].filter(Boolean).join(" · ")} (Rx #{item.prescription})
                    </option>
                  ))}
                </Select>
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Dose" required><Input value={form.dose} onChange={set("dose")} placeholder="500 mg" /></Field>
                <Field label="Route" required>
                  <Select value={form.route} onChange={set("route")}>
                    {ROUTES.map((route) => <option key={route} value={route}>{route}</option>)}
                  </Select>
                </Field>
                <Field label="Frequency" required hint="OD, BID, TID, QID, Q8H or PRN">
                  <Input value={form.frequency} onChange={set("frequency")} placeholder="TID" />
                </Field>
                <Field label="Last day (optional)">
                  <Input type="date" value={form.end_date} min={hospitalToday()} onChange={set("end_date")} />
                </Field>
              </div>
              {formError && <Alert tone="danger">{formError}</Alert>}
              <div className="flex justify-end">
                <Button type="submit" icon={Plus} loading={saving}>{t("Order medicine")}</Button>
              </div>
            </>
          )}
        </form>
      )}
      {confirmDialog}
    </Modal>
  )
}
