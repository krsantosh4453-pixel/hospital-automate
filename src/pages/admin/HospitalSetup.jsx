import { useCallback, useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeft, ArrowRight, BedDouble, Building2, Check, ClipboardList, Plus, UserPlus } from "lucide-react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import { useHospitals } from "../../assets/context/HospitalsContext.jsx"
import { usePatient } from "../../assets/context/PatientContext.jsx"
import InviteStaffForm from "../../components/admin/InviteStaffForm.jsx"
import WardBedsForm from "../../components/admin/WardBedsForm.jsx"
import api from "../../services/api.js"
import { Alert, Badge, Button, Card, CardBody, CardHeader, Field, Input, PageHeader, Select } from "../../components/ui"

const STEPS = [
  { title: "Hospital", icon: Building2 },
  { title: "Departments", icon: ClipboardList },
  { title: "Wards & beds", icon: BedDouble },
  { title: "Staff", icon: UserPlus },
]
const HOSPITAL_TYPES = ["Private", "Government", "Trust"]
const EMPTY_HOSPITAL = { name: "", code: "", type: "Private", phone: "", email: "", address: "", city: "", state: "" }
const list = (data) => (Array.isArray(data) ? data : data?.results || [])

// Mirrors hospital.views.can_add_hospital; the server has the final say.
function canAddHospital(auth) {
  const roles = auth?.user?.roles || auth?.roles || []
  const hospitals = auth?.user?.hospitals || auth?.hospitals || []
  const profileRole = auth?.user?.staff_role || auth?.staff_role
  return roles.includes("Admin") || (profileRole === "Admin" && hospitals.length === 0)
}

