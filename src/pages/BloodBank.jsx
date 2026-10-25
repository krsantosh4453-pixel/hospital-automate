import { useCallback, useEffect, useState } from "react"
import { Check, Droplet, Hospital, PackageCheck, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api"
import { useToast } from "../components/Toast.jsx"
import {
  Alert,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  SkeletonRows,
  StatusBadge,
  TableWrap,
  useConfirm,
} from "../components/ui"

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
const COMPONENTS = ["Whole Blood", "Packed Red Cells", "Platelets", "Fresh Frozen Plasma", "Cryoprecipitate"]
const EMPTY_REQUEST = { patient: "", blood_group: "", component: "Whole Blood", units: 1 }
const list = (data) => (Array.isArray(data) ? data : data?.results || [])

const daysUntil = (date) => (date ? Math.ceil((new Date(date) - new Date()) / 86400000) : null)

function BloodBank() {
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()
  const { selectedHospital } = usePatient()

  const [inventory, setInventory] = useState([])
  const [requests, setRequests] = useState([])
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [showRequestModal, setShowRequestModal] = useState(false)
  const [editingRequest, setEditingRequest] = useState(null)
  const [requestForm, setRequestForm] = useState(EMPTY_REQUEST)
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState("")

  const fetchData = useCallback(async () => {
    if (!selectedHospital) {
      setInventory([])
      setRequests([])
      setLoading(false)
      return
    }
    setLoading(true)
    setLoadError("")
    try {
      const [invRes, reqRes, patientRes] = await Promise.all([
        api.bloodbank.inventory.list(selectedHospital.id),
        api.bloodbank.requests.list(selectedHospital.id),
        api.patients.list(selectedHospital.id),
      ])
      setInventory(list(invRes))
      setRequests(list(reqRes))
      setPatients(list(patientRes))
    } catch (err) {
      setLoadError(err.message || "Failed to load blood bank data")
    } finally {
      setLoading(false)
    }
  }, [selectedHospital])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const resetForms = () => {
    setEditingRequest(null)
    setRequestForm(EMPTY_REQUEST)
    setShowRequestModal(false)
  }

  const handleRequestSubmit = async (e) => {
    e.preventDefault()
    if (!selectedHospital) return
    setSaving(true)
    const payload = {
      hospital: selectedHospital.id,
      patient: Number(requestForm.patient),
      blood_group: requestForm.blood_group,
      component: requestForm.component,
      units: Number(requestForm.units),
    }
    try {
      if (editingRequest) await api.bloodbank.requests.patch(editingRequest.id, payload)
      else await api.bloodbank.requests.create(payload)
      toast.success(editingRequest ? "Blood request updated" : "Blood request created")
      resetForms()
      fetchData()
    } catch (err) {
      toast.error(err.message || "The request was not saved")
    } finally {
      setSaving(false)
    }
  }

  const handleEdit = (req) => {
    setEditingRequest(req)
    setRequestForm({
      patient: req.patient ? String(req.patient) : "",
      blood_group: req.blood_group || "",
      component: req.component || "Whole Blood",
      units: req.units || 1,
    })
    setShowRequestModal(true)
  }

  const handleDelete = async (req) => {
    if (!(await confirm({ title: "Delete blood request?", message: `Delete the request for ${req.patient_name || "this patient"}? This cannot be undone.`, confirmLabel: "Delete" }))) return
    try {
      await api.bloodbank.requests.delete(req.id)
      toast.success("Blood request deleted")
      fetchData()
    } catch (err) {
      toast.error(err.message || "The request was not deleted")
    }
  }

  const runAction = async (req, action) => {
    const copy = {
      approve: { title: "Approve request?", message: `Approve ${req.units} unit(s) of ${req.blood_group} ${req.component} for ${req.patient_name}? Stock is checked but not yet deducted.`, label: "Approve", done: "Request approved" },
      issue: { title: "Issue blood?", message: `Issue ${req.units} unit(s) of ${req.blood_group} ${req.component} to ${req.patient_name}? This deducts the units from stock.`, label: "Issue", done: "Blood issued and stock updated" },
      reject: { title: "Reject request?", message: `Reject the request for ${req.patient_name}?`, label: "Reject", done: "Request rejected" },
    }[action]
    if (!(await confirm({ title: copy.title, message: copy.message, confirmLabel: copy.label, destructive: action === "reject" }))) return
    setBusy(`${action}-${req.id}`)
    try {
      await api.bloodbank.requests[action](req.id)
      toast.success(copy.done)
      fetchData()
    } catch (err) {
      toast.error(err.message || `Could not ${action} the request`)
    } finally {
      setBusy("")
    }
  }

  const header = (
    <PageHeader
      title="Blood bank"
      description={selectedHospital ? `Stock and requests at ${selectedHospital.name}.` : undefined}
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Blood bank" }]}
      actions={
        selectedHospital && (
          <>
            <Button variant="secondary" icon={RefreshCw} onClick={fetchData} disabled={loading}>Refresh</Button>
            <Button icon={Plus} onClick={() => { resetForms(); setShowRequestModal(true) }}>New request</Button>
          </>
        )
      }
    />
  )

  if (!selectedHospital) {
    return (
      <>{confirmDialog}<div className="space-y-5">
        {header}
        <Card><EmptyState icon={Hospital} title="Select a hospital" description="Choose a hospital in the header to view its blood bank." /></Card>
      </div></>
    )
  }

  // Units by blood group across components, for the stock overview.
  const byGroup = BLOOD_GROUPS.map((group) => {
    const rows = inventory.filter((i) => i.blood_group === group)
    return {
      group,
      units: rows.reduce((s, r) => s + Number(r.units || 0), 0),
      expiringSoon: rows.some((r) => {
        const d = daysUntil(r.expiry_date)
        return d !== null && d >= 0 && d <= 7 && Number(r.units) > 0
      }),
    }
  })
  const openRequests = requests.filter((r) => r.status === "Requested" || r.status === "Approved")

  return (
    <>{confirmDialog}<div className="space-y-5">
      {header}

      {loadError && (
        <Alert tone="danger" action={<Button size="sm" variant="secondary" onClick={fetchData}>Retry</Button>}>{loadError}</Alert>
      )}

      <Card>
        <CardHeader title="Stock by blood group" description="All components, in units. Groups with stock expiring within 7 days are flagged." />
        {loading && inventory.length === 0 ? (
          <SkeletonRows rows={2} />
        ) : (
          <ul className="grid grid-cols-2 gap-px bg-line sm:grid-cols-4 xl:grid-cols-8">
            {byGroup.map(({ group, units, expiringSoon }) => (
              <li key={group} className="bg-white px-4 py-4">
                <p className="flex items-center gap-1.5 text-sm font-semibold text-ink-700">
                  <Droplet size={15} className="text-red-500" aria-hidden="true" /> {group}
                </p>
                <p className={`mt-1 text-2xl font-semibold tabular-nums ${units === 0 ? "text-red-700" : "text-ink-900"}`}>{units}</p>
                <p className={`text-xs ${expiringSoon ? "font-medium text-amber-700" : units === 0 ? "text-red-700" : "text-ink-500"}`}>
                  {expiringSoon ? "Expiring soon" : units === 0 ? "None in stock" : "units"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[minmax(0,1fr)_28rem]">
        <Card className="overflow-hidden">
          <CardHeader title="Requests" description={`${openRequests.length} open`} />
          {loading && requests.length === 0 ? (
            <SkeletonRows rows={4} />
          ) : requests.length === 0 ? (
            <EmptyState icon={Droplet} title="No blood requests yet" />
          ) : (
            <TableWrap>
              <table className="hms-table">
                <thead>
                  <tr>
                    <th scope="col">Patient</th>
                    <th scope="col">Group</th>
                    <th scope="col">Component</th>
                    <th scope="col" className="num">Units</th>
                    <th scope="col">Status</th>
                    <th scope="col"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map((req) => (
                    <tr key={req.id}>
                      <td>
                        <span className="block font-medium text-ink-900">{req.patient_name || `Patient #${req.patient}`}</span>
                        <span className="block text-xs text-ink-500 tabular-nums">{req.created_at ? new Date(req.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : ""}</span>
                      </td>
                      <td className="font-semibold text-ink-900">{req.blood_group}</td>
                      <td className="text-ink-600">{req.component}</td>
                      <td className="num">{req.units}</td>
                      <td><StatusBadge status={req.status} /></td>
                      <td>
                        <div className="flex items-center justify-end gap-1">
                          {req.status === "Requested" && (
                            <>
                              <Button size="sm" variant="subtle" icon={Check} loading={busy === `approve-${req.id}`} onClick={() => runAction(req, "approve")}>Approve</Button>
                              <Button size="icon-sm" variant="ghost" icon={X} onClick={() => runAction(req, "reject")} aria-label="Reject request" title="Reject" />
                              <Button size="icon-sm" variant="ghost" icon={Pencil} onClick={() => handleEdit(req)} aria-label="Edit request" title="Edit" />
                            </>
                          )}
                          {req.status === "Approved" && (
                            <Button size="sm" icon={PackageCheck} loading={busy === `issue-${req.id}`} onClick={() => runAction(req, "issue")}>Issue</Button>
                          )}
                          {req.status === "Requested" && (
                            <Button size="icon-sm" variant="danger-ghost" icon={Trash2} onClick={() => handleDelete(req)} aria-label="Delete request" title="Delete" />
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}
        </Card>

        <Card className="self-start overflow-hidden">
          <CardHeader title="Inventory lots" />
          {inventory.length === 0 ? (
            <EmptyState compact icon={Droplet} title="No inventory recorded" />
          ) : (
            <TableWrap>
              <table className="hms-table">
                <thead>
                  <tr>
                    <th scope="col">Group</th>
                    <th scope="col">Component</th>
                    <th scope="col" className="num">Units</th>
                    <th scope="col">Expiry</th>
                  </tr>
                </thead>
                <tbody>
                  {inventory.map((item) => {
                    const d = daysUntil(item.expiry_date)
                    return (
                      <tr key={item.id}>
                        <td className="font-semibold text-ink-900">{item.blood_group}</td>
                        <td className="text-ink-600">{item.component}</td>
                        <td className="num">{item.units}</td>
                        <td className={`whitespace-nowrap tabular-nums ${d !== null && d < 0 ? "font-medium text-red-700" : d !== null && d <= 7 ? "font-medium text-amber-700" : "text-ink-600"}`}>
                          {item.expiry_date ? new Date(item.expiry_date).toLocaleDateString("en-IN") : "—"}
                          {d !== null && d < 0 && " (expired)"}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </TableWrap>
          )}
        </Card>
      </div>

      <Modal
        open={showRequestModal}
        onClose={resetForms}
        title={editingRequest ? "Edit blood request" : "New blood request"}
        footer={
          <>
            <Button variant="secondary" onClick={resetForms}>Cancel</Button>
            <Button type="submit" form="blood-form" loading={saving}>{editingRequest ? "Save changes" : "Create request"}</Button>
          </>
        }
      >
        <form id="blood-form" onSubmit={handleRequestSubmit} className="space-y-4">
          <Field label="Patient" required>
            <Select value={requestForm.patient} onChange={(e) => setRequestForm({ ...requestForm, patient: e.target.value })}>
              <option value="">Select patient</option>
              {patients.map((p) => <option key={p.id} value={p.id}>{p.name}{p.phone ? ` · ${p.phone}` : ""}</option>)}
            </Select>
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Blood group" required>
              <Select value={requestForm.blood_group} onChange={(e) => setRequestForm({ ...requestForm, blood_group: e.target.value })}>
                <option value="">Select</option>
                {BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
              </Select>
            </Field>
            <Field label="Units" required>
              <Input type="number" min="1" inputMode="numeric" value={requestForm.units} onChange={(e) => setRequestForm({ ...requestForm, units: e.target.value })} />
            </Field>
          </div>
          <Field label="Component" required>
            <Select value={requestForm.component} onChange={(e) => setRequestForm({ ...requestForm, component: e.target.value })}>
              {COMPONENTS.map((c) => <option key={c}>{c}</option>)}
              {requestForm.component && !COMPONENTS.includes(requestForm.component) && <option>{requestForm.component}</option>}
            </Select>
          </Field>
        </form>
      </Modal>
    </div></>
  )
}

export default BloodBank
