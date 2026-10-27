import { useCallback, useEffect, useState } from "react"
import { Pencil, Trash2 } from "lucide-react"
import api from "../../services/api"
import { useToast } from "../Toast.jsx"
import {
  Alert,
  Button,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  SearchInput,
  Select,
  SkeletonRows,
  StatusBadge,
  TableWrap,
  Toolbar,
  useConfirm,
} from "../ui"

/*
 * Every bed of the hospital with its status and current patient. The
 * hospital's Admin or Manager can change a free bed's status, rename a bed
 * and delete a bed that never held a patient; the server enforces the same.
 */

// Statuses set by hand. "Occupied" comes only from allocating a bed.
const MANUAL_STATUSES = ["Available", "Maintenance", "Cleaning", "Reserved"]
const ALL_STATUSES = ["Available", "Occupied", ...MANUAL_STATUSES.slice(1)]
const BED_TYPES = ["General", "ICU", "Private", "Semi-private", "Pediatric", "Maternity", "Isolation"]

/** @param {{ hospitalId?: number|string, canManage: boolean, refreshKey: number, onChanged: () => void }} props */
export default function BedsTable({ hospitalId, canManage, refreshKey, onChanged }) {
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()
  const [beds, setBeds] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [busy, setBusy] = useState("")
  const [editing, setEditing] = useState(null)
  const [editError, setEditError] = useState("")

  const load = useCallback(async () => {
    if (!hospitalId) return
    setLoading(true)
    setLoadError("")
    try {
      setBeds(await api.beds.listAll(hospitalId))
    } catch (err) {
      setLoadError(err.message || "Beds could not be loaded.")
    } finally {
      setLoading(false)
    }
  }, [hospitalId])

  useEffect(() => {
    load()
  }, [load, refreshKey])

  const afterChange = async () => {
    await load()
    onChanged()
  }

  const changeStatus = async (bed, status) => {
    setBusy(`status-${bed.id}`)
    try {
      await api.beds.update(hospitalId, bed.id, { status })
      toast.success(`Bed ${bed.bed_number} is now ${status}`)
      await afterChange()
    } catch (err) {
      toast.error(`Not changed: ${err.message}`)
    } finally {
      setBusy("")
    }
  }

  const removeBed = async (bed) => {
    const ok = await confirm({
      title: "Delete bed?",
      message: `Delete bed ${bed.bed_number} in ${bed.ward_name}, room ${bed.room_number}? A bed that ever held a patient cannot be deleted; set it to Maintenance instead.`,
      confirmLabel: "Delete bed",
    })
    if (!ok) return
    setBusy(`delete-${bed.id}`)
    try {
      await api.beds.remove(hospitalId, bed.id)
      toast.success(`Bed ${bed.bed_number} deleted`)
      await afterChange()
    } catch (err) {
      toast.error(`Not deleted: ${err.message}`)
    } finally {
      setBusy("")
    }
  }

  const saveEdit = async (e) => {
    e.preventDefault()
    setEditError("")
    setBusy("edit")
    try {
      await api.beds.update(hospitalId, editing.id, { bed_number: editing.bed_number, bed_type: editing.bed_type })
      toast.success(`Bed ${editing.bed_number} saved`)
      setEditing(null)
      await afterChange()
    } catch (err) {
      setEditError(`Not saved: ${err.message}`)
    } finally {
      setBusy("")
    }
  }

  const query = search.trim().toLowerCase()
  const shown = beds.filter(
    (bed) =>
      (!statusFilter || bed.status === statusFilter) &&
      (!query || `${bed.ward_name} ${bed.room_number} ${bed.bed_number} ${bed.current_patient || ""}`.toLowerCase().includes(query)),
  )

  if (loadError) return <ErrorState title="Beds could not be loaded" message={loadError} onRetry={load} />

  return (
    <>
      {confirmDialog}
      <Toolbar>
        <SearchInput value={search} onChange={setSearch} placeholder="Ward, room, bed or patient" label="Search beds" className="w-full sm:max-w-xs" />
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filter by status" className="w-full sm:w-48">
          <option value="">All statuses ({beds.length})</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>{s} ({beds.filter((b) => b.status === s).length})</option>
          ))}
        </Select>
      </Toolbar>

      {loading && beds.length === 0 ? (
        <SkeletonRows rows={4} />
      ) : shown.length === 0 ? (
        <EmptyState title={beds.length ? "No beds match these filters" : "No beds yet"} description={beds.length ? "Change the search or status filter." : "Add a bed to start using IPD."} />
      ) : (
        <TableWrap>
          <table className="hms-table">
            <caption className="sr-only">All beds</caption>
            <thead>
              <tr>
                <th scope="col">Ward</th>
                <th scope="col">Room</th>
                <th scope="col">Bed</th>
                <th scope="col">Type</th>
                <th scope="col">Status</th>
                <th scope="col">Patient</th>
                {canManage && <th scope="col"><span className="sr-only">Actions</span></th>}
              </tr>
            </thead>
            <tbody>
              {shown.map((bed) => {
                const inUse = Boolean(bed.current_patient)
                return (
                  <tr key={bed.id}>
                    <td>{bed.ward_name}</td>
                    <td>{bed.room_number}</td>
                    <td className="font-semibold text-ink-900 tabular-nums">{bed.bed_number}</td>
                    <td className="text-ink-600">{bed.bed_type || "—"}</td>
                    <td><StatusBadge status={bed.status} /></td>
                    <td>{bed.current_patient || <span className="text-ink-400">—</span>}</td>
                    {canManage && (
                      <td>
                        <div className="flex items-center justify-end gap-1.5">
                          {inUse ? (
                            <span className="text-xs text-ink-500">Release from the admission to change</span>
                          ) : (
                            <Select
                              value={bed.status}
                              onChange={(e) => changeStatus(bed, e.target.value)}
                              disabled={busy === `status-${bed.id}`}
                              aria-label={`Status of bed ${bed.bed_number}`}
                              className="h-8 min-h-0 w-36 py-1 text-xs"
                            >
                              {MANUAL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                            </Select>
                          )}
                          <Button size="sm" variant="ghost" icon={Pencil} onClick={() => { setEditError(""); setEditing({ ...bed }) }} aria-label={`Edit bed ${bed.bed_number}`}>
                            Edit
                          </Button>
                          {!inUse && (
                            <Button size="sm" variant="ghost" icon={Trash2} loading={busy === `delete-${bed.id}`} onClick={() => removeBed(bed)} aria-label={`Delete bed ${bed.bed_number}`}>
                              Delete
                            </Button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </TableWrap>
      )}

      <Modal
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        size="sm"
        title="Edit bed"
        description={editing ? `${editing.ward_name} · room ${editing.room_number}` : undefined}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditing(null)} disabled={busy === "edit"}>Cancel</Button>
            <Button type="submit" form="ipd-edit-bed" loading={busy === "edit"}>Save</Button>
          </>
        }
      >
        {editing && (
          <form id="ipd-edit-bed" onSubmit={saveEdit} className="space-y-4">
            {editError && <Alert tone="danger">{editError}</Alert>}
            <Field label="Bed number" required>
              <Input value={editing.bed_number} onChange={(e) => setEditing({ ...editing, bed_number: e.target.value })} required />
            </Field>
            <Field label="Bed type">
              <Select value={editing.bed_type || "General"} onChange={(e) => setEditing({ ...editing, bed_type: e.target.value })}>
                {[...new Set([...BED_TYPES, editing.bed_type].filter(Boolean))].map((type) => <option key={type} value={type}>{type}</option>)}
              </Select>
            </Field>
          </form>
        )}
      </Modal>
    </>
  )
}
