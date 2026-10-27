import { useCallback, useEffect, useState } from "react"
import { usePatient } from "../../assets/context/PatientContext.jsx"
import api from "../../services/api.js"
import { Alert, Button, Card, CardHeader, Field, Input, PageHeader, Select, TableWrap } from "../../components/ui"

const SHIFTS = ["Morning", "Evening", "Night"]
const rows = (data) => (Array.isArray(data) ? data : data?.results || [])

/** Today's date in the browser's time zone, as YYYY-MM-DD. */
function todayIso() {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

// Ward duty roster of the selected hospital. A Nurse sees the admitted
// patients of the wards of today's duty (yesterday's Night shift included);
// only that hospital's Admin or Hospital Manager can change the roster.
function NurseDuty() {
  const { selectedHospital } = usePatient()
  const [day, setDay] = useState(todayIso)
  const [duties, setDuties] = useState([])
  const [nurses, setNurses] = useState([])
  const [wards, setWards] = useState([])
  const [form, setForm] = useState({ nurse: "", ward: "", shift: "Morning" })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  const load = useCallback(async () => {
    if (!selectedHospital) return
    setLoading(true)
    setError("")
    try {
      const [dutyData, nurseData, wardData] = await Promise.all([
        api.nurseWardDuty.list(selectedHospital.id, day),
        api.nurses.list(selectedHospital.id),
        api.wards.list(selectedHospital.id),
      ])
      setDuties(rows(dutyData))
      setNurses(rows(nurseData))
      setWards(rows(wardData))
    } catch (err) {
      setError(err.message || "Could not load the duty roster.")
    } finally {
      setLoading(false)
    }
  }, [selectedHospital, day])

  useEffect(() => {
    load()
  }, [load])

  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  const assign = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError("")
    setNotice("")
    try {
      await api.nurseWardDuty.create({
        hospital: selectedHospital.id,
        nurse: Number(form.nurse),
        ward: Number(form.ward),
        shift: form.shift,
        shift_date: day,
      })
      setNotice("Duty assigned.")
      setForm((prev) => ({ ...prev, nurse: "" }))
      await load()
    } catch (err) {
      setError(err.message || "Could not assign the duty.")
    } finally {
      setSaving(false)
    }
  }

  const setActive = async (duty, isActive) => {
    setError("")
    setNotice("")
    try {
      await api.nurseWardDuty.update(duty.id, { is_active: isActive })
      await load()
    } catch (err) {
      setError(err.message || "Could not change the duty.")
    }
  }

  const unlinked = nurses.filter((n) => !n.user)

  return (
    <div className="space-y-5">
      <PageHeader
        title="Nurse duty"
        description={`Ward and shift duty of ${selectedHospital?.name || "the selected hospital"}. A nurse sees the patients of their own duty.`}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Administration", to: "/admin" }, { label: "Nurse duty" }]}
      />

      {error && <Alert tone="danger">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}
      {unlinked.length > 0 && (
        <Alert tone="warning">
          Not linked to a staff login, so they see no ward patients yet: {unlinked.map((n) => n.name).join(", ")}.
          Set each nurse&apos;s email to their login email on the Nursing page.
        </Alert>
      )}

      <Card>
        <CardHeader title="Assign duty" description="One nurse, one ward, one shift of the chosen day." />
        <form onSubmit={assign} className="grid grid-cols-1 gap-4 px-5 py-5 sm:grid-cols-2 lg:grid-cols-5">
          <Field label="Date" required>
            <Input type="date" value={day} onChange={(e) => setDay(e.target.value)} />
          </Field>
          <Field label="Nurse" required>
            <Select value={form.nurse} onChange={(e) => set("nurse", e.target.value)}>
              <option value="">Select nurse</option>
              {nurses.map((n) => (
                <option key={n.id} value={n.id}>{n.name}</option>
              ))}
            </Select>
          </Field>
          <Field label="Ward" required>
            <Select value={form.ward} onChange={(e) => set("ward", e.target.value)}>
              <option value="">Select ward</option>
              {wards.map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </Select>
          </Field>
          <Field label="Shift" required>
            <Select value={form.shift} onChange={(e) => set("shift", e.target.value)}>
              {SHIFTS.map((s) => <option key={s}>{s}</option>)}
            </Select>
          </Field>
          <div className="flex items-end">
            <Button type="submit" loading={saving} disabled={!form.nurse || !form.ward}>
              Assign
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardHeader title={`Duty on ${day}`} />
        <div className="px-5 py-4">
          {loading ? (
            <p className="text-sm text-ink-500" role="status">Loading duty…</p>
          ) : duties.length === 0 ? (
            <p className="text-sm text-ink-500">No duty assigned for this day.</p>
          ) : (
            <TableWrap>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-ink-500">
                    <th className="py-2 pr-4">Nurse</th>
                    <th className="py-2 pr-4">Ward</th>
                    <th className="py-2 pr-4">Shift</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {duties.map((duty) => (
                    <tr key={duty.id} className="border-b last:border-0">
                      <td className="py-3 pr-4 font-medium text-ink-900">{duty.nurse_name}</td>
                      <td className="py-3 pr-4">{duty.ward_name}</td>
                      <td className="py-3 pr-4">{duty.shift}</td>
                      <td className="py-3 pr-4">{duty.is_active ? "On duty" : "Cancelled"}</td>
                      <td className="py-3 text-right">
                        <Button variant="secondary" size="sm" onClick={() => setActive(duty, !duty.is_active)}>
                          {duty.is_active ? "Cancel" : "Restore"}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}
        </div>
      </Card>
    </div>
  )
}

export default NurseDuty
