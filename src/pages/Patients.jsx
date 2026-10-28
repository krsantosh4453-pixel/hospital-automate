import { useEffect, useMemo, useRef, useState } from "react"
import { Eye, Hospital, Pencil, Phone, Trash2, UserPlus, UsersRound } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import api from "../services/api.js"
import Pagination from "../components/Pagination.jsx"
import {
  Alert,
  Avatar,
  Badge,
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
  Select,
  SkeletonRows,
  TableWrap,
  Toolbar,
} from "../components/ui"

const EMPTY_FORM = {
  name: "", age: "", gender: "", phone: "", condition: "",
  emergencyName: "", emergencyRelation: "", emergencyPhone: "",
  dateOfBirth: "",
  maritalStatus: "",
  addressLine: "",
  city: "",
  district: "",
  state: "",
  pincode: "",
  idType: "",
  idLast4: "",
  payerType: "",
  payerName: "",
  policyNumber: "",
}

function Patients() {
  // Only the front desk registers patients; a Hospital Manager only views them.
  const { canAdd, canEdit } = useRole()
  const { selectedHospital } = usePatient()

  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalRecords, setTotalRecords] = useState(0)
  const pageSizeRef = useRef(50)

  // Display list, always loaded from the Django API. Nothing is kept in the
  // browser: a patient exists only once the server has saved it.
  const [patients, setPatients] = useState([])

  // Request + feedback state
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const [reloadToken, setReloadToken] = useState(0)

  // Add / Edit form state
  const [showForm, setShowForm] = useState(false)
  const [editingPatient, setEditingPatient] = useState(null)
  const [formData, setFormData] = useState(EMPTY_FORM)
  const [formErrors, setFormErrors] = useState({})
  const [saving, setSaving] = useState(false)

  // Read-only "View" and delete confirmation
  const [viewPatient, setViewPatient] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState("")

  // Maps a Django Patient record into the shape this UI already uses.
  const mapFromApi = (record) => ({
    id: record.id,
    name: record.name || "",
    age: record.age ?? "",
    gender: record.gender || "",
    phone: record.phone || "",
    condition: record.condition || "",
    emergencyName: record.emergency_contact_name || "",
    emergencyRelation: record.emergency_contact_relation || "",
    emergencyPhone: record.emergency_contact_phone || "",
    dateOfBirth: record.date_of_birth || "",
    maritalStatus: record.marital_status || "",
    addressLine: record.address_line || "",
    city: record.city || "",
    district: record.district || "",
    state: record.state || "",
    pincode: record.pincode || "",
    idType: record.id_type || "",
    idLast4: record.id_last4 || "",
    payerType: record.payer_type || "",
    payerName: record.payer_name || "",
    policyNumber: record.policy_number || "",
    doctor: record.doctor || "",
    status: record.status || "Active",
    hospitalId: record.hospital ?? selectedHospital?.id ?? "",
    source: "api",
  })

  // Keeps IDs readable whether they are Django integers or local "PAT-..."
  // strings, so "PAT-PAT-..." never happens.
  const formatPatientId = (patient) => {
    const value = String(patient?.id ?? "")
    return value.toUpperCase().startsWith("PAT-") ? value : `PAT-${value}`
  }

  // Auto-hide the success banner after a few seconds.
  useEffect(() => {
    if (!successMessage) return undefined
    const timer = setTimeout(() => setSuccessMessage(""), 4000)
    return () => clearTimeout(timer)
  }, [successMessage])

  // Search runs on the server (name / phone); wait for typing to pause.
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search.trim())
      setCurrentPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  // Back to page 1 when the hospital changes.
  useEffect(() => {
    setCurrentPage(1)
  }, [selectedHospital?.id])

  // Load patients from the Django API whenever the hospital, page or search changes.
  useEffect(() => {
    if (!selectedHospital) {
      setPatients([])
      setLoadError("")
      return undefined
    }

    let cancelled = false

    const loadPatients = async () => {
      setLoading(true)
      setLoadError("")

      try {
        const data = await api.patients.list(selectedHospital.id, currentPage, debouncedSearch)
        const results = Array.isArray(data) ? data : data?.results || []
        if (cancelled) return

        setPatients(results.map(mapFromApi))

        if (data && !Array.isArray(data)) {
          const count = data.count ?? results.length
          setTotalRecords(count)
          // The page size is set server-side; a page that has a next page is full.
          if (data.next && results.length > 0) pageSizeRef.current = results.length
          setTotalPages(data.next || data.previous ? Math.max(Math.ceil(count / pageSizeRef.current), currentPage) : 1)
        } else {
          setTotalRecords(results.length)
          setTotalPages(1)
        }
      } catch (error) {
        if (cancelled) return
        setPatients([])
        setLoadError(error.message || "Unable to reach the server. Patients could not be loaded.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadPatients()

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHospital, reloadToken, currentPage, debouncedSearch])

  // Selected hospital's patients
  const hospitalPatients = useMemo(() => {
    if (!selectedHospital) return []
    return patients.filter((patient) => String(patient.hospitalId) === String(selectedHospital.id))
  }, [patients, selectedHospital])

  // The server already applied the search.
  const filteredPatients = hospitalPatients

  // =====================================================
  // FORM HELPERS + VALIDATION
  // =====================================================

  const resetForm = () => {
    setFormData(EMPTY_FORM)
    setFormErrors({})
    setEditingPatient(null)
  }

  const openAddForm = () => {
    if (!selectedHospital) {
      setLoadError("Select a hospital before adding a patient.")
      return
    }
    resetForm()
    setShowForm(true)
  }

  const openEditForm = (patient) => {
    setEditingPatient(patient)
    setFormData({
      name: patient.name || "",
      age: patient.age ?? "",
      gender: patient.gender || "",
      phone: patient.phone || "",
      condition: patient.condition || "",
      emergencyName: patient.emergencyName || "",
      emergencyRelation: patient.emergencyRelation || "",
      emergencyPhone: patient.emergencyPhone || "",
      dateOfBirth: patient.dateOfBirth || "",
      maritalStatus: patient.maritalStatus || "",
      addressLine: patient.addressLine || "",
      city: patient.city || "",
      district: patient.district || "",
      state: patient.state || "",
      pincode: patient.pincode || "",
      idType: patient.idType || "",
      idLast4: patient.idLast4 || "",
      payerType: patient.payerType || "",
      payerName: patient.payerName || "",
      policyNumber: patient.policyNumber || "",
    })
    setFormErrors({})
    setViewPatient(null)
    setShowForm(true)
  }

  const closeForm = () => {
    setShowForm(false)
    resetForm()
  }

  const handleFormChange = (event) => {
    const { name, value } = event.target
    setFormData({ ...formData, [name]: value })
  }

  const validateForm = () => {
    const errors = {}

    if (!formData.name.trim()) errors.name = "Patient name is required."

    const ageValue = Number(formData.age)
    if (formData.age === "" || Number.isNaN(ageValue) || ageValue < 0 || ageValue > 130) {
      errors.age = "Enter an age between 0 and 130."
    }

    if (!formData.gender) errors.gender = "Please select a gender."

    const digits = String(formData.phone).replace(/\D/g, "")
    if (digits.length < 10) errors.phone = "Phone number must have at least 10 digits."

    const emergencyDigits = String(formData.emergencyPhone).replace(/\D/g, "")
    if (emergencyDigits && emergencyDigits.length < 10) {
      errors.emergencyPhone = "Phone number must have at least 10 digits."
    } else if (formData.emergencyName.trim() && !emergencyDigits) {
      errors.emergencyPhone = "Add a phone number for the emergency contact."
    }
    if (formData.pincode && !/^\d{6}$/.test(formData.pincode.trim())) errors.pincode = "A PIN code has 6 digits."
    if (formData.idLast4 && !/^[A-Za-z0-9]{4}$/.test(formData.idLast4.trim())) errors.idLast4 = "Enter only the last 4 characters."
    if (formData.idLast4 && !formData.idType) errors.idType = "Choose the type of ID."
    if (["Insurance", "Government scheme", "Corporate"].includes(formData.payerType) && !formData.payerName.trim()) {
      errors.payerName = "Name the insurer, scheme or company."
    }

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  // =====================================================
  // CREATE / UPDATE (POST / PUT)
  // =====================================================

  const handleSubmit = async (event, { confirmNew = false } = {}) => {
    event?.preventDefault()
    if (!validateForm()) return

    const payload = {
      name: formData.name.trim(),
      age: Number(formData.age),
      gender: formData.gender,
      phone: String(formData.phone).replace(/\D/g, ""),
      condition: formData.condition.trim(),
      emergency_contact_name: formData.emergencyName.trim(),
      emergency_contact_relation: formData.emergencyRelation.trim(),
      emergency_contact_phone: String(formData.emergencyPhone).replace(/\D/g, ""),
      // Demographics (B3); empty strings clear a field, a missing DOB is null.
      date_of_birth: formData.dateOfBirth || null,
      marital_status: String(formData.maritalStatus).trim(),
      address_line: String(formData.addressLine).trim(),
      city: String(formData.city).trim(),
      district: String(formData.district).trim(),
      state: String(formData.state).trim(),
      pincode: String(formData.pincode).trim(),
      id_type: String(formData.idType).trim(),
      id_last4: String(formData.idLast4).trim(),
      payer_type: String(formData.payerType).trim(),
      payer_name: String(formData.payerName).trim(),
      policy_number: String(formData.policyNumber).trim(),
      hospital: selectedHospital?.id ?? null,
    }

    setSaving(true)
    setLoadError("")

    try {
      if (editingPatient) {
        const updated = await api.patients.update(editingPatient.id, payload)
        setPatients((prev) =>
          prev.map((patient) => (String(patient.id) === String(editingPatient.id) ? mapFromApi(updated) : patient)),
        )
        setSuccessMessage("Patient updated successfully.")
      } else {
        const created = await api.patients.create(confirmNew ? { ...payload, confirm_new: true } : payload)
        setPatients((prev) => [mapFromApi(created), ...prev])
        setTotalRecords((n) => n + 1)
        setSuccessMessage("Patient added successfully.")
      }

      closeForm()
    } catch (error) {
      // Refused, unreachable or timed out: keep the form open and say so.
      // Nothing is saved in the browser. After a timeout the server may
      // already have saved it, so the list is reloaded to show the truth.
      if (error.status === 409 && Array.isArray(error.body?.duplicates)) {
        // Same mobile number already registered here (B5): let staff choose.
        setFormErrors((prev) => ({ ...prev, _duplicates: error.body.duplicates }))
        return
      }
      setFormErrors((prev) => ({ ...prev, _server: `Not saved: ${error.message}` }))
      if (error.isTimeout) setReloadToken((value) => value + 1)
    } finally {
      setSaving(false)
    }
  }

  // =====================================================
  // DELETE
  // =====================================================

  const confirmDelete = async () => {
    const patient = pendingDelete
    if (!patient) return
    setDeleting(true)
    setLoadError("")

    try {
      await api.patients.delete(patient.id)
      setSuccessMessage("Patient deleted successfully.")
      setTotalRecords((n) => Math.max(n - 1, 0))
    } catch (error) {
      // Refused or unreachable: the patient still exists on the server.
      setLoadError(`Not deleted: ${error.message}`)
      setDeleting(false)
      setPendingDelete(null)
      if (error.isTimeout) setReloadToken((value) => value + 1)
      return
    }

    setPatients((prev) => prev.filter((item) => String(item.id) !== String(patient.id)))
    setDeleting(false)
    setPendingDelete(null)
    setDeleteConfirmText("")
    setViewPatient(null)
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Patients"
        description={
          selectedHospital
            ? `Patients registered at ${selectedHospital.name}.`
            : "Select a hospital from the header to see its patients."
        }
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Patients" }]}
        actions={
          canAdd("Patients") && (
            <Button icon={UserPlus} onClick={openAddForm} disabled={!selectedHospital}>
              Register patient
            </Button>
          )
        }
      />

      {successMessage && (
        <Alert tone="success" onDismiss={() => setSuccessMessage("")}>
          {successMessage}
        </Alert>
      )}

      {loadError && (
        <Alert
          tone="danger"
          action={
            <Button size="sm" variant="secondary" onClick={() => setReloadToken((value) => value + 1)}>
              Retry
            </Button>
          }
        >
          {loadError}
        </Alert>
      )}

      {!selectedHospital ? (
        <Card>
          <EmptyState icon={Hospital} title="No hospital selected" description="Choose a hospital in the header to manage its patients." />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <Toolbar
            actions={
              <p className="text-[13px] text-ink-500">
                <span className="font-semibold text-ink-800 tabular-nums">{totalRecords}</span>{" "}
                {debouncedSearch ? "matching" : "registered"} patient{totalRecords === 1 ? "" : "s"}
              </p>
            }
          >
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Search by name, phone or UHID"
              label="Search patients"
              className="w-full sm:max-w-sm"
            />
          </Toolbar>

          {loading && filteredPatients.length === 0 ? (
            <SkeletonRows rows={6} />
          ) : filteredPatients.length > 0 ? (
            <>
              {/* Desktop / tablet table */}
              <TableWrap className="hidden md:block">
                <table className="hms-table" aria-busy={loading}>
                  <caption className="sr-only">Patients at {selectedHospital.name}</caption>
                  <thead>
                    <tr>
                      <th scope="col">Patient</th>
                      <th scope="col" className="num">Age</th>
                      <th scope="col">Gender</th>
                      <th scope="col">Phone</th>
                      <th scope="col">Reason for visit</th>
                      <th scope="col">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPatients.map((patient) => (
                      <tr key={patient.id}>
                        <td>
                          <button
                            type="button"
                            onClick={() => setViewPatient(patient)}
                            className="flex items-center gap-3 text-left"
                          >
                            <Avatar name={patient.name} size="sm" />
                            <span>
                              <span className="block font-medium text-ink-900 hover:text-brand-700">{patient.name}</span>
                              <span className="block text-xs text-ink-500 tabular-nums">{formatPatientId(patient)}</span>
                            </span>
                          </button>
                        </td>
                        <td className="num tabular-nums">{patient.age}</td>
                        <td>{patient.gender}</td>
                        <td className="tabular-nums whitespace-nowrap">{patient.phone}</td>
                        <td className="max-w-[16rem]">
                          {patient.condition ? (
                            <span className="line-clamp-1">{patient.condition}</span>
                          ) : (
                            <span className="text-ink-400">—</span>
                          )}
                        </td>
                        <td>
                          <div className="flex items-center justify-end gap-0.5">
                            <Button variant="ghost" size="icon-sm" icon={Eye} onClick={() => setViewPatient(patient)} aria-label={`View ${patient.name}`} title="View" />
                            {canEdit("Patients") && <Button variant="ghost" size="icon-sm" icon={Pencil} onClick={() => openEditForm(patient)} aria-label={`Edit ${patient.name}`} title="Edit" />}
                            <Button variant="danger-ghost" size="icon-sm" icon={Trash2} onClick={() => setPendingDelete(patient)} aria-label={`Delete ${patient.name}`} title="Delete" />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>

              {/* Phone: stacked rows keep name, ID and phone visible */}
              <ul className="divide-y divide-ink-100 md:hidden">
                {filteredPatients.map((patient) => (
                  <li key={patient.id} className="flex items-center gap-3 px-4 py-3">
                    <Avatar name={patient.name} size="sm" />
                    <button type="button" onClick={() => setViewPatient(patient)} className="min-w-0 flex-1 text-left">
                      <span className="block truncate font-medium text-ink-900">{patient.name}</span>
                      <span className="block text-xs text-ink-500 tabular-nums">
                        {formatPatientId(patient)} · {patient.age} y · {patient.gender}
                      </span>
                      <span className="mt-0.5 flex items-center gap-1 text-xs text-ink-600 tabular-nums">
                        <Phone size={12} aria-hidden="true" /> {patient.phone}
                      </span>
                    </button>
                    {canEdit("Patients") && <Button variant="ghost" size="icon-sm" icon={Pencil} onClick={() => openEditForm(patient)} aria-label={`Edit ${patient.name}`} />}
                  </li>
                ))}
              </ul>

              {totalPages > 1 && (
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  totalRecords={totalRecords}
                  onPageChange={setCurrentPage}
                />
              )}
            </>
          ) : (
            <EmptyState
              icon={UsersRound}
              title={search ? "No patients match your search" : "No patients registered yet"}
              description={search ? "Try a different name or phone number." : "Registered patients for this hospital will appear here."}
              action={
                search ? (
                  <Button variant="secondary" onClick={() => setSearch("")}>Clear search</Button>
                ) : (
                  canAdd("Patients") && <Button icon={UserPlus} onClick={openAddForm}>Register patient</Button>
                )
              }
            />
          )}
        </Card>
      )}

      {/* Add / Edit Patient */}
      <Modal
        open={showForm}
        onClose={closeForm}
        title={editingPatient ? "Edit patient" : "Register patient"}
        description={selectedHospital ? `At ${selectedHospital.name}` : undefined}
        footer={
          <>
            <Button variant="secondary" onClick={closeForm} disabled={saving}>Cancel</Button>
            <Button type="submit" form="patient-form" loading={saving}>
              {editingPatient ? "Save changes" : "Register patient"}
            </Button>
          </>
        }
      >
        <form id="patient-form" onSubmit={handleSubmit} noValidate className="space-y-4">
          {formErrors._server && <Alert tone="danger" title="Not saved">{formErrors._server}</Alert>}
          {formErrors._duplicates && (
            <Alert tone="warning" title="This mobile number is already registered here">
              <ul className="mt-1 space-y-1">
                {formErrors._duplicates.map((match) => (
                  <li key={match.id} className="flex flex-wrap items-center justify-between gap-2">
                    <span>{match.name} · {match.age} y · {match.gender}</span>
                    <Button size="sm" variant="secondary" onClick={() => { closeForm(); setViewPatient(mapFromApi(match)) }}>
                      Use this patient
                    </Button>
                  </li>
                ))}
              </ul>
              <Button size="sm" variant="ghost" className="mt-2" loading={saving} onClick={() => handleSubmit(null, { confirmNew: true })}>
                Different person: register anyway
              </Button>
            </Alert>
          )}
          <Field label="Full name" required error={formErrors.name}>
            <Input name="name" value={formData.name} onChange={handleFormChange} placeholder="As on ID document" autoComplete="off" />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Age (years)" required error={formErrors.age}>
              <Input type="number" inputMode="numeric" min="0" max="130" name="age" value={formData.age} onChange={handleFormChange} />
            </Field>
            <Field label="Gender" required error={formErrors.gender}>
              <Select name="gender" value={formData.gender} onChange={handleFormChange}>
                <option value="">Select</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </Select>
            </Field>
          </div>
          <Field label="Mobile number" required error={formErrors.phone} hint="10-digit number; used for appointment and token updates.">
            <Input type="tel" inputMode="tel" name="phone" value={formData.phone} onChange={handleFormChange} autoComplete="off" />
          </Field>
          <Field label="Reason for visit">
            <Input name="condition" value={formData.condition} onChange={handleFormChange} placeholder="e.g. fever for 3 days" />
          </Field>
          <fieldset className="space-y-3 rounded-xl border border-line px-4 pb-4 pt-2">
            <legend className="px-1 text-[13px] font-medium text-ink-700">Emergency contact (optional)</legend>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Name">
                <Input name="emergencyName" value={formData.emergencyName} onChange={handleFormChange} maxLength={100} autoComplete="off" />
              </Field>
              <Field label="Relation">
                <Input name="emergencyRelation" value={formData.emergencyRelation} onChange={handleFormChange} maxLength={50} placeholder="e.g. spouse" />
              </Field>
            </div>
            <Field label="Phone" error={formErrors.emergencyPhone}>
              <Input type="tel" inputMode="tel" name="emergencyPhone" value={formData.emergencyPhone} onChange={handleFormChange} autoComplete="off" />
            </Field>
          </fieldset>
          <details className="rounded-xl border border-line px-4 py-2" open={Boolean(formErrors.pincode || formErrors.idLast4 || formErrors.idType || formErrors.payerName)}>
            <summary className="cursor-pointer py-1 text-[13px] font-medium text-ink-700">More details (optional)</summary>
            <div className="mt-3 space-y-3 pb-2">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Date of birth">
                  <Input type="date" name="dateOfBirth" value={formData.dateOfBirth} onChange={handleFormChange} max={new Date().toISOString().slice(0, 10)} />
                </Field>
                <Field label="Marital status">
                  <Select name="maritalStatus" value={formData.maritalStatus} onChange={handleFormChange}>
                    <option value="">Not recorded</option>
                    {["Single", "Married", "Widowed", "Divorced", "Separated"].map((v) => <option key={v}>{v}</option>)}
                  </Select>
                </Field>
              </div>
              <Field label="Address">
                <Input name="addressLine" value={formData.addressLine} onChange={handleFormChange} maxLength={200} placeholder="House, street, locality" />
              </Field>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Field label="City / village"><Input name="city" value={formData.city} onChange={handleFormChange} maxLength={80} /></Field>
                <Field label="District"><Input name="district" value={formData.district} onChange={handleFormChange} maxLength={80} /></Field>
                <Field label="State"><Input name="state" value={formData.state} onChange={handleFormChange} maxLength={80} /></Field>
                <Field label="PIN code" error={formErrors.pincode}><Input name="pincode" inputMode="numeric" value={formData.pincode} onChange={handleFormChange} maxLength={6} /></Field>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="ID type" error={formErrors.idType}>
                  <Select name="idType" value={formData.idType} onChange={handleFormChange}>
                    <option value="">None</option>
                    {["Aadhaar", "PAN", "Voter ID", "Passport", "Driving licence", "ABHA", "Other"].map((v) => <option key={v}>{v}</option>)}
                  </Select>
                </Field>
                <Field label="Last 4 of ID" error={formErrors.idLast4} hint="Only the last 4 characters are kept, never the full number.">
                  <Input name="idLast4" value={formData.idLast4} onChange={handleFormChange} maxLength={4} autoComplete="off" />
                </Field>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Field label="Who pays">
                  <Select name="payerType" value={formData.payerType} onChange={handleFormChange}>
                    <option value="">Not recorded</option>
                    {["Self", "Insurance", "Government scheme", "Corporate"].map((v) => <option key={v}>{v}</option>)}
                  </Select>
                </Field>
                <Field label="Insurer / scheme / company" error={formErrors.payerName}><Input name="payerName" value={formData.payerName} onChange={handleFormChange} maxLength={120} /></Field>
                <Field label="Policy / card number"><Input name="policyNumber" value={formData.policyNumber} onChange={handleFormChange} maxLength={60} /></Field>
              </div>
            </div>
          </details>
        </form>
      </Modal>

      {/* Patient details */}
      <Modal
        open={Boolean(viewPatient)}
        onClose={() => setViewPatient(null)}
        title="Patient details"
        footer={
          viewPatient && (
            <>
              <Button variant="danger-ghost" icon={Trash2} onClick={() => setPendingDelete(viewPatient)} className="mr-auto">
                Delete
              </Button>
              <Button variant="secondary" onClick={() => setViewPatient(null)}>Close</Button>
              {canEdit("Patients") && <Button icon={Pencil} onClick={() => openEditForm(viewPatient)}>Edit</Button>}
            </>
          )
        }
      >
        {viewPatient && (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <Avatar name={viewPatient.name} size="lg" />
              <div>
                <p className="text-base font-semibold text-ink-900">{viewPatient.name}</p>
                <p className="text-[13px] text-ink-500 tabular-nums">{formatPatientId(viewPatient)}</p>
              </div>
              {viewPatient.source !== "api" && <Badge tone="warning" className="ml-auto">Saved locally only</Badge>}
            </div>
            <DescriptionList
              items={[
                { label: "Age", value: viewPatient.age !== "" ? `${viewPatient.age} years` : "" },
                { label: "Gender", value: viewPatient.gender },
                { label: "Mobile", value: viewPatient.phone },
                { label: "Reason for visit", value: viewPatient.condition },
                { label: "Date of birth", value: viewPatient.dateOfBirth },
                { label: "Marital status", value: viewPatient.maritalStatus },
                {
                  label: "Address",
                  value: [viewPatient.addressLine, viewPatient.city, viewPatient.district, viewPatient.state, viewPatient.pincode].filter(Boolean).join(", "),
                },
                { label: "ID", value: viewPatient.idType ? `${viewPatient.idType} ending ${viewPatient.idLast4 || "—"}` : "" },
                { label: "Payer", value: [viewPatient.payerType, viewPatient.payerName, viewPatient.policyNumber].filter(Boolean).join(" · ") },
                {
                  label: "Emergency contact",
                  value: [viewPatient.emergencyName, viewPatient.emergencyRelation && `(${viewPatient.emergencyRelation})`, viewPatient.emergencyPhone]
                    .filter(Boolean)
                    .join(" "),
                },
              ]}
            />
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onCancel={() => {
          setPendingDelete(null)
          setDeleteConfirmText("")
        }}
        onConfirm={confirmDelete}
        loading={deleting}
        destructive
        title="Permanently delete patient?"
        confirmLabel="Delete patient and records"
        confirmDisabled={
          pendingDelete?.source === "api" &&
          deleteConfirmText.trim().toLowerCase() !== String(pendingDelete?.name || "").trim().toLowerCase()
        }
        message={
          <>
            Deleting <strong className="font-semibold text-ink-900">{pendingDelete?.name}</strong> (
            {pendingDelete && formatPatientId(pendingDelete)}) also permanently deletes their visits, clinical notes, prescriptions, medication
            records, lab tests, admissions, invoices and consent records. This cannot be undone. Use it only for a registration made in error.
          </>
        }
      >
        {pendingDelete?.source === "api" && (
          <div className="mt-4">
            <label htmlFor="confirm-patient-name" className="hms-label">
              Type the patient&apos;s name to confirm
            </label>
            <input
              id="confirm-patient-name"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              autoComplete="off"
              className="hms-input w-full"
            />
          </div>
        )}
      </ConfirmDialog>
    </div>
  )
}

export default Patients
