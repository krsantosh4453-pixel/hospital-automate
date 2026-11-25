import { useEffect, useState } from "react"
import api from "../../services/api.js"
import { Alert, Button, Field, Input, Modal, Select, Textarea } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { hospitalToday } from "../../utils/hospitalDate.js"

// Prompt 5 (MF-003): a patient cancels or moves their own booking. Every rule
// (window, working days, free slots, capacity) is the server's; this dialog
// only offers what booking-options returns and shows the server's answer.

/** A booking the patient may still change online: Scheduled and not yet started. */
export function canManageOnline(appointment, now = new Date()) {
  if (!appointment || appointment.status !== "Scheduled" || !appointment.appointment_date) return false
  const at = new Date(`${appointment.appointment_date}T${String(appointment.appointment_time || "00:00").slice(0, 5)}`)
  return at.getTime() > now.getTime()
}

function describe(appointment, t) {
  return `${appointment.doctor_name || t("Doctor")} · ${appointment.appointment_date} ${String(appointment.appointment_time || "").slice(0, 5)}`
}

function CancelDialog({ appointment, onDone, onClose }) {
  const { t } = useLanguage()
  const [reason, setReason] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  const submit = async () => {
    setSaving(true)
    setError("")
    try {
      onDone(await api.appointments.selfCancel(appointment.id, reason.trim()), "cancelled")
    } catch (err) {
      setError(err.message || t("The appointment could not be cancelled."))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t("Cancel appointment")}
      description={describe(appointment, t)}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>{t("Keep appointment")}</Button>
          <Button variant="danger" onClick={submit} loading={saving}>{t("Cancel appointment")}</Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="Reason (optional)" htmlFor="cancel-reason">
          <Textarea id="cancel-reason" value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
        </Field>
      </div>
    </Modal>
  )
}

function RescheduleDialog({ appointment, onDone, onClose }) {
  const { t } = useLanguage()
  const [date, setDate] = useState(appointment.appointment_date)
  const [time, setTime] = useState("")
  const [slots, setSlots] = useState([])
  const [reason, setReason] = useState("")
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setTime("")
    setError("")
    api.appointments
      .bookingOptions({ hospital: appointment.hospital, doctor: appointment.doctor, date })
      .then((data) => {
        if (cancelled) return
        setSlots((data.slots || []).filter((slot) => slot.available))
        setReason(data.unavailable_reason || "")
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [appointment.hospital, appointment.doctor, date])

  const submit = async () => {
    setSaving(true)
    setError("")
    try {
      onDone(await api.appointments.selfReschedule(appointment.id, { appointment_date: date, appointment_time: time }), "moved")
    } catch (err) {
      // The booking is unchanged on the server when a move is refused.
      setError(err.message || t("The appointment could not be moved."))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t("Reschedule appointment")}
      description={describe(appointment, t)}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>{t("Close")}</Button>
          <Button onClick={submit} loading={saving} disabled={!date || !time}>{t("Move appointment")}</Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="New date" htmlFor="move-date" required>
          <Input id="move-date" type="date" value={date} min={hospitalToday()} onChange={(e) => setDate(e.target.value)} />
        </Field>
        {reason && <Alert tone="warning">{reason}</Alert>}
        <Field label="New time" htmlFor="move-time" required
          hint={!loading && !reason && slots.length === 0 ? t("No free time on this day. Try another date.") : undefined}>
          <Select id="move-time" value={time} onChange={(e) => setTime(e.target.value)} disabled={loading || slots.length === 0}>
            <option value="">{loading ? t("Loading free times…") : t("Select time")}</option>
            {slots.map((slot) => <option key={slot.time} value={slot.time}>{slot.time}</option>)}
          </Select>
        </Field>
      </div>
    </Modal>
  )
}

/** mode: "cancel" | "reschedule". onChanged(updatedAppointment, what) after the server accepts. */
export default function ManageAppointmentDialog({ appointment, mode, onClose, onChanged }) {
  if (!appointment || !mode) return null
  const done = (updated, what) => {
    onChanged?.(updated, what)
    onClose()
  }
  const Dialog = mode === "cancel" ? CancelDialog : RescheduleDialog
  // Keyed so a new booking or mode always starts from a fresh form.
  return <Dialog key={`${mode}-${appointment.id}`} appointment={appointment} onDone={done} onClose={onClose} />
}
