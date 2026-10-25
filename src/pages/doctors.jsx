import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Briefcase, Clock, FileText, Hospital, Pencil, Phone, Stethoscope, Trash2, UserPlus } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import {
  Alert,
  Avatar,
  Button,
  Card,
  ConfirmDialog,
  DescriptionList,
  EmptyState,
  Field,
  Input,
  Modal,
  PageHeader,
  SearchInput,
  SegmentedControl,
  Select,
  StatusBadge,
} from "../components/ui"

// =====================================================
// Helpers — keep the existing (flat, display-oriented) UI
// shape while talking to the Django Doctor API.
// =====================================================

// The directory UI only knows "Available" / "On Leave".
// Any other backend value is kept as-is.
const DOCTOR_STATUSES = ["Available", "On Leave"]

const normaliseDoctorStatus = (status) => {
  if (!status) return "Available"
  const match = DOCTOR_STATUSES.find((item) => item.toLowerCase() === String(status).toLowerCase())
  return match || status
}

// Map a Django Doctor record to the flat shape the UI expects. `apiId` keeps
// the real database id (used for update/delete); `id` is the display id.
const mapDoctorFromApi = (record) => ({
  apiId: record.id,
  id: `D${String(record.id).padStart(3, "0")}`,
  name: record.name || "",
  specialization: record.specialization || "",
  phone: record.phone || "",
  experience: record.experience || "",
  status: normaliseDoctorStatus(record.status),
  availability: record.availability || "",
  hospitalId: record.hospital,
})

const EMPTY_FORM = { name: "", specialization: "", phone: "", experience: "", status: "Available", availability: "" }

