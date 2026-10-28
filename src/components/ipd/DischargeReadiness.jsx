import { useEffect, useRef, useState } from "react"
import { CircleCheck, CircleDashed, ReceiptIndianRupee } from "lucide-react"
import api from "../../services/api.js"

// Discharge checklist (E7) and final-bill state (E12, H8) of one admission.
// The server decides readiness; this panel shows it and ticks checklist items.
// onChange(readiness) lets the page enable "Complete discharge".

export default function DischargeReadiness({ admissionId, reloadToken, canTick, onChange }) {
  const [state, setState] = useState(null)
  const [error, setError] = useState("")
  const [saving, setSaving] = useState("")
  // Pages pass onChange inline; a ref keeps it out of the effect's inputs.
  const onChangeRef = useRef(onChange)
  useEffect(() => {
    onChangeRef.current = onChange
  })

  const show = (data) => {
    setState(data)
    onChangeRef.current?.(data)
  }

  useEffect(() => {
    let cancelled = false
    api.ipd.admissions
      .readiness(admissionId)
      .then((data) => !cancelled && show(data))
      .catch((err) => !cancelled && setError(err.message || "Could not load the discharge checklist."))
    return () => {
      cancelled = true
    }
  }, [admissionId, reloadToken])

  const tick = async (item) => {
    if (!state?.plan) return
    setSaving(item.field)
    setError("")
    try {
      await api.ipd.dischargePlans.patch(state.plan, { [item.field]: !item.done })
      show(await api.ipd.admissions.readiness(admissionId))
    } catch (err) {
      setError(err.message || "Could not update the checklist.")
    } finally {
      setSaving("")
    }
  }

  if (error) return <p className="text-[13px] text-red-700">{error}</p>
  if (!state) return <p className="text-[13px] text-ink-500">Loading checklist…</p>

  const bill = state.final_invoice
  const billDone = bill && Number(bill.balance_due) <= 0

  return (
    <div className="space-y-2 text-[13px]">
      <fieldset>
        <legend className="mb-1 font-medium text-ink-700">Discharge checklist</legend>
        <ul className="flex flex-wrap gap-x-4 gap-y-1.5">
          {state.checklist.map((item) => (
            <li key={item.field}>
              <label className={`flex items-center gap-1.5 ${item.done ? "text-green-700" : "text-ink-600"}`}>
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-brand-600"
                  checked={item.done}
                  disabled={!canTick || !state.plan || saving === item.field}
                  onChange={() => tick(item)}
                />
                {item.label}
              </label>
            </li>
          ))}
        </ul>
      </fieldset>
      <p className={`flex items-center gap-1.5 ${billDone ? "text-green-700" : "text-ink-600"}`}>
        <ReceiptIndianRupee size={15} aria-hidden="true" />
        {bill
          ? `Final bill ${bill.invoice_number}: ₹${bill.total}${billDone ? ", paid" : `, ₹${bill.balance_due} due`}`
          : "Final bill not created yet (Billing creates it)"}
      </p>
      <p className={`flex items-center gap-1.5 font-medium ${state.ready ? "text-green-700" : "text-ink-600"}`}>
        {state.ready ? <CircleCheck size={15} aria-hidden="true" /> : <CircleDashed size={15} aria-hidden="true" />}
        {state.ready ? "Ready to complete" : `${state.blockers.length} step(s) left`}
      </p>
    </div>
  )
}
