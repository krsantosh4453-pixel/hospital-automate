import { useState } from "react"
import { Button, Alert, Field, Modal, Textarea } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// Matches MIN_OVERRIDE_REASON in backend/clinical/serializers.py.
export const MIN_OVERRIDE_REASON = 10

const SEVERITY = {
  high: { label: "High risk", tone: "danger" },
  moderate: { label: "Caution", tone: "warning" },
  info: { label: "Note", tone: "info" },
}

/**
 * Medication safety alerts shown before a prescription is saved. High-risk alerts
 * need a written reason, which the server stores and audits with the prescription.
 *
 * @param {{
 *   result: { alerts: object[], review_status: string } | null,
 *   saving: boolean,
 *   onCancel: () => void,
 *   onConfirm: (reason: string) => void,
 * }} props
 */
export default function MedicationSafetyDialog({ result, saving, onCancel, onConfirm }) {
  const { t } = useLanguage()
  const [reason, setReason] = useState("")
  const alerts = result?.alerts || []
  const hasHigh = alerts.some((alert) => alert.severity === "high")
  const reasonOk = !hasHigh || reason.trim().length >= MIN_OVERRIDE_REASON

  const close = () => {
    setReason("")
    onCancel()
  }

  return (
    <Modal
      open={Boolean(result)}
      onClose={close}
      size="lg"
      title={hasHigh ? "High-risk medication alert" : "Medication check"}
      description="Checked against this patient's recorded allergies, the other medicines on this prescription and the hospital's interaction list."
      footer={
        <>
          <Button variant="secondary" onClick={close}>{t("Go back and change")}</Button>
          <Button
            variant={hasHigh ? "danger" : "primary"}
            loading={saving}
            disabled={!reasonOk}
            onClick={() => onConfirm(reason.trim())}
          >
            {hasHigh ? "Prescribe anyway" : "Save prescription"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <ul className="space-y-2">
          {alerts.map((alert, index) => {
            const style = SEVERITY[alert.severity] || SEVERITY.info
            return (
              <li key={`${alert.rule || alert.type}-${index}`}>
                <Alert tone={style.tone} title={`${style.label}: ${alert.medicines.join(" + ")}`}>
                  {alert.message}
                </Alert>
              </li>
            )
          })}
        </ul>
        {hasHigh && (
          <Field
            label="Reason to prescribe anyway"
            required
            hint={t("At least {MIN_OVERRIDE_REASON} characters. Saved with the prescription and in the audit log.", { MIN_OVERRIDE_REASON })}
          >
            <Textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
        )}
        <p className="text-xs text-ink-500">
          {result?.review_status}{t(". This is not a complete interaction check; use clinical judgement.")}
        </p>
      </div>
    </Modal>
  )
}
