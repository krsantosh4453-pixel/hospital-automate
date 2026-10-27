import { useEffect, useState } from "react"
import api from "../../services/api.js"
import { Alert, Button, Field, Modal, Select, Textarea, Input } from "../../components/ui"

/** Today's date in the browser's time zone, as YYYY-MM-DD. */
function todayIso(offsetDays = 0) {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

/**
 * Patient self-booking: hospital → doctor → date → free slot. The server
 * re-checks every rule (own hospital, date window, free slot, booking limit).
 */
function BookAppointmentModal({ open, onClose, onBooked }) {
  const [options, setOptions] = useState({ hospitals: [], doctors: [], slots: [], window_days: 60 })
  const [form, setForm] = useState({ hospital: "", doctor: "", date: todayIso(1), time: "", reason: "" })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [refresh, setRefresh] = useState(0)

  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  useEffect(() => {
    if (!open) return
    setError("")
    api.appointments
      .bookingOptions()
      .then((data) => {
        setOptions((prev) => ({ ...prev, ...data }))
        if (data.hospitals?.length === 1) set("hospital", String(data.hospitals[0].id))
      })
      .catch((e) => setError(e.message))
  }, [open])

  useEffect(() => {
    if (!open || !form.hospital) return
    set("doctor", "")
    api.appointments
      .bookingOptions({ hospital: form.hospital })
      .then((data) => setOptions((prev) => ({ ...prev, doctors: data.doctors || [], slots: [] })))
      .catch((e) => setError(e.message))
  }, [open, form.hospital])

  useEffect(() => {
    if (!open || !form.hospital || !form.doctor || !form.date) return
    set("time", "")
    setLoading(true)
    api.appointments
      .bookingOptions({ hospital: form.hospital, doctor: form.doctor, date: form.date })
      .then((data) => setOptions((prev) => ({ ...prev, slots: data.slots || [] })))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [open, form.hospital, form.doctor, form.date, refresh])

  const freeSlots = options.slots.filter((s) => s.available)

  const submit = async () => {
    setError("")
    setSaving(true)
    try {
      const appointment = await api.appointments.book({
        doctor: form.doctor,
        appointment_date: form.date,
        appointment_time: form.time,
        reason: form.reason,
      })
      onBooked?.(appointment)
      onClose()
    } catch (e) {
      setError(e.message)
      // The slot may have just been taken: reload the free times.
      if (e.status === 409) setRefresh((n) => n + 1)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Book an appointment"
      description="Choose a doctor, a date and a free time."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving} disabled={!form.doctor || !form.date || !form.time}>
            Confirm booking
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <Alert tone="danger">{error}</Alert>}
        {options.hospitals.length === 0 && !error && (
          <Alert tone="warning">You are not registered at any hospital yet. Please register at the reception first.</Alert>
        )}
        <Field label="Hospital" required>
          <Select value={form.hospital} onChange={(e) => set("hospital", e.target.value)}>
            <option value="">Select hospital</option>
            {options.hospitals.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Doctor" required>
          <Select value={form.doctor} onChange={(e) => set("doctor", e.target.value)} disabled={!form.hospital}>
            <option value="">Select doctor</option>
            {options.doctors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} — {d.specialization}
                {d.availability ? ` (${d.availability})` : ""}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Date" required>
          <Input
            type="date"
            value={form.date}
            min={todayIso(0)}
            max={todayIso(options.window_days || 60)}
            onChange={(e) => set("date", e.target.value)}
          />
        </Field>
        <Field
          label="Time"
          required
          hint={form.doctor && !loading && freeSlots.length === 0 ? "No free time on this day. Try another date." : undefined}
        >
          <Select value={form.time} onChange={(e) => set("time", e.target.value)} disabled={!form.doctor || loading}>
            <option value="">{loading ? "Loading free times…" : "Select time"}</option>
            {freeSlots.map((s) => (
              <option key={s.time} value={s.time}>
                {s.time}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Reason for visit">
          <Textarea value={form.reason} maxLength={500} onChange={(e) => set("reason", e.target.value)} />
        </Field>
      </div>
    </Modal>
  )
}

export default BookAppointmentModal
