import { useEffect, useMemo, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import Pagination from "../components/Pagination.jsx"

function Patients() {
  const {
    selectedHospital,
    getHospitalPatients,
    addPatient: addLocalPatient,
    updatePatient: updateLocalPatient,
    deletePatient: deleteLocalPatient,
  } = usePatient()

  const [search, setSearch] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalRecords, setTotalRecords] = useState(0)

  // Display list. Loaded from the Django API when reachable, otherwise it
  // falls back to the localStorage-backed PatientContext data.
  const [patients, setPatients] = useState([])

  // Request + feedback state
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const [offlineMode, setOfflineMode] = useState(false)
  const [reloadToken, setReloadToken] = useState(0)

  // Add / Edit form state
  const [showForm, setShowForm] = useState(false)
  const [editingPatient, setEditingPatient] = useState(null)
  const [formData, setFormData] = useState({
    name: "",
    age: "",
    gender: "",
    phone: "",
    condition: "",
  })
  const [formErrors, setFormErrors] = useState({})
  const [saving, setSaving] = useState(false)

  // Read-only "View" modal state
  const [viewPatient, setViewPatient] = useState(null)

  // Last-resort demo dataset so the UI still renders something when both
  // the API and localStorage are empty.
  // No demo records: the page shows only data returned by the API.
  const fallbackPatients = []

  // Maps a Django Patient record into the shape this UI already uses.
  const mapFromApi = (record) => ({
    id: record.id,
    name: record.name || "",
    age: record.age ?? "",
    gender: record.gender || "",
    phone: record.phone || "",
    condition: record.condition || "",
    doctor: record.doctor || "",
    status: record.status || "Active",
    hospitalId: record.hospital ?? selectedHospital?.id ?? "",
    source: "api",
  })

  // Keeps IDs readable whether they are Django integers or local "PAT-..."
  // strings, so "PAT-PAT-..." never happens.
  const formatPatientId = (patient) => {
    const value = String(patient?.id ?? "")
    return value.toUpperCase().startsWith("PAT-")
      ? value
      : `PAT-${value}`
  }

  const showSuccess = (message) => {
    setSuccessMessage(message)
  }

  // Auto-hide the success banner after a few seconds.
  useEffect(() => {
    if (!successMessage) {
      return
    }

    const timer = setTimeout(
      () => setSuccessMessage(""),
      4000
    )

    return () => clearTimeout(timer)
  }, [successMessage])

  // Load patients from the Django API whenever the hospital changes.
  useEffect(() => {
    if (!selectedHospital) {
      setPatients([])
      setLoadError("")
      setOfflineMode(false)
      return
    }

    let cancelled = false

    const loadPatients = async () => {
      setLoading(true)
      setLoadError("")

      try {
        const data = await api.patients.list(
          selectedHospital.id,
          currentPage
        )

        const results = Array.isArray(data)
          ? data
          : data?.results || []

        if (cancelled) {
          return
        }

        setPatients(results.map(mapFromApi))

        // Handle pagination
        if (data && !Array.isArray(data)) {
          setTotalRecords(data.count || results.length)
          const pageSize = results.length || 10
          setTotalPages(Math.ceil((data.count || results.length) / pageSize))
        }

        setOfflineMode(false)
      } catch (error) {
        if (cancelled) {
          return
        }

        // Fall back to localStorage so existing behaviour keeps working.
        const localPatients = getHospitalPatients(
          selectedHospital.id
        )

        const demoPatients = fallbackPatients.filter(
          (patient) =>
            String(patient.hospitalId) ===
            String(selectedHospital.id)
        )

        setPatients(
          localPatients.length > 0
            ? localPatients
            : demoPatients
        )

        setOfflineMode(true)
        setLoadError(
          error.message ||
          "Unable to reach the server. Showing locally saved patients."
        )
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadPatients()

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHospital, reloadToken])

  // Selected hospital ke patients
  const hospitalPatients = useMemo(() => {
    if (!selectedHospital) {
      return []
    }

    return patients.filter(
      (patient) =>
        String(patient.hospitalId) ===
        String(selectedHospital.id)
    )
  }, [patients, selectedHospital])

  // Search
  const filteredPatients = hospitalPatients.filter(
    (patient) =>
      `${patient.name || ""} ${patient.phone || ""} ${patient.condition || ""
        }`
        .toLowerCase()
        .includes(search.toLowerCase())
  )

  // =====================================================
  // FORM HELPERS + VALIDATION
  // =====================================================

  const resetForm = () => {
    setFormData({
      name: "",
      age: "",
      gender: "",
      phone: "",
      condition: "",
    })
    setFormErrors({})
    setEditingPatient(null)
  }

  const openAddForm = () => {
    if (!selectedHospital) {
      setLoadError(
        "Select a hospital before adding a patient."
      )
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
    })
    setFormErrors({})
    setShowForm(true)
  }

  const closeForm = () => {
    setShowForm(false)
    resetForm()
  }

  const handleFormChange = (event) => {
    const { name, value } = event.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }

  const validateForm = () => {
    const errors = {}

    if (!formData.name.trim()) {
      errors.name = "Patient name is required."
    }

    const ageValue = Number(formData.age)

    if (
      formData.age === "" ||
      Number.isNaN(ageValue) ||
      ageValue < 0 ||
      ageValue > 130
    ) {
      errors.age = "Enter an age between 0 and 130."
    }

    if (!formData.gender) {
      errors.gender = "Please select a gender."
    }

    const digits = String(formData.phone).replace(/\D/g, "")

    if (digits.length < 10) {
      errors.phone = "Phone number must have at least 10 digits."
    }

    setFormErrors(errors)

    return Object.keys(errors).length === 0
  }

  // =====================================================
  // CREATE / UPDATE (POST / PUT)
  // =====================================================

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!validateForm()) {
      return
    }

    const payload = {
      name: formData.name.trim(),
      age: Number(formData.age),
      gender: formData.gender,
      phone: String(formData.phone).replace(/\D/g, ""),
      condition: formData.condition.trim(),
      hospital: selectedHospital?.id ?? null,
    }

    setSaving(true)
    setLoadError("")

    try {
      if (editingPatient) {
        const updated = await api.patients.update(
          editingPatient.id,
          payload
        )

        setPatients((prev) =>
          prev.map((patient) =>
            String(patient.id) === String(editingPatient.id)
              ? mapFromApi(updated)
              : patient
          )
        )

        showSuccess("Patient updated successfully.")
      } else {
        const created = await api.patients.create(payload)

        setPatients((prev) => [
          mapFromApi(created),
          ...prev,
        ])

        showSuccess("Patient added successfully.")
      }

      setOfflineMode(false)
      closeForm()
    } catch (error) {
      // Backend unavailable: keep the feature working through the
      // localStorage-backed PatientContext (temporary compatibility).
      if (editingPatient) {
        updateLocalPatient(editingPatient.id, {
          ...payload,
          hospitalId: selectedHospital?.id,
        })

        setPatients((prev) =>
          prev.map((patient) =>
            String(patient.id) === String(editingPatient.id)
              ? {
                ...patient,
                ...payload,
                hospitalId:
                  selectedHospital?.id ?? patient.hospitalId,
              }
              : patient
          )
        )

        setLoadError(
          `Saved locally, but the server update failed: ${error.message}`
        )
      } else {
        const localPatient = addLocalPatient({
          ...payload,
          hospitalId: selectedHospital?.id,
        })

        setPatients((prev) => [
          {
            ...localPatient,
            hospitalId:
              localPatient.hospitalId ?? selectedHospital?.id,
          },
          ...prev,
        ])

        setLoadError(
          `Saved locally, but the server save failed: ${error.message}`
        )
      }

      setOfflineMode(true)
      closeForm()
    } finally {
      setSaving(false)
    }
  }

  // =====================================================
  // DELETE
  // =====================================================

  const handleDelete = async (patient) => {
    const confirmed = window.confirm(
      `Delete patient "${patient.name}"? This cannot be undone.`
    )

    if (!confirmed) {
      return
    }

    setLoadError("")

    try {
      await api.patients.delete(patient.id)

      showSuccess("Patient deleted successfully.")
      setOfflineMode(false)
    } catch (error) {
      // Remove locally so the UI stays consistent while offline.
      deleteLocalPatient(patient.id)
      setOfflineMode(true)
      setLoadError(
        `Removed locally, but the server delete failed: ${error.message}`
      )
    }

    setPatients((prev) =>
      prev.filter(
        (item) => String(item.id) !== String(patient.id)
      )
    )
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

        <div>

          <p className="text-blue-600 font-semibold text-sm">
            PATIENT MANAGEMENT
          </p>

          <h1 className="text-3xl font-bold text-gray-800 mt-1">
            Patients
          </h1>

          <p className="text-gray-500 mt-1">
            Manage patients for the selected hospital.
          </p>

        </div>


        <button
          onClick={openAddForm}
          className="px-5 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700"
        >
          + Add Patient
        </button>

      </div>


      {/* Feedback banners */}
      {successMessage && (

        <div className="bg-green-50 border border-green-200 text-green-700 rounded-2xl px-5 py-3 flex items-center justify-between gap-4">

          <span className="text-sm font-medium">
            ✅ {successMessage}
          </span>

          <button
            onClick={() => setSuccessMessage("")}
            className="text-green-700 hover:text-green-900 text-sm font-semibold"
          >
            ✕
          </button>

        </div>

      )}

      {loadError && (

        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl px-5 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">

          <span className="text-sm font-medium">
            {offlineMode ? "⚠️ " : "❌ "}
            {loadError}
          </span>

          <button
            onClick={() => setReloadToken((value) => value + 1)}
            className="px-4 py-2 bg-white border border-red-200 rounded-xl text-sm font-semibold hover:bg-red-100 self-start"
          >
            Retry
          </button>

        </div>

      )}


      {/* Hospital */}
      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">

        {selectedHospital ? (

          <div className="flex items-center gap-4">

            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">
              🏥
            </div>

            <div>

              <p className="text-xs text-gray-500">
                Current Hospital
              </p>

              <h2 className="font-bold text-gray-800">
                {selectedHospital.name}
              </h2>

              <p className="text-sm text-gray-500">
                📍 {selectedHospital.address}
              </p>

            </div>

          </div>

        ) : (

          <div className="text-orange-600">

            <p className="font-semibold">
              ⚠️ No hospital selected
            </p>

            <p className="text-sm mt-1">
              Select a hospital from the header first.
            </p>

          </div>

        )}

      </div>


      {/* Search + Stats */}
      {selectedHospital && (

        <>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

            <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">

              <p className="text-sm text-gray-500">
                Total Patients
              </p>

              <p className="text-3xl font-bold text-gray-800 mt-2">
                {hospitalPatients.length}
              </p>

            </div>


            <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">

              <p className="text-sm text-gray-500">
                Today&apos;s Patients
              </p>

              <p className="text-3xl font-bold text-blue-600 mt-2">
                {hospitalPatients.length}
              </p>

            </div>


            <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">

              <p className="text-sm text-gray-500">
                Search Results
              </p>

              <p className="text-3xl font-bold text-green-600 mt-2">
                {filteredPatients.length}
              </p>

            </div>

          </div>


          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">

            <div className="flex flex-col md:flex-row gap-4">

              <input
                type="text"
                value={search}
                onChange={(e) =>
                  setSearch(e.target.value)
                }
                placeholder="Search patient by name, phone or condition..."
                className="flex-1 border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              />

              <button
                onClick={() => setSearch("")}
                className="px-5 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200"
              >
                Clear
              </button>

            </div>

          </div>


          {/* Patient Table */}
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">

            <div className="p-5 border-b border-gray-100">

              <h2 className="text-lg font-bold text-gray-800">
                Hospital Patients
              </h2>

            </div>


            {loading ? (

              <div className="p-12 text-center">

                <div className="text-4xl mb-3 animate-pulse">
                  ⏳
                </div>

                <h3 className="font-bold text-gray-800">
                  Loading patients...
                </h3>

                <p className="text-sm text-gray-500 mt-1">
                  Fetching patient records from the server.
                </p>

              </div>

            ) : filteredPatients.length > 0 ? (

              <div className="overflow-x-auto">

                <table className="w-full">

                  <thead className="bg-gray-50">

                    <tr>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Patient
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Age
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Gender
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Phone
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Condition
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Action
                      </th>

                    </tr>

                  </thead>


                  <tbody>

                    {filteredPatients.map(
                      (patient) => (

                        <tr
                          key={patient.id}
                          className="border-t border-gray-100 hover:bg-gray-50"
                        >

                          <td className="px-5 py-4">

                            <div className="flex items-center gap-3">

                              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                                👤
                              </div>

                              <div>

                                <p className="font-semibold text-gray-800">
                                  {patient.name}
                                </p>

                                <p className="text-xs text-gray-500">
                                  ID: {formatPatientId(patient)}
                                </p>

                              </div>

                            </div>

                          </td>


                          <td className="px-5 py-4 text-sm text-gray-700">
                            {patient.age}
                          </td>


                          <td className="px-5 py-4 text-sm text-gray-700">
                            {patient.gender}
                          </td>


                          <td className="px-5 py-4 text-sm text-gray-700">
                            {patient.phone}
                          </td>


                          <td className="px-5 py-4">

                            <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                              {patient.condition}
                            </span>

                          </td>


                          <td className="px-5 py-4">

                            <div className="flex items-center gap-3">

                              <button
                                onClick={() => setViewPatient(patient)}
                                className="text-blue-600 font-medium text-sm hover:text-blue-800"
                              >
                                View
                              </button>

                              <button
                                onClick={() => openEditForm(patient)}
                                className="text-amber-600 font-medium text-sm hover:text-amber-800"
                              >
                                Edit
                              </button>

                              <button
                                onClick={() => handleDelete(patient)}
                                className="text-red-600 font-medium text-sm hover:text-red-800"
                              >
                                Delete
                              </button>

                            </div>

                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>

                {totalPages > 1 && (
                  <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    totalRecords={totalRecords}
                    onPageChange={setCurrentPage}
                  />
                )}

              </div>

            ) : (

              <div className="p-12 text-center">

                <div className="text-4xl mb-3">
                  👤
                </div>

                <h3 className="font-bold text-gray-800">
                  No patients found
                </h3>

                <p className="text-sm text-gray-500 mt-1">
                  There are no matching patients in this hospital.
                </p>

              </div>

            )}

          </div>

        </>

      )}


      {/* Add / Edit Patient Modal */}
      {showForm && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">

            <div className="p-5 border-b border-gray-100 flex items-center justify-between">

              <h2 className="text-lg font-bold text-gray-800">
                {editingPatient ? "Edit Patient" : "Add Patient"}
              </h2>

              <button
                onClick={closeForm}
                className="text-gray-400 hover:text-gray-700 text-xl font-semibold"
              >
                ✕
              </button>

            </div>


            <form
              onSubmit={handleSubmit}
              className="p-5 space-y-4"
            >

              <div>

                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Full Name
                </label>

                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleFormChange}
                  placeholder="Enter patient name"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />

                {formErrors.name && (
                  <p className="text-xs text-red-600 mt-1">
                    {formErrors.name}
                  </p>
                )}

              </div>


              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

                <div>

                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Age
                  </label>

                  <input
                    type="number"
                    name="age"
                    value={formData.age}
                    onChange={handleFormChange}
                    placeholder="Age"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                  />

                  {formErrors.age && (
                    <p className="text-xs text-red-600 mt-1">
                      {formErrors.age}
                    </p>
                  )}

                </div>


                <div>

                  <label className="block text-sm font-semibold text-gray-700 mb-1">
                    Gender
                  </label>

                  <select
                    name="gender"
                    value={formData.gender}
                    onChange={handleFormChange}
                    className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select gender</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>

                  {formErrors.gender && (
                    <p className="text-xs text-red-600 mt-1">
                      {formErrors.gender}
                    </p>
                  )}

                </div>

              </div>


              <div>

                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Phone
                </label>

                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleFormChange}
                  placeholder="10-digit mobile number"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />

                {formErrors.phone && (
                  <p className="text-xs text-red-600 mt-1">
                    {formErrors.phone}
                  </p>
                )}

              </div>


              <div>

                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Condition
                </label>

                <input
                  type="text"
                  name="condition"
                  value={formData.condition}
                  onChange={handleFormChange}
                  placeholder="Reason for visit"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>


              <div className="flex items-center justify-end gap-3 pt-2">

                <button
                  type="button"
                  onClick={closeForm}
                  className="px-5 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving
                    ? "Saving..."
                    : editingPatient
                      ? "Update Patient"
                      : "Add Patient"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}


      {/* View Patient Modal */}
      {viewPatient && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">

            <div className="p-5 border-b border-gray-100 flex items-center justify-between">

              <h2 className="text-lg font-bold text-gray-800">
                Patient Details
              </h2>

              <button
                onClick={() => setViewPatient(null)}
                className="text-gray-400 hover:text-gray-700 text-xl font-semibold"
              >
                ✕
              </button>

            </div>


            <div className="p-5 space-y-4">

              <div className="flex items-center gap-3">

                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-2xl">
                  👤
                </div>

                <div>

                  <p className="font-bold text-gray-800">
                    {viewPatient.name}
                  </p>

                  <p className="text-xs text-gray-500">
                    ID: {formatPatientId(viewPatient)}
                  </p>

                </div>

              </div>


              <div className="grid grid-cols-2 gap-3 text-sm">

                <div>

                  <p className="text-gray-500">Age</p>

                  <p className="font-semibold text-gray-800">
                    {viewPatient.age}
                  </p>

                </div>

                <div>

                  <p className="text-gray-500">Gender</p>

                  <p className="font-semibold text-gray-800">
                    {viewPatient.gender}
                  </p>

                </div>

                <div>

                  <p className="text-gray-500">Phone</p>

                  <p className="font-semibold text-gray-800">
                    {viewPatient.phone}
                  </p>

                </div>

                <div>

                  <p className="text-gray-500">Condition</p>

                  <p className="font-semibold text-gray-800">
                    {viewPatient.condition || "-"}
                  </p>

                </div>

              </div>


              <button
                onClick={() => setViewPatient(null)}
                className="w-full px-5 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200"
              >
                Close
              </button>

            </div>

          </div>

        </div>

      )}

    </div>
  )
}

export default Patients