import { useEffect, useMemo, useState } from "react"

import { usePatient } from "../assets/context/PatientContext.jsx"
import { usePrescription } from "../assets/context/PrescriptionContext.jsx"
import api from "../services/api.js"


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

const statusClass = (status) => {
  switch (status) {
    case "Dispensed":
      return "bg-emerald-50 text-emerald-700"
    case "Pending":
      return "bg-amber-50 text-amber-700"
    case "Cancelled":
      return "bg-red-50 text-red-600"
    default:
      return "bg-blue-50 text-blue-700"
  }
}


function Prescription() {
  const { selectedHospital } = usePatient()

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

  const refresh = () => setReloadToken((token) => token + 1)

  // ---------------------------------------------------------
  // LOAD DROPDOWN OPTIONS for the selected hospital
  // ---------------------------------------------------------
  useEffect(() => {
    let cancelled = false

    const loadOptions = async () => {
      if (!selectedHospital) {
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
  }, [selectedHospital, reloadToken])

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
      setActionError(
        "This record is only cached locally and cannot be deleted on the server."
      )
      return
    }

    const confirmed = window.confirm(
      `Delete prescription ${record.id}? This cannot be undone.`
    )

    if (!confirmed) {
      return
    }

    try {
      await deletePrescription(record.apiId)
      setSuccessMessage(`Prescription ${record.id} deleted.`)
    } catch (err) {
      setActionError(err?.message || "Unable to delete the prescription.")
    }
  }

  // ---------------------------------------------------------
  // Hospital gate
  // ---------------------------------------------------------
  if (!selectedHospital) {
    return (
      <div className="p-4 md:p-6 space-y-6 bg-slate-50 min-h-screen">
        <Header
          hospitalName="No hospital selected"
          onRefresh={refresh}
          disabled
        />
        <EmptyState text="Select a hospital to manage prescriptions." />
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 space-y-6 bg-slate-50 min-h-screen">

      {/* =========================
          Header
      ========================= */}
      <Header
        hospitalName={selectedHospital.name}
        onRefresh={refresh}
        disabled={loading}
      />

      {/* =========================
          Banners
      ========================= */}
      {successMessage && (
        <Banner tone="success">{successMessage}</Banner>
      )}

      {(error || actionError) && (
        <Banner tone="error">
          {actionError || error}
          <button
            type="button"
            onClick={refresh}
            className="ml-3 underline font-semibold cursor-pointer"
          >
            Retry
          </button>
        </Banner>
      )}

      {usingFallback && !error && (
        <Banner tone="info">
          The server is currently unreachable; the list below may be out of date. Changes cannot be saved until it reconnects.
        </Banner>
      )}

      {/* =========================
          Create form
      ========================= */}
      <section className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
        <h2 className="text-lg font-bold text-slate-800 mb-1">
          New Prescription
        </h2>
        <p className="text-xs text-slate-500 mb-4">
          Patient → Visit → Doctor → Medicines. Everything is saved to the
          Django backend.
        </p>

        {formError && (
          <div className="mb-4 rounded-xl bg-red-50 text-red-600 text-sm px-4 py-2">
            {formError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <FieldSelect
              label="Patient *"
              value={form.patientId}
              onChange={(value) => setField("patientId", value)}
              options={patients}
              placeholder={
                loadingOptions ? "Loading…" : "Select patient"
              }
            />

            <FieldSelect
              label="Visit"
              value={form.visitId}
              onChange={handleVisitChange}
              options={visits}
              placeholder={
                loadingOptions ? "Loading…" : "Select visit (optional)"
              }
            />

            <FieldSelect
              label="Doctor"
              value={form.doctorId}
              onChange={(value) => setField("doctorId", value)}
              options={doctors}
              placeholder={
                loadingOptions ? "Loading…" : "Select doctor (optional)"
              }
            />

            <FieldSelect
              label="Status"
              value={form.status}
              onChange={(value) => setField("status", value)}
              options={PRESCRIPTION_STATUSES.map((status) => ({
                value: status,
                label: status,
              }))}
            />
          </div>

          {/* Medicines */}
          <div className="border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-slate-700">
                Medicines
              </h3>
              <button
                type="button"
                onClick={addMedicineRow}
                className="px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-600 text-xs font-medium cursor-pointer"
              >
                + Add Medicine
              </button>
            </div>

            <div className="space-y-3">
              {form.medicines.map((medicine, index) => (
                <div
                  key={index}
                  className="grid grid-cols-1 md:grid-cols-6 gap-3 items-end bg-slate-50 rounded-xl p-3"
                >
                  <Field
                    label="Name *"
                    value={medicine.name}
                    onChange={(value) =>
                      setMedicineField(index, "name", value)
                    }
                    placeholder="e.g. Paracetamol 500mg"
                    className="md:col-span-2"
                  />

                  <Field
                    label="Dosage"
                    value={medicine.dosage}
                    onChange={(value) =>
                      setMedicineField(index, "dosage", value)
                    }
                    placeholder="500 mg"
                  />

                  <Field
                    label="Frequency"
                    value={medicine.frequency}
                    onChange={(value) =>
                      setMedicineField(index, "frequency", value)
                    }
                    placeholder="1-0-1"
                  />

                  <Field
                    label="Duration"
                    value={medicine.duration}
                    onChange={(value) =>
                      setMedicineField(index, "duration", value)
                    }
                    placeholder="5 days"
                  />

                  <div className="flex gap-2 items-end">
                    <Field
                      label="Qty *"
                      type="number"
                      value={medicine.quantity}
                      onChange={(value) =>
                        setMedicineField(index, "quantity", value)
                      }
                      className="w-20"
                    />

                    <button
                      type="button"
                      onClick={() => removeMedicineRow(index)}
                      disabled={form.medicines.length === 1}
                      className="mb-0.5 px-3 py-2 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 text-xs font-medium cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Remove medicine"
                    >
                      ✕
                    </button>
                  </div>

                  <Field
                    label="Instructions"
                    value={medicine.instructions}
                    onChange={(value) =>
                      setMedicineField(index, "instructions", value)
                    }
                    placeholder="After food"
                    className="md:col-span-6"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? "Saving…" : "Save Prescription"}
            </button>
          </div>
        </form>

        {/* Additive note — the AI Assisted Prescription card is intentionally
            kept on the Doctors screen untouched. */}
        <div className="mt-4 rounded-xl bg-slate-50 border border-slate-200 px-4 py-3">
          <p className="text-xs text-slate-500">
            AI Assisted Prescription remains available on the Doctors screen and
            is unchanged. Automated AI suggestions are planned as a separate
            task.
          </p>
        </div>
      </section>

      {/* =========================
          Existing prescriptions
      ========================= */}
      <section className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
          <h2 className="text-lg font-bold text-slate-800">
            Prescriptions ({filteredPrescriptions.length})
          </h2>

          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by ID, patient, doctor…"
            className="w-full md:w-72 border border-slate-300 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {loading && (
          <p className="text-sm text-slate-500 py-6 text-center">
            Loading prescriptions…
          </p>
        )}

        {!loading && filteredPrescriptions.length === 0 && (
          <EmptyState
            text={
              search
                ? "No prescriptions match your search."
                : "No prescriptions for this hospital yet."
            }
          />
        )}

        <div className="space-y-4">
          {!loading &&
            filteredPrescriptions.map((record) => (
              <article
                key={record.apiId || record.id}
                className="border border-slate-200 rounded-2xl p-4"
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-slate-800">
                        {record.id}
                      </h3>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${statusClass(
                          record.status
                        )}`}
                      >
                        {record.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Patient: {record.patientName || "—"} · Doctor:{" "}
                      {record.doctor || "—"} · Date:{" "}
                      {formatDate(record.createdAt)}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    {record.status !== "Dispensed" && (
                      <button
                        type="button"
                        onClick={() => handleDispense(record)}
                        className="px-3 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-medium cursor-pointer"
                      >
                        Dispense
                      </button>
                    )}

                    {record.apiId && (
                      <button
                        type="button"
                        onClick={() => handleDelete(record)}
                        className="px-3 py-1.5 rounded-lg bg-red-50 hover:bg-red-100 text-red-600 text-xs font-medium cursor-pointer"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>

                {(record.medicines || []).length > 0 && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-slate-500 uppercase tracking-wide">
                          <th className="py-1 pr-4">Medicine</th>
                          <th className="py-1 pr-4">Dosage</th>
                          <th className="py-1 pr-4">Frequency</th>
                          <th className="py-1 pr-4">Duration</th>
                          <th className="py-1 pr-4">Qty</th>
                          <th className="py-1">Instructions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {record.medicines.map((medicine, index) => (
                          <tr
                            key={medicine.id || index}
                            className="border-t border-slate-100 text-slate-700"
                          >
                            <td className="py-1.5 pr-4 font-medium">
                              {medicine.name}
                            </td>
                            <td className="py-1.5 pr-4">
                              {medicine.dosage || "—"}
                            </td>
                            <td className="py-1.5 pr-4">
                              {medicine.frequency || "—"}
                            </td>
                            <td className="py-1.5 pr-4">
                              {medicine.duration || "—"}
                            </td>
                            <td className="py-1.5 pr-4">
                              {medicine.quantity}
                            </td>
                            <td className="py-1.5">
                              {medicine.instructions || "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </article>
            ))}
        </div>
      </section>
    </div>
  )
}


// =========================================================
// PRESENTATIONAL HELPERS
// =========================================================

function Header({ hospitalName, onRefresh, disabled }) {
  return (
    <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">
          Prescription
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Create and manage prescriptions ·{" "}
          <span className="font-semibold text-blue-600">
            {hospitalName}
          </span>
        </p>
      </div>

      <button
        type="button"
        onClick={onRefresh}
        disabled={disabled}
        className="px-4 py-2 rounded-xl bg-white border border-slate-300 hover:bg-slate-100 text-sm font-medium text-slate-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
      >
        ⟳ Refresh
      </button>
    </header>
  )
}

function Banner({ tone = "info", children }) {
  const tones = {
    success: "bg-emerald-50 text-emerald-700",
    error: "bg-red-50 text-red-600",
    info: "bg-amber-50 text-amber-700",
  }

  return (
    <div
      className={`rounded-xl px-4 py-2 text-sm ${tones[tone] || tones.info}`}
    >
      {children}
    </div>
  )
}

function Field({ label, value, onChange, type = "text", placeholder, className = "" }) {
  return (
    <div className={className}>
      <label className="block text-xs font-semibold text-slate-500 mb-1">
        {label}
      </label>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="w-full border border-slate-300 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  )
}

function FieldSelect({ label, value, onChange, options, placeholder }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-500 mb-1">
        {label}
      </label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full border border-slate-300 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 bg-white"
      >
        <option value="">{placeholder || "Select…"}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function EmptyState({ text }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
      <p className="text-sm text-slate-500">{text}</p>
    </div>
  )
}

export default Prescription