function Doctors() {
  const { selectedHospital } = usePatient()

  const [doctors, setDoctors] = useState([])

  // API / UX states.
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [formError, setFormError] = useState("")
  const [offlineMode, setOfflineMode] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")
  const [reloadToken, setReloadToken] = useState(0)

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [showForm, setShowForm] = useState(false)
  const [selectedDoctor, setSelectedDoctor] = useState(null)
  const [formData, setFormData] = useState(EMPTY_FORM)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)

  // ==============================
  // LOAD DOCTORS FROM DJANGO
  // ==============================

  useEffect(() => {
    if (!selectedHospital) {
      setDoctors([])
      setLoadError("")
      setOfflineMode(false)
      return undefined
    }

    let cancelled = false

    const loadDoctors = async () => {
      setLoading(true)
      setLoadError("")
      try {
        const data = await api.doctors.list(selectedHospital.id)
        const results = Array.isArray(data) ? data : data?.results || []
        if (cancelled) return
        setDoctors(results.map(mapDoctorFromApi))
        setOfflineMode(false)
      } catch (error) {
        if (cancelled) return
        setDoctors([])
        setOfflineMode(true)
        setLoadError(error.message || "Unable to reach the server.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadDoctors()
    return () => {
      cancelled = true
    }
  }, [selectedHospital, reloadToken])

  // Auto-dismiss the success message.
  useEffect(() => {
    if (!successMessage) return undefined
    const timer = setTimeout(() => setSuccessMessage(""), 3000)
    return () => clearTimeout(timer)
  }, [successMessage])

  // ==============================
  // FILTERS
  // ==============================

  const hospitalDoctors = selectedHospital ? doctors.filter((doctor) => String(doctor.hospitalId) === String(selectedHospital.id)) : []

  const filteredDoctors = hospitalDoctors.filter((doctor) => {
    const q = search.toLowerCase()
    const matches =
      doctor.name.toLowerCase().includes(q) || doctor.specialization.toLowerCase().includes(q) || doctor.id.toLowerCase().includes(q)
    const statusOk = statusFilter === "all" || (statusFilter === "available" ? doctor.status === "Available" : doctor.status !== "Available")
    return matches && statusOk
  })

  const availableDoctors = hospitalDoctors.filter((doctor) => doctor.status === "Available").length
  const onLeaveDoctors = hospitalDoctors.filter((doctor) => doctor.status === "On Leave").length

  // ==============================
  // FORM
  // ==============================

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData({ ...formData, [name]: value })
  }

  const resetForm = () => {
    setFormData(EMPTY_FORM)
    setSelectedDoctor(null)
    setFormError("")
    setShowForm(false)
  }

  const openNew = () => {
    setSelectedDoctor(null)
    setFormData(EMPTY_FORM)
    setFormError("")
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedHospital || saving) return

    const payload = {
      name: formData.name,
      specialization: formData.specialization,
      phone: formData.phone,
      experience: formData.experience,
      availability: formData.availability,
      status: formData.status || "Available",
      hospital: selectedHospital.id,
    }

    setSaving(true)
    setFormError("")
    try {
      const created = await api.doctors.create(payload)
      setDoctors([...doctors, mapDoctorFromApi(created)])
      setSuccessMessage("Doctor added.")
      resetForm()
    } catch (error) {
      // A doctor that is not on the server cannot be booked or linked, so
      // nothing is kept locally: show why and keep the form open.
      setFormError(error.isNetworkError ? "The server could not be reached. Nothing was saved." : error.message)
    } finally {
      setSaving(false)
    }
  }

  const handleEdit = (doctor) => {
    setSelectedDoctor(doctor)
    setFormData({
      name: doctor.name,
      specialization: doctor.specialization,
      phone: doctor.phone,
      experience: doctor.experience,
      status: doctor.status,
      availability: doctor.availability,
    })
    setFormError("")
    setShowForm(true)
  }

  const handleUpdate = async (e) => {
    e.preventDefault()
    if (!selectedDoctor || saving) return

    const payload = {
      name: formData.name,
      specialization: formData.specialization,
      phone: formData.phone,
      experience: formData.experience,
      availability: formData.availability,
      status: formData.status || "Available",
      hospital: selectedHospital?.id ?? selectedDoctor.hospitalId,
    }

    setSaving(true)
    setFormError("")
    try {
      if (selectedDoctor.apiId) await api.doctors.update(selectedDoctor.apiId, payload)
      setDoctors(doctors.map((doctor) => (String(doctor.id) === String(selectedDoctor.id) ? { ...doctor, ...formData } : doctor)))
      setSuccessMessage("Doctor updated.")
      resetForm()
    } catch (error) {
      setFormError(error.isNetworkError ? "The server could not be reached. Nothing was saved." : error.message)
    } finally {
      setSaving(false)
    }
  }

  const confirmDelete = async () => {
    const target = pendingDelete
    if (!target) return
    setDeleting(true)
    try {
      if (target.apiId) await api.doctors.delete(target.apiId)
      setDoctors(doctors.filter((doctor) => String(doctor.id) !== String(target.id)))
      setSuccessMessage("Doctor deleted.")
    } catch (error) {
      setLoadError(error.isNetworkError ? "The server could not be reached. Please try again." : `Not deleted: ${error.message}`)
    } finally {
      setDeleting(false)
      setPendingDelete(null)
      setSelectedDoctor(null)
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Doctors"
        description={selectedHospital ? `Doctors, specialities and availability at ${selectedHospital.name}.` : "Select a hospital from the header to view doctors."}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Doctors" }]}
        actions={
          <>
            <Link
              to="/prescription"
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-line-strong bg-white px-4 text-sm font-medium text-ink-800 shadow-sm hover:bg-ink-50"
            >
              <FileText size={17} aria-hidden="true" /> Write prescription
            </Link>
            <Button icon={UserPlus} onClick={openNew} disabled={!selectedHospital}>
              Add doctor
            </Button>
          </>
        }
      />

      {successMessage && <Alert tone="success" onDismiss={() => setSuccessMessage("")}>{successMessage}</Alert>}
      {loadError && (
        <Alert
          tone={offlineMode ? "warning" : "danger"}
          title={offlineMode ? "Server unreachable" : undefined}
          action={<Button size="sm" variant="secondary" onClick={() => setReloadToken((token) => token + 1)}>Retry</Button>}
        >
          {loadError}
        </Alert>
      )}

      {!selectedHospital ? (
        <Card>
          <EmptyState icon={Hospital} title="No hospital selected" description="Choose a hospital in the header to see its doctors." />
        </Card>
      ) : (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Name, speciality or ID"
              label="Search doctors"
              className="w-full sm:max-w-sm"
            />
            <SegmentedControl
              label="Availability"
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: "all", label: `All (${hospitalDoctors.length})` },
                { value: "available", label: `Available (${availableDoctors})` },
                { value: "away", label: `On leave (${onLeaveDoctors})` },
              ]}
            />
          </div>

          {loading && hospitalDoctors.length === 0 ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => <div key={i} className="skeleton h-40 rounded-2xl" />)}
            </div>
          ) : filteredDoctors.length === 0 ? (
            <Card>
              <EmptyState
                icon={Stethoscope}
                title={hospitalDoctors.length === 0 ? "No doctors yet" : "No doctors match"}
                description={hospitalDoctors.length === 0 ? "Add the doctors who practise at this hospital." : "Try a different name, speciality or filter."}
                action={hospitalDoctors.length === 0 && <Button icon={UserPlus} onClick={openNew}>Add doctor</Button>}
              />
            </Card>
          ) : (
            <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filteredDoctors.map((doctor) => (
                <li key={doctor.id}>
                  <Card className="flex h-full flex-col">
                    <button type="button" onClick={() => setSelectedDoctor(doctor)} className="flex items-start gap-3 px-5 pt-5 text-left">
                      <Avatar name={doctor.name} size="lg" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-semibold text-ink-900 hover:text-brand-700">{doctor.name}</span>
                        <span className="block truncate text-[13px] text-ink-600">{doctor.specialization || "Speciality not set"}</span>
                        <span className="mt-0.5 block text-xs text-ink-400 tabular-nums">{doctor.id}</span>
                      </span>
                      <StatusBadge status={doctor.status === "Available" ? "available" : doctor.status} label={doctor.status} />
                    </button>
                    <dl className="mt-4 grid grid-cols-1 gap-1.5 px-5 text-[13px] text-ink-600">
                      <div className="flex items-center gap-2"><dt className="sr-only">Availability</dt><Clock size={14} className="text-ink-400" aria-hidden="true" /><dd className="truncate">{doctor.availability || "Hours not set"}</dd></div>
                      <div className="flex items-center gap-2"><dt className="sr-only">Phone</dt><Phone size={14} className="text-ink-400" aria-hidden="true" /><dd className="tabular-nums">{doctor.phone || "—"}</dd></div>
                      <div className="flex items-center gap-2"><dt className="sr-only">Experience</dt><Briefcase size={14} className="text-ink-400" aria-hidden="true" /><dd className="truncate">{doctor.experience || "—"}</dd></div>
                    </dl>
                    <div className="mt-auto flex justify-end gap-1 border-t border-line px-3 py-2 pt-2">
                      <Button size="sm" variant="ghost" icon={Pencil} onClick={() => handleEdit(doctor)}>Edit</Button>
                      <Button size="icon-sm" variant="danger-ghost" icon={Trash2} onClick={() => setPendingDelete(doctor)} aria-label={`Delete ${doctor.name}`} title="Delete" />
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {/* Add / Edit */}
      <Modal
        open={showForm}
        onClose={resetForm}
        title={selectedDoctor ? `Edit ${selectedDoctor.name}` : "Add doctor"}
        description={selectedHospital ? `At ${selectedHospital.name}` : undefined}
        footer={
          <>
            <Button variant="secondary" onClick={resetForm} disabled={saving}>Cancel</Button>
            <Button type="submit" form="doctor-form" loading={saving}>{selectedDoctor ? "Save changes" : "Add doctor"}</Button>
          </>
        }
      >
        <form id="doctor-form" onSubmit={selectedDoctor ? handleUpdate : handleSubmit} className="space-y-4">
          {formError && <Alert tone="danger" title="Not saved">{formError}</Alert>}
          <Field label="Full name" required>
            <Input name="name" value={formData.name} onChange={handleChange} placeholder="Dr. …" />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Speciality" required>
              <Input name="specialization" value={formData.specialization} onChange={handleChange} />
            </Field>
            <Field label="Phone" required>
              <Input type="tel" name="phone" value={formData.phone} onChange={handleChange} />
            </Field>
            <Field label="Experience" required hint="e.g. 8 years">
              <Input name="experience" value={formData.experience} onChange={handleChange} />
            </Field>
            <Field label="Status">
              <Select name="status" value={formData.status} onChange={handleChange}>
                {DOCTOR_STATUSES.map((s) => <option key={s}>{s}</option>)}
                {!DOCTOR_STATUSES.includes(formData.status) && <option>{formData.status}</option>}
              </Select>
            </Field>
          </div>
          <Field label="OPD hours" required hint="e.g. Mon–Sat, 10:00–14:00">
            <Input name="availability" value={formData.availability} onChange={handleChange} />
          </Field>
        </form>
      </Modal>

      {/* Details */}
      <Modal
        open={Boolean(selectedDoctor) && !showForm && !pendingDelete}
        onClose={() => setSelectedDoctor(null)}
        title="Doctor details"
        footer={
          selectedDoctor && (
            <>
              <Button variant="danger-ghost" icon={Trash2} onClick={() => setPendingDelete(selectedDoctor)} className="mr-auto">Delete</Button>
              <Button variant="secondary" onClick={() => setSelectedDoctor(null)}>Close</Button>
              <Button icon={Pencil} onClick={() => handleEdit(selectedDoctor)}>Edit</Button>
            </>
          )
        }
      >
        {selectedDoctor && (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <Avatar name={selectedDoctor.name} size="lg" />
              <div>
                <p className="text-base font-semibold text-ink-900">{selectedDoctor.name}</p>
                <p className="text-[13px] text-ink-500">{selectedDoctor.specialization}</p>
              </div>
              <StatusBadge status={selectedDoctor.status === "Available" ? "available" : selectedDoctor.status} label={selectedDoctor.status} className="ml-auto" />
            </div>
            <DescriptionList
              items={[
                { label: "Doctor ID", value: selectedDoctor.id },
                { label: "Phone", value: selectedDoctor.phone },
                { label: "Experience", value: selectedDoctor.experience },
                { label: "OPD hours", value: selectedDoctor.availability },
              ]}
            />
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onCancel={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        loading={deleting}
        destructive
        title="Delete doctor?"
        confirmLabel="Delete doctor"
        message={
          <>
            Deleting <strong className="font-semibold text-ink-900">{pendingDelete?.name}</strong> also permanently deletes all of their
            appointments and schedules. This cannot be undone. To stop new bookings while keeping history, edit the doctor and set the status to
            <strong className="font-semibold text-ink-900"> On Leave</strong> instead.
          </>
        }
      />
    </div>
  )
}

export default Doctors
