import { useEffect, useMemo, useState } from "react"

import { usePatient } from "../assets/context/PatientContext.jsx"
import { usePrescription } from "../assets/context/PrescriptionContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import api from "../services/api.js"
import { FilePlus2, Hospital, PackageCheck, Pill, Plus, RefreshCw, Trash2, X } from "lucide-react"
import {
  Alert,
  Button,
  Card,
  CardHeader,
  ConfirmDialog,
  EmptyState,
  Field,
  Input,
  PageHeader,
  SearchInput,
  Select,
  SkeletonRows,
  StatusBadge,
  TableWrap,
} from "../components/ui"


// =========================================================
// HELPERS
// =========================================================

// Normalise a list response that may be a plain array or a paginated
// { count, next, previous, results } object (DRF default pagination).
const readResults = (data) =>
  Array.isArray(data) ? data : data?.results || []

// Turn an input string into a number or null (DRF numeric fields reject "").
const num = (value) => {
  if (value === "" || value === null || value === undefined) {
    return null
  }

  const parsed = Number(value)

  return Number.isNaN(parsed) ? null : parsed
}

const formatDate = (value) => {
  if (!value) return "—"

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return String(value)
  }

  return date.toLocaleDateString("en-IN")
}

// Build a dropdown option from a Django record. We always keep the real
// integer id as `value` so writes use stable database ids, never names.
const mapPatientOption = (record) => ({
  value: String(record.id),
  label: record.name
    ? `${record.name}${record.phone ? ` (${record.phone})` : ""}`
    : `Patient #${record.id}`,
})

const mapDoctorOption = (record) => ({
  value: String(record.id),
  label: record.name
    ? `${record.name}${record.specialization ? ` — ${record.specialization}` : ""}`
    : `Doctor #${record.id}`,
})

const mapVisitOption = (record) => ({
  value: String(record.id),
  label: `Visit #${record.id}${record.patient_name ? ` — ${record.patient_name}` : ""}`,
  patientId:
    record.patient !== null && record.patient !== undefined
      ? String(record.patient)
      : "",
})

const PRESCRIPTION_STATUSES = [
  "Confirmed",
  "Pending",
  "Dispensed",
  "Cancelled",
]

const emptyMedicine = () => ({
  name: "",
  dosage: "",
  frequency: "",
  duration: "",
  quantity: "1",
  instructions: "",
})

const emptyForm = () => ({
  patientId: "",
  visitId: "",
  doctorId: "",
  status: "Confirmed",
  medicines: [emptyMedicine()],
})

