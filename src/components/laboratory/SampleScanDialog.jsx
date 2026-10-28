import { useState } from "react"
import { ScanLine } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, Field, Input, Modal, StatusBadge } from "../ui"

// Barcode scan (F6). A USB or Bluetooth scanner types the sample number and
// presses Enter, so the field just needs focus. The found order's next step
// is offered right away.

export default function SampleScanDialog({ open, onClose, nextStepFor, onNextStep }) {
  const [code, setCode] = useState("")
  const [found, setFound] = useState(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const reset = () => {
    setCode("")
    setFound(null)
    setError("")
  }

  const lookUp = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError("")
    setFound(null)
    try {
      setFound(await api.laboratory.tests.bySample(code.trim()))
    } catch (err) {
      setError(err.status === 404 ? `No sample ${code.trim()} at this hospital.` : err.message)
    } finally {
      setBusy(false)
      setCode("")
    }
  }

  const step = found && nextStepFor(found.status)

  return (
    <Modal open={open} onClose={() => { reset(); onClose() }} title="Scan sample" description="Scan the tube's barcode, or type the sample number and press Enter.">
      <form onSubmit={lookUp} className="flex items-end gap-2">
        <Field label="Sample number" className="flex-1">
          <Input value={code} onChange={(e) => setCode(e.target.value)} autoComplete="off" autoFocus placeholder="LAB20261028-1-000001" />
        </Field>
        <Button type="submit" icon={ScanLine} loading={busy} disabled={!code.trim()}>Find</Button>
      </form>
      {error && <Alert tone="danger" className="mt-3">{error}</Alert>}
      {found && (
        <div className="mt-4 space-y-2 rounded-xl border border-line p-4 text-sm">
          <div className="flex items-center justify-between gap-2">
            <p className="font-semibold text-ink-900">{found.patient_name} · {found.name}</p>
            <StatusBadge status={found.status} />
          </div>
          <p className="text-ink-500">Sample {found.sample_collection?.sample_id} · ordered by {found.doctor_name || "—"}</p>
          {step ? (
            <Button loading={busy} onClick={async () => { setBusy(true); try { await onNextStep(found) } finally { setBusy(false); reset() } }}>
              {step}
            </Button>
          ) : (
            <p className="text-ink-500">Nothing more to do for this sample.</p>
          )}
        </div>
      )}
    </Modal>
  )
}
