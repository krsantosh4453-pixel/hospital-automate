import { useState } from "react"
import { useHospitals } from "../../assets/context/HospitalsContext.jsx"

function Hospitals() {
  const {
    hospitals,
    addHospital,
    updateHospital,
    deleteHospital: removeHospital,
    toggleHospitalStatus,
    loading,
    error: loadError,
  } = useHospitals()

  const [actionError, setActionError] = useState("")
  const [saving, setSaving] = useState(false)

  const [search, setSearch] = useState("")
  const [typeFilter, setTypeFilter] = useState("All")
  const [statusFilter, setStatusFilter] = useState("All")

  const [showModal, setShowModal] = useState(false)
  const [editingHospital, setEditingHospital] = useState(null)

  const [formData, setFormData] = useState({
    name: "",
    code: "",
    address: "",
    phone: "",
    email: "",
    type: "Private",
    status: "Active",
  })

  const resetForm = () => {
    setFormData({
      name: "",
      code: "",
      address: "",
      phone: "",
      email: "",
      type: "Private",
      status: "Active",
    })

    setEditingHospital(null)
  }

  const openAddModal = () => {
    resetForm()
    setShowModal(true)
  }

  const openEditModal = (hospital) => {
    setEditingHospital(hospital)

    setFormData({
      name: hospital.name || "",
      code: hospital.code || "",
      address: hospital.address || "",
      phone: hospital.phone || "",
      email: hospital.email || "",
      type: hospital.type || "Private",
      status: hospital.status || "Active",
    })

    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setActionError("")
    resetForm()
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handlePhoneChange = (e) => {
    const value = e.target.value
      .replace(/\D/g, "")
      .slice(0, 10)

    setFormData({
      ...formData,
      phone: value,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setActionError("")

    if (!formData.name.trim()) {
      setActionError("Please enter hospital name")
      return
    }

    if (!formData.code.trim()) {
      setActionError("Please enter hospital code")
      return
    }

    if (formData.phone.length !== 10) {
      setActionError("Please enter valid 10 digit phone number")
      return
    }

    setSaving(true)
    try {
      if (editingHospital) {
        await updateHospital(editingHospital.id, formData)
      } else {
        await addHospital(formData)
      }
      closeModal()
    } catch (err) {
      // e.g. 403 when the signed-in user is not a platform administrator
      setActionError(err.message || "Could not save the hospital.")
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteHospital = async (id) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this hospital?"
    )

    if (!confirmDelete) return

    setActionError("")
    try {
      await removeHospital(id)
    } catch (err) {
      setActionError(err.message || "Could not delete the hospital.")
    }
  }

  const handleToggleStatus = async (id) => {
    setActionError("")
    try {
      await toggleHospitalStatus(id)
    } catch (err) {
      setActionError(err.message || "Could not change the hospital status.")
    }
  }

  const filteredHospitals = hospitals.filter(
    (hospital) => {
      const searchText =
        search.toLowerCase().trim()

      const matchesSearch =
        hospital.name
          .toLowerCase()
          .includes(searchText) ||
        hospital.code
          .toLowerCase()
          .includes(searchText) ||
        hospital.address
          .toLowerCase()
          .includes(searchText)

      const matchesType =
        typeFilter === "All" ||
        hospital.type === typeFilter

      const matchesStatus =
        statusFilter === "All" ||
        hospital.status === statusFilter

      return (
        matchesSearch &&
        matchesType &&
        matchesStatus
      )
    }
  )

  const totalHospitals = hospitals.length

  const activeHospitals =
    hospitals.filter(
      (hospital) =>
        hospital.status === "Active"
    ).length

  const governmentHospitals =
    hospitals.filter(
      (hospital) =>
        hospital.type === "Government"
    ).length

  const privateHospitals =
    hospitals.filter(
      (hospital) =>
        hospital.type === "Private"
    ).length

  return (
    <div className="p-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            Hospitals
          </h1>

          <p className="text-gray-500 mt-1">
            Manage hospitals in the system
          </p>
        </div>

        <button
          onClick={openAddModal}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium"
        >
          + Add Hospital
        </button>

      </div>

      {(loadError || actionError) && !showModal && (
        <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
          {actionError || loadError}
        </div>
      )}
      {loading && (
        <p className="mb-6 text-sm text-gray-500" role="status">Loading hospitals…</p>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">

        {/* Total */}
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Total Hospitals
          </p>

          <h2 className="text-3xl font-bold mt-2">
            {totalHospitals}
          </h2>
        </div>

        {/* Active */}
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Active Hospitals
          </p>

          <h2 className="text-3xl font-bold text-green-600 mt-2">
            {activeHospitals}
          </h2>
        </div>

        {/* Government */}
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Government
          </p>

          <h2 className="text-3xl font-bold text-blue-600 mt-2">
            {governmentHospitals}
          </h2>
        </div>

        {/* Private */}
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Private
          </p>

          <h2 className="text-3xl font-bold text-purple-600 mt-2">
            {privateHospitals}
          </h2>
        </div>

      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow p-4 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <input
            type="text"
            placeholder="Search hospital..."
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
            className="hms-input"
          />

          <select
            value={typeFilter}
            onChange={(e) =>
              setTypeFilter(e.target.value)
            }
            className="hms-input"
          >
            <option value="All">
              All Types
            </option>

            <option value="Government">
              Government
            </option>

            <option value="Private">
              Private
            </option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value)
            }
            className="hms-input"
          >
            <option value="All">
              All Status
            </option>

            <option value="Active">
              Active
            </option>

            <option value="Inactive">
              Inactive
            </option>
          </select>

        </div>

      </div>

      {/* Hospital Table */}
      <div className="bg-white rounded-xl shadow overflow-x-auto">

        <table className="w-full min-w-[1100px]">

          <thead className="bg-gray-100">

            <tr>

              <th className="p-4 text-left">
                Hospital
              </th>

              <th className="p-4 text-left">
                Code
              </th>

              <th className="p-4 text-left">
                Contact
              </th>

              <th className="p-4 text-left">
                Type
              </th>

              <th className="p-4 text-left">
                Departments
              </th>

              <th className="p-4 text-left">
                Doctors
              </th>

              <th className="p-4 text-left">
                Nurses
              </th>

              <th className="p-4 text-left">
                Status
              </th>

              <th className="p-4 text-left">
                Actions
              </th>

            </tr>

          </thead>

          <tbody>

            {filteredHospitals.length === 0 ? (

              <tr>
                <td
                  colSpan="9"
                  className="p-8 text-center text-gray-500"
                >
                  No hospitals found
                </td>
              </tr>

            ) : (

              filteredHospitals.map(
                (hospital) => (

                  <tr
                    key={hospital.id}
                    className="border-t hover:bg-gray-50"
                  >

                    {/* Hospital */}
                    <td className="p-4">

                      <div className="font-semibold text-gray-800">
                        {hospital.name}
                      </div>

                      <div className="text-sm text-gray-500">
                        {hospital.address}
                      </div>

                    </td>

                    {/* Code */}
                    <td className="p-4">

                      <span className="bg-gray-100 px-3 py-1 rounded-lg text-sm">
                        {hospital.code}
                      </span>

                    </td>

                    {/* Contact */}
                    <td className="p-4">

                      <div>
                        {hospital.phone}
                      </div>

                      <div className="text-sm text-gray-500">
                        {hospital.email}
                      </div>

                    </td>

                    {/* Type */}
                    <td className="p-4">

                      <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-sm">
                        {hospital.type}
                      </span>

                    </td>

                    {/* Departments */}
                    <td className="p-4">
                      {hospital.departments || 0}
                    </td>

                    {/* Doctors */}
                    <td className="p-4">
                      {hospital.doctors || 0}
                    </td>

                    {/* Nurses */}
                    <td className="p-4">
                      {hospital.nurses || 0}
                    </td>

                    {/* Status */}
                    <td className="p-4">

                      <button
                        onClick={() =>
                          handleToggleStatus(
                            hospital.id
                          )
                        }
                        className={
                          hospital.status ===
                            "Active"
                            ? "text-green-600 font-medium"
                            : "text-red-600 font-medium"
                        }
                      >
                        {hospital.status}
                      </button>

                    </td>

                    {/* Actions */}
                    <td className="p-4 whitespace-nowrap">

                      <button
                        onClick={() =>
                          openEditModal(
                            hospital
                          )
                        }
                        className="text-blue-600 mr-4 hover:underline"
                      >
                        Edit
                      </button>

                      <button
                        onClick={() =>
                          handleDeleteHospital(
                            hospital.id
                          )
                        }
                        className="text-red-600 hover:underline"
                      >
                        Delete
                      </button>

                    </td>

                  </tr>

                )
              )

            )}

          </tbody>

        </table>

      </div>

      {/* Add / Edit Modal */}
      {showModal && (

        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">

          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">

            {/* Modal Header */}
            <div className="p-6 border-b">

              <div className="flex justify-between items-center">

                <div>

                  <h2 className="text-xl font-bold">
                    {editingHospital
                      ? "Edit Hospital"
                      : "Add Hospital"}
                  </h2>

                  <p className="text-sm text-gray-500 mt-1">
                    Enter hospital information
                  </p>

                </div>

                <button
                  onClick={closeModal}
                  className="text-gray-500 text-2xl hover:text-gray-800"
                >
                  ×
                </button>

              </div>

            </div>

            {/* Form */}
            <form
              onSubmit={handleSubmit}
              className="p-6 space-y-4"
            >
              {actionError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
                  {actionError}
                </div>
              )}

              {/* Hospital Name */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Hospital Name
                </label>

                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Enter hospital name"
                  className="hms-input w-full"
                />

              </div>

              {/* Hospital Code */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Hospital Code
                </label>

                <input
                  type="text"
                  name="code"
                  value={formData.code}
                  onChange={handleChange}
                  placeholder="Example: CHB001"
                  className="hms-input w-full"
                />

              </div>

              {/* Address */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Address
                </label>

                <textarea
                  name="address"
                  value={formData.address}
                  onChange={handleChange}
                  rows="3"
                  placeholder="Enter hospital address"
                  className="hms-input w-full"
                />

              </div>

              {/* Phone */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Contact Number
                </label>

                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handlePhoneChange}
                  maxLength="10"
                  placeholder="10 digit contact number"
                  className="hms-input w-full"
                />

              </div>

              {/* Email */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Email
                </label>

                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="hospital@example.com"
                  className="hms-input w-full"
                />

              </div>

              {/* Type */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Hospital Type
                </label>

                <select
                  name="type"
                  value={formData.type}
                  onChange={handleChange}
                  className="hms-input w-full"
                >

                  <option value="Private">
                    Private
                  </option>

                  <option value="Government">
                    Government
                  </option>

                </select>

              </div>

              {/* Status */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Status
                </label>

                <select
                  name="status"
                  value={formData.status}
                  onChange={handleChange}
                  className="hms-input w-full"
                >

                  <option value="Active">
                    Active
                  </option>

                  <option value="Inactive">
                    Inactive
                  </option>

                </select>

              </div>

              {/* Buttons */}
              <div className="flex justify-end gap-3 pt-4">

                <button
                  type="button"
                  onClick={closeModal}
                  className="px-5 py-2.5 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
                >
                  {saving
                    ? "Saving…"
                    : editingHospital
                      ? "Update Hospital"
                      : "Add Hospital"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  )
}

export default Hospitals