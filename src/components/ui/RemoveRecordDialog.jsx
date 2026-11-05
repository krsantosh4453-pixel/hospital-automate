import { useState } from "react"
import { ConfirmDialog } from "./Modal.jsx"
import { Field, Textarea } from "./Field.jsx"
import { useT } from "./useT.js"

// Matches MIN_REASON_LENGTH in backend/audit/entered_in_error.py.
export const MIN_REMOVAL_REASON = 5

/**
 * Remove a clinical record or patient. Nothing is erased: the server marks it
 * entered in error and keeps who removed it, when and why (R-03).
 * ``onConfirm`` receives the reason.
 */
export function RemoveRecordDialog({ open, onCancel, onConfirm, title, message, loading = false, confirmDisabled = false, children }) {
  const tr = useT()
  const [reason, setReason] = useState("")
  const tooShort = reason.trim().length < MIN_REMOVAL_REASON

  const close = () => {
    setReason("")
    onCancel()
  }
  const confirm = async () => {
    await onConfirm(reason.trim())
    setReason("")
  }

  return (
    <ConfirmDialog
      open={open}
      onCancel={close}
      onConfirm={confirm}
      loading={loading}
      destructive
      title={title}
      confirmLabel="Remove"
      confirmDisabled={tooShort || confirmDisabled}
      message={message}
    >
      <p className="mt-2 text-[13px] text-ink-500">
        {tr("The record is hidden, not erased. Your name, the time and the reason are kept.")}
      </p>
      <Field label="Why was this entered in error?" required className="mt-4">
        <Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} placeholder={tr("e.g. Recorded for the wrong patient")} />
      </Field>
      {children}
    </ConfirmDialog>
  )
}

export default RemoveRecordDialog
