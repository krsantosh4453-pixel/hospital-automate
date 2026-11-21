import { useCallback, useEffect, useMemo, useState } from "react"
import { Pill, Plus } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Alert, Button, EmptyState, Field, Input, Modal, Select, StatusBadge, TableWrap, useConfirm, usePrompt } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { hospitalToday } from "../../utils/hospitalDate.js"
import { isPrnFrequency, prnLimitText } from "../../utils/prnLimits.js"

// Medicine orders (MAR) of one admission. Only a doctor orders or stops one;
// nurses give scheduled doses from the Nurses page (owner decision,
// 2026-11-05) and as-needed (PRN) doses here. Each order comes from the
// patient's own prescription. H-10: a PRN order may carry a minimum time
// between doses and a 24-hour maximum, enforced by the server.

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const ROUTES = ["Oral", "IV", "IM", "SC", "Topical", "Inhaled", "Rectal", "Other"]
// first_dose: the server places the first dose (nurses/scheduling.py) and never in the past.
const EMPTY_FORM = {
  item: "", dose: "", route: "Oral", frequency: "", end_date: "", first_dose: "next_round", first_dose_at: "",
  prn_interval_hours: "", prn_max_doses: "",
}

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

export default function MedicationOrders({ open, onClose, admission, hospitalId, canOrder, canGive = false }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()
  const [promptText, promptDialog] = usePrompt()
  const [givingId, setGivingId] = useState(null)
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
    const prn = isPrnFrequency(form.frequency)
    const intervalHours = prn && form.prn_interval_hours !== "" ? Number(form.prn_interval_hours) : null
    const maxDoses = prn && form.prn_max_doses !== "" ? Number(form.prn_max_doses) : null
    if ((intervalHours !== null && !(intervalHours > 0)) || (maxDoses !== null && !Number.isInteger(maxDoses))) {
      setFormError(t("Enter the dose limits as numbers, or leave them empty."))
      return
    }
    setSaving(true)
    setFormError("")
    try {
      await api.nurses.mar.create({
        patient: admission.patient, admission: admission.id, hospital: hospitalId,
        prescription: item.prescription, prescription_item: item.id, medicine_name: item.name,
        dose: form.dose.trim(), route: form.route, frequency: form.frequency.trim(),
        start_date: hospitalToday(), end_date: form.end_date || null,
        // Scheduled with the order in one transaction; a refused time leaves no order behind.
        first_dose: form.first_dose,
        ...(form.first_dose === "at" ? { first_dose_at: form.first_dose_at } : {}),
        ...(prn
          ? {
              prn_min_interval_minutes: intervalHours === null ? null : Math.round(intervalHours * 60),
              prn_max_doses_per_24h: maxDoses,
            }
          : {}),
      })
      toast.success(t("Medicine ordered. Nurses can now give it."))
      setForm(EMPTY_FORM)
      reload()
    } catch (err) {
      setFormError(err.message || "Could not save the order.")
    } finally {
      setSaving(false)
    }
  }

  const givePrn = async (order) => {
    const notes = await promptText({
      title: t("Give {medicine} now", { medicine: order.medicine_name }),
      label: t("Reason or note (optional)"),
      confirmLabel: t("Record dose"),
    })
    if (notes === null) return
    setGivingId(order.id)
    try {
      await api.nurses.mar.givePrn(order.id, notes.trim())
      toast.success(t("Dose recorded."))
      reload()
    } catch (err) {
      // H-10: a dose inside the minimum interval or over the daily maximum is refused.
      toast.error(err.message || "The dose was not recorded.")
    } finally {
      setGivingId(null)
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
      {canGive && (
        <Alert tone="info">{t("As-needed (PRN) medicines are given here with Give dose.")}</Alert>
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
                {(canOrder || canGive) && <th scope="col"><span className="sr-only">{t("Actions")}</span></th>}
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td className="font-medium text-ink-900">{order.medicine_name}</td>
                  <td className="whitespace-nowrap">{order.dose} · {order.route}</td>
                  <td>
                    {order.frequency}
                    {prnLimitText(order, t) && <span className="block text-xs text-ink-500">{prnLimitText(order, t)}</span>}
                  </td>
                  <td className="whitespace-nowrap tabular-nums text-ink-600">{order.start_date}{order.end_date ? ` → ${order.end_date}` : ""}</td>
                  <td>{order.ordered_by_name || <span className="text-ink-400">—</span>}</td>
                  <td><StatusBadge status={order.is_active ? "Active" : "Stopped"} /></td>
                  {(canOrder || canGive) && (
                    <td className="text-right whitespace-nowrap">
                      {canGive && order.is_active && isPrnFrequency(order.frequency) && (
                        <Button size="sm" variant="subtle" loading={givingId === order.id} onClick={() => givePrn(order)}>{t("Give dose")}</Button>
                      )}
                      {canOrder && order.is_active && <Button size="sm" variant="danger-ghost" onClick={() => stop(order)}>{t("Stop")}</Button>}
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
                <Field label="First dose" required>
                  <Select value={form.first_dose} onChange={set("first_dose")}>
                    <option value="next_round">{t("Next medication round")}</option>
                    <option value="now">{t("Start now")}</option>
                    <option value="at">{t("Specific time")}</option>
                  </Select>
                </Field>
                {form.first_dose === "at" && (
                  <Field label="First dose time" required>
                    <Input type="datetime-local" value={form.first_dose_at} onChange={set("first_dose_at")} />
                  </Field>
                )}
                {isPrnFrequency(form.frequency) && (
                  <>
                    <Field label="Minimum hours between doses (optional)" hint="Empty means no limit">
                      <Input type="number" min="0.25" step="0.25" value={form.prn_interval_hours} onChange={set("prn_interval_hours")} placeholder="4" />
                    </Field>
                    <Field label="Most doses in 24 hours (optional)" hint="Empty means no limit">
                      <Input type="number" min="1" max="48" step="1" value={form.prn_max_doses} onChange={set("prn_max_doses")} placeholder="4" />
                    </Field>
                  </>
                )}
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
      {promptDialog}
    </Modal>
  )
}
