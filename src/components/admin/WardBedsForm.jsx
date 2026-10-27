import { useState } from "react"
import { Plus, Trash2 } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, Field, Input, Select } from "../ui"

const WARD_TYPES = ["General", "Private", "Semi-Private", "ICU", "NICU", "Maternity", "Emergency", "Isolation"]
const MAX_BEDS_PER_ROOM = 50
const newRoom = (number = "") => ({ room_number: number, beds: 4 })

/**
 * A new ward with its rooms; each room gets that many beds, numbered
 * <room>-1, <room>-2, … by the server. Everything is saved together.
 */
export default function WardBedsForm({ hospitalId, onCreated }) {
  const [name, setName] = useState("")
  const [wardType, setWardType] = useState("General")
  const [rooms, setRooms] = useState([newRoom("101")])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  const totalBeds = rooms.reduce((sum, room) => sum + (Number(room.beds) || 0), 0)

  const updateRoom = (index, changes) =>
    setRooms(rooms.map((room, i) => (i === index ? { ...room, ...changes } : room)))

  const addRoom = () => {
    const last = Number(rooms[rooms.length - 1]?.room_number)
    setRooms([...rooms, newRoom(Number.isFinite(last) && last > 0 ? String(last + 1) : "")])
  }

  const submit = async (e) => {
    e.preventDefault()
    setError("")
    if (rooms.some((room) => !room.room_number.trim())) {
      setError("Give every room a number or name.")
      return
    }
    setSaving(true)
    try {
      const ward = await api.wardSetup.create(hospitalId, {
        name,
        ward_type: wardType,
        rooms: rooms.map((room) => ({ room_number: room.room_number.trim(), beds: Number(room.beds), bed_type: wardType })),
      })
      setName("")
      setRooms([newRoom("101")])
      onCreated?.(ward)
    } catch (err) {
      setError(err.message || "The ward was not saved.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {error && <Alert tone="danger">{error}</Alert>}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Ward name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. General Ward A" />
        </Field>
        <Field label="Ward type">
          <Select value={wardType} onChange={(e) => setWardType(e.target.value)}>
            {WARD_TYPES.map((type) => (
              <option key={type}>{type}</option>
            ))}
          </Select>
        </Field>
      </div>

      <div className="space-y-2">
        <p className="hms-label">Rooms and beds</p>
        {rooms.map((room, index) => (
          <div key={index} className="flex flex-wrap items-end gap-3">
            <Field label={`Room ${index + 1}`} className="min-w-[8rem] flex-1">
              <Input value={room.room_number} onChange={(e) => updateRoom(index, { room_number: e.target.value })} />
            </Field>
            <Field label="Beds" className="w-24">
              <Input
                type="number"
                min={1}
                max={MAX_BEDS_PER_ROOM}
                value={room.beds}
                onChange={(e) => updateRoom(index, { beds: e.target.value })}
              />
            </Field>
            <Button
              variant="danger-ghost"
              size="icon"
              icon={Trash2}
              aria-label={`Remove room ${room.room_number || index + 1}`}
              disabled={rooms.length === 1}
              onClick={() => setRooms(rooms.filter((_, i) => i !== index))}
            />
          </div>
        ))}
        <Button variant="ghost" size="sm" icon={Plus} onClick={addRoom}>
          Add room
        </Button>
      </div>

      <Button type="submit" icon={Plus} loading={saving} disabled={!name.trim() || totalBeds < 1}>
        Create ward with {totalBeds} {totalBeds === 1 ? "bed" : "beds"}
      </Button>
    </form>
  )
}