function StepList({ step, onPick, enabled }) {
  return (
    <ol className="flex flex-wrap gap-2" aria-label="Setup steps">
      {STEPS.map(({ title, icon: Icon }, index) => {
        const current = index === step
        return (
          <li key={title}>
            <button
              type="button"
              onClick={() => onPick(index)}
              disabled={!enabled && index > 0}
              aria-current={current ? "step" : undefined}
              className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium disabled:opacity-50 ${
                current ? "border-brand-600 bg-brand-50 text-brand-800" : "border-line bg-surface text-ink-700 hover:bg-ink-50"
              }`}
            >
              {index < step ? <Check size={16} aria-hidden="true" /> : <Icon size={16} aria-hidden="true" />}
              {index + 1}. {title}
            </button>
          </li>
        )
      })}
    </ol>
  )
}

function HospitalStep({ selectedHospital, allowNew, onCreated }) {
  const { addHospital } = useHospitals()
  const [creating, setCreating] = useState(!selectedHospital)
  const [form, setForm] = useState(EMPTY_HOSPITAL)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError("")
    if (form.phone && form.phone.length !== 10) {
      setError("Enter a 10-digit phone number, or leave it empty.")
      return
    }
    setSaving(true)
    try {
      onCreated(await addHospital(form))
    } catch (err) {
      setError(err.message || "The hospital was not created.")
    } finally {
      setSaving(false)
    }
  }

  if (!creating && selectedHospital) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-ink-700">
          Setting up <strong>{selectedHospital.name}</strong>. Continue to add its departments, wards and staff.
        </p>
        {allowNew && (
          <Button variant="secondary" icon={Plus} onClick={() => setCreating(true)}>
            Add a new hospital instead
          </Button>
        )}
      </div>
    )
  }

  if (!allowNew) {
    return (
      <Alert tone="warning" title="Only an Admin can add a hospital">
        Ask your platform administrator for an Admin account, or for a hospital to be added for you.
      </Alert>
    )
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {error && <Alert tone="danger">{error}</Alert>}
      <p className="text-sm text-ink-600">You become the Admin of the new hospital.</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Hospital name" required>
          <Input value={form.name} onChange={set("name")} />
        </Field>
        <Field label="Registration code" hint="Short code shown in lists, e.g. CCH01">
          <Input value={form.code} onChange={set("code")} />
        </Field>
        <Field label="Type">
          <Select value={form.type} onChange={set("type")}>
            {HOSPITAL_TYPES.map((type) => (
              <option key={type}>{type}</option>
            ))}
          </Select>
        </Field>
        <Field label="Phone">
          <Input
            value={form.phone}
            inputMode="numeric"
            onChange={(e) => setForm({ ...form, phone: e.target.value.replace(/\D/g, "").slice(0, 10) })}
          />
        </Field>
        <Field label="Email">
          <Input type="email" value={form.email} onChange={set("email")} />
        </Field>
        <Field label="Address">
          <Input value={form.address} onChange={set("address")} />
        </Field>
        <Field label="City">
          <Input value={form.city} onChange={set("city")} />
        </Field>
        <Field label="State">
          <Input value={form.state} onChange={set("state")} />
        </Field>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" icon={Plus} loading={saving} disabled={!form.name.trim()}>
          Create hospital
        </Button>
        {selectedHospital && (
          <Button variant="ghost" onClick={() => setCreating(false)}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  )
}

function NameBadges({ label, rows, empty }) {
  if (rows.length === 0) return <p className="text-sm text-ink-500">{empty}</p>
  return (
    <ul className="flex flex-wrap gap-2" aria-label={label}>
      {rows.map((row) => (
        <li key={row.id}>
          <Badge>{row.name}</Badge>
        </li>
      ))}
    </ul>
  )
}

function DepartmentsStep({ hospitalId, departments, onChange }) {
  const [name, setName] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  const add = async (e) => {
    e.preventDefault()
    setError("")
    setSaving(true)
    try {
      await api.departments.create({ hospital: hospitalId, name: name.trim() })
      setName("")
      await onChange()
    } catch (err) {
      setError(err.message || "The department was not added.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      {error && <Alert tone="danger">{error}</Alert>}
      <form onSubmit={add} className="flex flex-wrap items-end gap-3" noValidate>
        <Field label="Department name" className="min-w-[14rem] flex-1">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. General Medicine" />
        </Field>
        <Button type="submit" icon={Plus} loading={saving} disabled={!name.trim()}>
          Add
        </Button>
      </form>
      <NameBadges label="Departments" rows={departments} empty="No departments yet." />
    </div>
  )
}

function WardsStep({ hospitalId, wards, onChange }) {
  const [created, setCreated] = useState(null)
  return (
    <div className="space-y-5">
      {created && (
        <Alert tone="success">
          {created.name} was created with {created.room_count} rooms and {created.bed_count} beds.
        </Alert>
      )}
      <NameBadges label="Wards" rows={wards} empty="No wards yet." />
      <WardBedsForm
        hospitalId={hospitalId}
        onCreated={async (ward) => {
          setCreated(ward)
          await onChange()
        }}
      />
      <p className="text-[13px] text-ink-500">
        Beds can be renamed or put under maintenance later on the{" "}
        <Link to="/ipd" className="text-brand-700 hover:underline">IPD</Link> page.
      </p>
    </div>
  )
}

/**
 * Setting up a hospital in four steps: the hospital itself, its
 * departments, wards with beds, and staff invitations with roles.
 */
function HospitalSetup() {
  const navigate = useNavigate()
  const { user, refreshUser } = useAuth()
  const { selectedHospital, selectHospital } = usePatient()
  const [step, setStep] = useState(0)
  const [departments, setDepartments] = useState([])
  const [wards, setWards] = useState([])
  const [loadError, setLoadError] = useState("")
  const [invitedCount, setInvitedCount] = useState(0)
  const hospitalId = selectedHospital?.id

  const loadStructure = useCallback(async () => {
    if (!hospitalId) return
    setLoadError("")
    try {
      const [deptData, wardData] = await Promise.all([api.departments.list(hospitalId), api.wards.list(hospitalId)])
      setDepartments(list(deptData))
      setWards(list(wardData))
    } catch (err) {
      setLoadError(err.message || "Could not load this hospital's departments and wards.")
    }
  }, [hospitalId])

  useEffect(() => {
    loadStructure()
  }, [loadStructure])

  const onHospitalCreated = async (hospital) => {
    selectHospital(hospital)
    await refreshUser()
    setStep(1)
  }

  const body = [
    <HospitalStep key="h" selectedHospital={selectedHospital} allowNew={canAddHospital(user)} onCreated={onHospitalCreated} />,
    <DepartmentsStep key="d" hospitalId={hospitalId} departments={departments} onChange={loadStructure} />,
    <WardsStep key="w" hospitalId={hospitalId} wards={wards} onChange={loadStructure} />,
    <InviteStaffForm key="s" departments={departments} onInvited={() => setInvitedCount((n) => n + 1)} />,
  ][step]

  const last = step === STEPS.length - 1

  return (
    <div className="space-y-5">
      <PageHeader
        title="Hospital setup"
        description="Add a hospital, its departments, wards and beds, and invite its staff with their roles."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Administration", to: "/admin" }, { label: "Setup" }]}
      />
      <StepList step={step} onPick={setStep} enabled={Boolean(hospitalId)} />
      {loadError && <Alert tone="danger">{loadError}</Alert>}

      <Card>
        <CardHeader
          title={STEPS[step].title}
          icon={STEPS[step].icon}
          description={step > 0 && selectedHospital ? selectedHospital.name : undefined}
        />
        <CardBody>{body}</CardBody>
      </Card>

      {last && invitedCount > 0 && (
        <Alert tone="info">
          {invitedCount} {invitedCount === 1 ? "person was" : "people were"} invited. Manage everyone&apos;s roles on the{" "}
          <Link to="/admin/users" className="font-medium underline">Users</Link> page.
        </Alert>
      )}

      <div className="flex justify-between">
        <Button variant="ghost" icon={ArrowLeft} disabled={step === 0} onClick={() => setStep(step - 1)}>
          Back
        </Button>
        {last ? (
          <Button iconRight={Check} onClick={() => navigate("/admin")}>
            Finish
          </Button>
        ) : (
          <Button iconRight={ArrowRight} disabled={!hospitalId} onClick={() => setStep(step + 1)}>
            Next
          </Button>
        )}
      </div>
    </div>
  )
}

export default HospitalSetup