function Prescription() {
  const { selectedHospital } = usePatient()
  // Doctors write prescriptions; pharmacy and nursing staff only read them.
  const { canAdd } = useRole()
  const canWrite = canAdd("Prescriptions")

  const {
    prescriptions,
    dispensePrescription,
    getHospitalPrescriptions,
    loadPrescriptions,
    createPrescription,
    deletePrescription,
    loading,
    error,
    usingFallback,
  } = usePrescription()

  // ---------------------------------------------------------
  // Dropdown option state (patients / doctors / visits)
  // ---------------------------------------------------------
  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])
  const [visits, setVisits] = useState([])
  const [loadingOptions, setLoadingOptions] = useState(false)

  // ---------------------------------------------------------
  // Form + feedback state
  // ---------------------------------------------------------
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const [actionError, setActionError] = useState("")
  const [search, setSearch] = useState("")
  const [reloadToken, setReloadToken] = useState(0)
  const [pending, setPending] = useState(null) // { kind: 'dispense' | 'delete', record }
  const [working, setWorking] = useState(false)

  const refresh = () => setReloadToken((token) => token + 1)

  // ---------------------------------------------------------
  // LOAD DROPDOWN OPTIONS for the selected hospital
  // ---------------------------------------------------------
  useEffect(() => {
    let cancelled = false

    const loadOptions = async () => {
      if (!selectedHospital || !canWrite) {
        setPatients([])
        setDoctors([])
        setVisits([])
        return
      }

      setLoadingOptions(true)

      // Load all three in parallel. If one fails we still keep the others
      // so the form degrades gracefully instead of going blank.
      const [patientsResult, doctorsResult, visitsResult] =
        await Promise.allSettled([
          api.patients.list(selectedHospital.id),
          api.doctors.list(selectedHospital.id),
          api.visits.list(selectedHospital.id),
        ])

      if (cancelled) {
        return
      }

      setPatients(
        patientsResult.status === "fulfilled"
          ? readResults(patientsResult.value).map(mapPatientOption)
          : []
      )

      setDoctors(
        doctorsResult.status === "fulfilled"
          ? readResults(doctorsResult.value).map(mapDoctorOption)
          : []
      )

      setVisits(
        visitsResult.status === "fulfilled"
          ? readResults(visitsResult.value).map(mapVisitOption)
          : []
      )

      setLoadingOptions(false)
    }

    loadOptions()

    return () => {
      cancelled = true
    }
  }, [selectedHospital, reloadToken, canWrite])

  // ---------------------------------------------------------
  // LOAD PRESCRIPTIONS for the selected hospital
  // ---------------------------------------------------------
  useEffect(() => {
    if (!selectedHospital) {
      return
    }

    loadPrescriptions({ hospitalId: selectedHospital.id })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHospital, reloadToken])

  // ---------------------------------------------------------
  // Auto-dismiss the success banner
  // ---------------------------------------------------------
  useEffect(() => {
    if (!successMessage) {
      return undefined
    }

    const timer = setTimeout(() => setSuccessMessage(""), 4000)

    return () => clearTimeout(timer)
  }, [successMessage])

  // ---------------------------------------------------------
  // Derived: prescriptions for the current hospital + search
  // ---------------------------------------------------------
  const hospitalPrescriptions = useMemo(
    () => (selectedHospital ? getHospitalPrescriptions(selectedHospital.id) : []),
    [prescriptions, selectedHospital, getHospitalPrescriptions]
  )

  const filteredPrescriptions = useMemo(() => {
    const term = search.trim().toLowerCase()

    if (!term) {
      return hospitalPrescriptions
    }

    return hospitalPrescriptions.filter((record) => {
      const haystack = [
        record.id,
        record.patientName,
        record.doctor,
        record.status,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()

      return haystack.includes(term)
    })
  }, [hospitalPrescriptions, search])

  // ---------------------------------------------------------
  // Form field handlers
  // ---------------------------------------------------------
  const setField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const setMedicineField = (index, field, value) => {
    setForm((prev) => {
      const medicines = prev.medicines.map((medicine, i) =>
        i === index ? { ...medicine, [field]: value } : medicine
      )

      return { ...prev, medicines }
    })
  }

  const addMedicineRow = () => {
    setForm((prev) => ({
      ...prev,
      medicines: [...prev.medicines, emptyMedicine()],
    }))
  }

  const removeMedicineRow = (index) => {
    setForm((prev) => ({
      ...prev,
      medicines: prev.medicines.filter((_, i) => i !== index),
    }))
  }

  // Selecting a visit also selects the patient that visit belongs to so the
  // two dropdowns never contradict each other.
  const handleVisitChange = (value) => {
    setForm((prev) => {
      const match = visits.find((visit) => visit.value === value)

      return {
        ...prev,
        visitId: value,
        patientId: match?.patientId ? match.patientId : prev.patientId,
      }
    })
  }

  // ---------------------------------------------------------
  // VALIDATION (mirrors the backend serializer rules)
  // ---------------------------------------------------------
  const validate = () => {
    if (!selectedHospital) {
      return "Please select a hospital first."
    }

    if (!form.patientId) {
      return "Patient is required."
    }

    if (form.medicines.length === 0) {
      return "Add at least one medicine."
    }

    for (let index = 0; index < form.medicines.length; index += 1) {
      const medicine = form.medicines[index]

      if (!String(medicine.name || "").trim()) {
        return `Medicine ${index + 1}: name is required.`
      }

      const quantity = num(medicine.quantity)

      if (quantity === null || quantity < 1) {
        return `Medicine ${index + 1}: quantity must be at least 1.`
      }
    }

    return ""
  }

  // ---------------------------------------------------------
  // SUBMIT — persist via the API-backed context helper
  // ---------------------------------------------------------
  const handleSubmit = async (event) => {
    event.preventDefault()

    setFormError("")
    setActionError("")

    const validationError = validate()

    if (validationError) {
      setFormError(validationError)
      return
    }

    const payload = {
      hospital: selectedHospital.id,
      patient: num(form.patientId),
      doctor: num(form.doctorId) || null,
      visit: num(form.visitId) || null,
      status: form.status,
      items: form.medicines.map((medicine) => ({
        name: medicine.name.trim(),
        dosage: medicine.dosage || "",
        frequency: medicine.frequency || "",
        duration: medicine.duration || "",
        quantity: num(medicine.quantity) || 1,
        instructions: medicine.instructions || "",
      })),
    }

    setSaving(true)

    try {
      const created = await createPrescription(payload)

      setSuccessMessage(
        `Prescription ${created?.id || ""} created successfully.`
      )
      setForm(emptyForm())
    } catch (err) {
      setFormError(
        err?.message || "Unable to save the prescription. Please try again."
      )
    } finally {
      setSaving(false)
    }
  }

  // ---------------------------------------------------------
  // ACTIONS on an existing prescription
  // ---------------------------------------------------------
  const handleDispense = async (record) => {
    setActionError("")

    try {
      await dispensePrescription(record.id, selectedHospital?.id)
      setSuccessMessage(`Prescription ${record.id} marked as Dispensed.`)
    } catch (err) {
      setActionError(err.message || "Could not dispense this prescription.")
    }
  }

  const handleDelete = async (record) => {
    setActionError("")

    if (!record.apiId) {
      setActionError("This record is only cached locally and cannot be deleted on the server.")
      return
    }

    try {
      await deletePrescription(record.apiId)
      setSuccessMessage(`Prescription ${record.id} deleted.`)
    } catch (err) {
      setActionError(err?.message || "Unable to delete the prescription.")
    }
  }

  const runPending = async () => {
    if (!pending) return
    setWorking(true)
    if (pending.kind === "dispense") await handleDispense(pending.record)
    else await handleDelete(pending.record)
    setWorking(false)
    setPending(null)
  }

  const header = (
    <PageHeader
      title="Prescriptions"
      description={selectedHospital ? `Write and manage prescriptions at ${selectedHospital.name}.` : "Select a hospital to manage prescriptions."}
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Prescriptions" }]}
      actions={
        <Button variant="secondary" icon={RefreshCw} onClick={refresh} disabled={!selectedHospital || loading}>
          Refresh
        </Button>
      }
    />
  )

  // ---------------------------------------------------------
  // Hospital gate
  // ---------------------------------------------------------
  if (!selectedHospital) {
    return (
      <div className="space-y-5">
        {header}
        <Card>
          <EmptyState icon={Hospital} title="Select a hospital" description="Choose a hospital in the header to manage prescriptions." />
        </Card>
      </div>
    )
  }

  const optionList = (options, placeholder) => [
    <option key="" value="">{placeholder}</option>,
    ...options.map((option) => (
      <option key={option.value} value={option.value}>{option.label}</option>
    )),
  ]

  return (
    <div className="space-y-5">
      {header}

      {successMessage && <Alert tone="success" onDismiss={() => setSuccessMessage("")}>{successMessage}</Alert>}
      {(error || actionError) && (
        <Alert tone="danger" action={<Button size="sm" variant="secondary" onClick={refresh}>Retry</Button>}>
          {actionError || error}
        </Alert>
      )}
      {usingFallback && !error && (
        <Alert tone="warning" title="Server unreachable">
          The list below may be out of date. Changes cannot be saved until the server reconnects.
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[minmax(0,34rem)_minmax(0,1fr)]">
        {/* New prescription */}
        {canWrite && (
        <Card as="form" onSubmit={handleSubmit} className="self-start" noValidate>
          <CardHeader icon={FilePlus2} title="New prescription" description="Patient, visit and doctor, then one row per medicine." />
          <div className="space-y-5 px-5 py-4">
            {formError && <Alert tone="danger" title="Not saved">{formError}</Alert>}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Patient" required>
                <Select value={form.patientId} onChange={(e) => setField("patientId", e.target.value)}>
                  {optionList(patients, loadingOptions ? "Loading…" : "Select patient")}
                </Select>
              </Field>
              <Field label="Visit" hint="Optional; selects its patient">
                <Select value={form.visitId} onChange={(e) => handleVisitChange(e.target.value)}>
                  {optionList(visits, loadingOptions ? "Loading…" : "No visit")}
                </Select>
              </Field>
              <Field label="Doctor">
                <Select value={form.doctorId} onChange={(e) => setField("doctorId", e.target.value)}>
                  {optionList(doctors, loadingOptions ? "Loading…" : "Not specified")}
                </Select>
              </Field>
              <Field label="Status">
                <Select value={form.status} onChange={(e) => setField("status", e.target.value)}>
                  {PRESCRIPTION_STATUSES.map((status) => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </Select>
              </Field>
            </div>

            <fieldset className="space-y-3">
              <legend className="mb-2 flex w-full items-center justify-between text-sm font-semibold text-ink-900">
                Medicines
                <span className="text-xs font-normal text-ink-500">{form.medicines.length} item{form.medicines.length === 1 ? "" : "s"}</span>
              </legend>
              {form.medicines.map((medicine, index) => (
                <div key={index} className="rounded-xl border border-line bg-ink-50/60 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs font-semibold text-ink-500">Medicine {index + 1}</span>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      icon={X}
                      onClick={() => removeMedicineRow(index)}
                      disabled={form.medicines.length === 1}
                      aria-label={`Remove medicine ${index + 1}`}
                      title="Remove medicine"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-6">
                    <Field label="Name" required className="col-span-2 sm:col-span-4">
                      <Input value={medicine.name} onChange={(e) => setMedicineField(index, "name", e.target.value)} placeholder="Drug and strength" />
                    </Field>
                    <Field label="Qty" required className="sm:col-span-2">
                      <Input type="number" min="1" inputMode="numeric" value={medicine.quantity} onChange={(e) => setMedicineField(index, "quantity", e.target.value)} />
                    </Field>
                    <Field label="Dosage" className="sm:col-span-2">
                      <Input value={medicine.dosage} onChange={(e) => setMedicineField(index, "dosage", e.target.value)} placeholder="500 mg" />
                    </Field>
                    <Field label="Frequency" className="sm:col-span-2">
                      <Input value={medicine.frequency} onChange={(e) => setMedicineField(index, "frequency", e.target.value)} placeholder="1-0-1" />
                    </Field>
                    <Field label="Duration" className="col-span-2 sm:col-span-2">
                      <Input value={medicine.duration} onChange={(e) => setMedicineField(index, "duration", e.target.value)} placeholder="5 days" />
                    </Field>
                    <Field label="Instructions" className="col-span-2 sm:col-span-6">
                      <Input value={medicine.instructions} onChange={(e) => setMedicineField(index, "instructions", e.target.value)} placeholder="After food" />
                    </Field>
                  </div>
                </div>
              ))}
              <Button variant="subtle" size="sm" icon={Plus} onClick={addMedicineRow}>
                Add medicine
              </Button>
            </fieldset>

            <div className="flex items-center justify-between gap-3 border-t border-line pt-4">
              <p className="text-xs text-ink-500">There is no automatic drug-interaction check; review the full list before saving.</p>
              <Button type="submit" loading={saving}>Save prescription</Button>
            </div>
          </div>
        </Card>
        )}

        {/* Existing prescriptions */}
        <Card className="self-start overflow-hidden">
          <CardHeader
            icon={Pill}
            title="Prescriptions"
            description={`${filteredPrescriptions.length} shown`}
            actions={<SearchInput value={search} onChange={setSearch} placeholder="ID, patient, doctor, status" label="Search prescriptions" className="w-full sm:w-64" />}
          />
          {loading ? (
            <SkeletonRows rows={4} />
          ) : filteredPrescriptions.length === 0 ? (
            <EmptyState
              icon={Pill}
              title={search ? "No prescriptions match your search" : "No prescriptions yet"}
              description={search ? undefined : "Saved prescriptions for this hospital appear here."}
            />
          ) : (
            <ul className="divide-y divide-line">
              {filteredPrescriptions.map((record) => (
                <li key={record.apiId || record.id} className="px-5 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-ink-900 tabular-nums">{record.id}</p>
                        <StatusBadge status={record.status} />
                      </div>
                      <p className="mt-0.5 text-[13px] text-ink-500">
                        {record.patientName || "Unknown patient"} · {record.doctor || "No doctor"} · {formatDate(record.createdAt)}
                      </p>
                    </div>
                    <div className="flex gap-1.5">
                      {record.status !== "Dispensed" && (
                        <Button size="sm" variant="subtle" icon={PackageCheck} onClick={() => setPending({ kind: "dispense", record })}>
                          Dispense
                        </Button>
                      )}
                      {record.apiId && (
                        <Button size="icon-sm" variant="danger-ghost" icon={Trash2} onClick={() => setPending({ kind: "delete", record })} aria-label={`Delete prescription ${record.id}`} title="Delete" />
                      )}
                    </div>
                  </div>
                  {(record.medicines || []).length > 0 && (
                    <TableWrap className="mt-3 rounded-lg border border-line">
                      <table className="hms-table text-[13px]">
                        <thead>
                          <tr>
                            <th scope="col">Medicine</th>
                            <th scope="col">Dosage</th>
                            <th scope="col">Frequency</th>
                            <th scope="col">Duration</th>
                            <th scope="col" className="num">Qty</th>
                            <th scope="col">Instructions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {record.medicines.map((medicine, index) => (
                            <tr key={medicine.id || index}>
                              <td className="font-medium text-ink-900">{medicine.name}</td>
                              <td>{medicine.dosage || "—"}</td>
                              <td className="tabular-nums">{medicine.frequency || "—"}</td>
                              <td>{medicine.duration || "—"}</td>
                              <td className="num">{medicine.quantity}</td>
                              <td className="text-ink-600">{medicine.instructions || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </TableWrap>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <ConfirmDialog
        open={Boolean(pending)}
        onCancel={() => setPending(null)}
        onConfirm={runPending}
        loading={working}
        destructive={pending?.kind === "delete"}
        title={pending?.kind === "delete" ? "Delete prescription?" : "Mark as dispensed?"}
        confirmLabel={pending?.kind === "delete" ? "Delete" : "Mark dispensed"}
        message={
          pending?.kind === "delete"
            ? `Prescription ${pending?.record.id} for ${pending?.record.patientName || "this patient"} will be deleted. This cannot be undone.`
            : `Confirm that every medicine on prescription ${pending?.record.id} has been handed to ${pending?.record.patientName || "the patient"}.`
        }
      />
    </div>
  )
}

export default Prescription
