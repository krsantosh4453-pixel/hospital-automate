import { useEffect, useState } from "react"
import api from "../../services/api"
import { Alert, Button, Field, Input, Modal, Select } from "../ui"

/*
 * Add a bed to a room of the selected hospital. The ward and the room can be
 * picked or created here, so a new hospital can be set up from one form.
 * The server lets only that hospital's Admin or Manager save.
 */

const NEW = "new"
const BED_TYPES = ["General", "ICU", "Private", "Semi-private", "Pediatric", "Maternity", "Isolation"]
const START_STATUSES = ["Available", "Maintenance", "Reserved"]
const EMPTY_BED = { bed_number: "", bed_type: "General", status: "Available" }
const list = (data) => (Array.isArray(data) ? data : data?.results || [])

/** @param {{ open: boolean, onClose: () => void, hospitalId?: number|string, onAdded: (bed: object) => void }} props */
export default function AddBedDialog({ open, onClose, hospitalId, onAdded }) {
  const [wards, setWards] = useState([])
  const [rooms, setRooms] = useState([])
  const [wardId, setWardId] = useState("")
  const [roomId, setRoomId] = useState("")
  const [newWard, setNewWard] = useState({ name: "", ward_type: "" })
  const [newRoom, setNewRoom] = useState({ room_number: "", room_type: "" })
  const [bed, setBed] = useState(EMPTY_BED)
  const [error, setError] = useState("")
  const [loadError, setLoadError] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open || !hospitalId) return undefined
    let active = true
    setLoadError("")
    api.wards
      .list(hospitalId)
      .then((data) => {
        if (!active) return
        const rows = list(data)
        setWards(rows)
        setWardId((current) => current || (rows.length ? String(rows[0].id) : NEW))
      })
      .catch((err) => active && setLoadError(`Wards could not be loaded: ${err.message}`))
    return () => {
      active = false
    }
  }, [open, hospitalId])

  useEffect(() => {
    setRooms([])
    if (!open || !hospitalId || !wardId || wardId === NEW) {
      setRoomId(wardId === NEW ? NEW : "")
      return undefined
    }
    let active = true
    api.rooms
      .list(hospitalId, wardId)
      .then((data) => {
        if (!active) return
        const rows = list(data)
        setRooms(rows)
        setRoomId(rows.length ? String(rows[0].id) : NEW)
      })
      .catch((err) => active && setLoadError(`Rooms could not be loaded: ${err.message}`))
    return () => {
      active = false
    }
  }, [open, hospitalId, wardId])

  const close = () => {
    setError("")
    setBed(EMPTY_BED)
    setNewWard({ name: "", ward_type: "" })
    setNewRoom({ room_number: "", room_type: "" })
    onClose()
  }

  // Saves the ward and room first when they are new. A ward or room saved
  // before a later step fails stays selected, so a retry does not add it twice.
  const ensureWard = async () => {
    if (wardId !== NEW) return wardId
    const ward = await api.wards.create(hospitalId, newWard)
    setWards((prev) => [...prev, ward])
    setWardId(String(ward.id))
    setNewWard({ name: "", ward_type: "" })
    return String(ward.id)
  }

  const ensureRoom = async (savedWardId) => {
    if (roomId !== NEW) return roomId
    const room = await api.rooms.create(hospitalId, { ...newRoom, ward: savedWardId })
    setRooms((prev) => [...prev, room])
    setRoomId(String(room.id))
    setNewRoom({ room_number: "", room_type: "" })
    return String(room.id)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setSaving(true)
    try {
      const savedWardId = await ensureWard()
      const savedRoomId = await ensureRoom(savedWardId)
      const created = await api.beds.create(hospitalId, { ...bed, room: savedRoomId })
      onAdded(created)
      close()
    } catch (err) {
      setError(`Not saved: ${err.message || "the server refused the request."}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Add bed"
      description="Pick or create the ward and room, then enter the bed."
      footer={
        <>
          <Button variant="secondary" onClick={close} disabled={saving}>Cancel</Button>
          <Button type="submit" form="ipd-add-bed" loading={saving}>Add bed</Button>
        </>
      }
    >
      <form id="ipd-add-bed" onSubmit={handleSubmit} className="space-y-4">
        {loadError && <Alert tone="danger">{loadError}</Alert>}
        {error && <Alert tone="danger">{error}</Alert>}

        <Field label="Ward" required>
          <Select value={wardId} onChange={(e) => setWardId(e.target.value)} disabled={saving}>
            {wards.map((w) => (
              <option key={w.id} value={w.id}>{w.name}{w.ward_type ? ` (${w.ward_type})` : ""}</option>
            ))}
            <option value={NEW}>+ New ward</option>
          </Select>
        </Field>
        {wardId === NEW && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="New ward name" required>
              <Input value={newWard.name} onChange={(e) => setNewWard({ ...newWard, name: e.target.value })} placeholder="General Ward" required disabled={saving} />
            </Field>
            <Field label="Ward type">
              <Input value={newWard.ward_type} onChange={(e) => setNewWard({ ...newWard, ward_type: e.target.value })} placeholder="General, ICU…" disabled={saving} />
            </Field>
          </div>
        )}

        <Field label="Room" required>
          <Select value={roomId} onChange={(e) => setRoomId(e.target.value)} disabled={saving || !wardId}>
            {rooms.map((r) => (
              <option key={r.id} value={r.id}>Room {r.room_number}{r.room_type ? ` (${r.room_type})` : ""}</option>
            ))}
            <option value={NEW}>+ New room</option>
          </Select>
        </Field>
        {roomId === NEW && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="New room number" required>
              <Input value={newRoom.room_number} onChange={(e) => setNewRoom({ ...newRoom, room_number: e.target.value })} placeholder="101" required disabled={saving} />
            </Field>
            <Field label="Room type">
              <Input value={newRoom.room_type} onChange={(e) => setNewRoom({ ...newRoom, room_type: e.target.value })} placeholder="Private, Shared…" disabled={saving} />
            </Field>
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="Bed number" required>
            <Input value={bed.bed_number} onChange={(e) => setBed({ ...bed, bed_number: e.target.value })} placeholder="B-1" required disabled={saving} />
          </Field>
          <Field label="Bed type">
            <Select value={bed.bed_type} onChange={(e) => setBed({ ...bed, bed_type: e.target.value })} disabled={saving}>
              {BED_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
            </Select>
          </Field>
          <Field label="Status">
            <Select value={bed.status} onChange={(e) => setBed({ ...bed, status: e.target.value })} disabled={saving}>
              {START_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
          </Field>
        </div>
      </form>
    </Modal>
  )
}
