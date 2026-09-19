import { useState } from "react"

function Departments() {
  const [departments, setDepartments] = useState([
    {
      id: 1,
      name: "Cardiology",
      code: "CARD",
      hospital: "City Hospital Begusarai",
      head: "Dr. Sharma",
      doctors: 3,
      status: "Active",
    },
    {
      id: 2,
      name: "General Medicine",
      code: "GENMED",
      hospital: "City Hospital Begusarai",
      head: "Dr. Kumar",
      doctors: 4,
      status: "Active",
    },
    {
      id: 3,
      name: "Orthopedics",
      code: "ORTHO",
      hospital: "Sadar Hospital Begusarai",
      head: "Dr. Singh",
      doctors: 5,
      status: "Active",
    },
    {
      id: 4,
      name: "Pediatrics",
      code: "PEDIA",
      hospital: "Sadar Hospital Begusarai",
      head: "Dr. Verma",
      doctors: 3,
      status: "Active",
    },
    {
      id: 5,
      name: "Emergency",
      code: "EMER",
      hospital: "Medicare Hospital Begusarai",
      head: "Dr. Gupta",
      doctors: 2,
      status: "Active",
    },
  ])

  const [search, setSearch] = useState("")
  const [hospitalFilter, setHospitalFilter] =
    useState("All")
  const [statusFilter, setStatusFilter] =
    useState("All")

  const [showModal, setShowModal] =
    useState(false)

  const [editingDepartment, setEditingDepartment] =
    useState(null)

  const [formData, setFormData] = useState({
    name: "",
    code: "",
    hospital: "",
    head: "",
    doctors: 0,
    status: "Active",
  })

  const hospitals = [
    "City Hospital Begusarai",
    "Sadar Hospital Begusarai",
    "Medicare Hospital Begusarai",
  ]

  const resetForm = () => {
    setFormData({
      name: "",
      code: "",
      hospital: "",
      head: "",
      doctors: 0,
      status: "Active",
    })

    setEditingDepartment(null)
  }

  const openAddModal = () => {
    resetForm()
    setShowModal(true)
  }

  const openEditModal = (department) => {
    setEditingDepartment(department)

    setFormData({
      name: department.name,
      code: department.code,
      hospital: department.hospital,
      head: department.head,
      doctors: department.doctors,
      status: department.status,
    })

    setShowModal(true)
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      alert("Please enter department name")
      return
    }

    if (!formData.code.trim()) {
      alert("Please enter department code")
      return
    }

    if (!formData.hospital) {
      alert("Please select hospital")
      return
    }

    if (editingDepartment) {
      setDepartments(
        departments.map((department) =>
          department.id === editingDepartment.id
            ? {
              ...department,
              ...formData,
              doctors: Number(formData.doctors),
            }
            : department
        )
      )
    } else {
      const newDepartment = {
        id: Date.now(),
        ...formData,
        doctors: Number(formData.doctors),
      }

      setDepartments([
        newDepartment,
        ...departments,
      ])
    }

    setShowModal(false)
    resetForm()
  }

  const deleteDepartment = (id) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this department?"
    )

    if (!confirmDelete) return

    setDepartments(
      departments.filter(
        (department) => department.id !== id
      )
    )
  }

  const toggleStatus = (id) => {
    setDepartments(
      departments.map((department) =>
        department.id === id
          ? {
            ...department,
            status:
              department.status === "Active"
                ? "Inactive"
                : "Active",
          }
          : department
      )
    )
  }

  const filteredDepartments =
    departments.filter((department) => {
      const searchText =
        search.toLowerCase()

      const matchesSearch =
        department.name
          .toLowerCase()
          .includes(searchText) ||
        department.code
          .toLowerCase()
          .includes(searchText) ||
        department.head
          .toLowerCase()
          .includes(searchText)

      const matchesHospital =
        hospitalFilter === "All" ||
        department.hospital ===
        hospitalFilter

      const matchesStatus =
        statusFilter === "All" ||
        department.status === statusFilter

      return (
        matchesSearch &&
        matchesHospital &&
        matchesStatus
      )
    })

  const activeDepartments =
    departments.filter(
      (department) =>
        department.status === "Active"
    ).length

  const totalDoctors =
    departments.reduce(
      (total, department) =>
        total + Number(department.doctors),
      0
    )

  return (
    <div className="p-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            Departments
          </h1>

          <p className="text-gray-500 mt-1">
            Manage hospital departments
          </p>
        </div>

        <button
          onClick={openAddModal}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium"
        >
          + Add Department
        </button>

      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Total Departments
          </p>

          <h2 className="text-3xl font-bold mt-2">
            {departments.length}
          </h2>
        </div>

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Active Departments
          </p>

          <h2 className="text-3xl font-bold text-green-600 mt-2">
            {activeDepartments}
          </h2>
        </div>

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Doctors Assigned
          </p>

          <h2 className="text-3xl font-bold text-blue-600 mt-2">
            {totalDoctors}
          </h2>
        </div>

      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow p-4 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <input
            type="text"
            placeholder="Search department..."
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
            className="border rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
          />

          <select
            value={hospitalFilter}
            onChange={(e) =>
              setHospitalFilter(e.target.value)
            }
            className="border rounded-lg px-4 py-2.5"
          >
            <option value="All">
              All Hospitals
            </option>

            {hospitals.map((hospital) => (
              <option
                key={hospital}
                value={hospital}
              >
                {hospital}
              </option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value)
            }
            className="border rounded-lg px-4 py-2.5"
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

      {/* Departments Table */}
      <div className="bg-white rounded-xl shadow overflow-x-auto">

        <table className="w-full min-w-[1000px]">

          <thead className="bg-gray-100">

            <tr>

              <th className="p-4 text-left">
                Department
              </th>

              <th className="p-4 text-left">
                Code
              </th>

              <th className="p-4 text-left">
                Hospital
              </th>

              <th className="p-4 text-left">
                Department Head
              </th>

              <th className="p-4 text-left">
                Doctors
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

            {filteredDepartments.length === 0 ? (

              <tr>

                <td
                  colSpan="7"
                  className="p-8 text-center text-gray-500"
                >
                  No departments found
                </td>

              </tr>

            ) : (

              filteredDepartments.map(
                (department) => (

                  <tr
                    key={department.id}
                    className="border-t hover:bg-gray-50"
                  >

                    <td className="p-4">

                      <div className="font-semibold text-gray-800">
                        {department.name}
                      </div>

                    </td>

                    <td className="p-4">

                      <span className="bg-gray-100 px-3 py-1 rounded-lg text-sm">
                        {department.code}
                      </span>

                    </td>

                    <td className="p-4">
                      {department.hospital}
                    </td>

                    <td className="p-4">
                      {department.head || "—"}
                    </td>

                    <td className="p-4">
                      {department.doctors}
                    </td>

                    <td className="p-4">

                      <button
                        onClick={() =>
                          toggleStatus(
                            department.id
                          )
                        }
                        className={
                          department.status ===
                            "Active"
                            ? "text-green-600 font-medium"
                            : "text-red-600 font-medium"
                        }
                      >
                        {department.status}
                      </button>

                    </td>

                    <td className="p-4 whitespace-nowrap">

                      <button
                        onClick={() =>
                          openEditModal(
                            department
                          )
                        }
                        className="text-blue-600 mr-4"
                      >
                        Edit
                      </button>

                      <button
                        onClick={() =>
                          deleteDepartment(
                            department.id
                          )
                        }
                        className="text-red-600"
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

          <div className="bg-white rounded-2xl shadow-xl w-full max-w-xl max-h-[90vh] overflow-y-auto">

            {/* Modal Header */}
            <div className="p-6 border-b">

              <div className="flex justify-between items-center">

                <div>

                  <h2 className="text-xl font-bold">
                    {editingDepartment
                      ? "Edit Department"
                      : "Add Department"}
                  </h2>

                  <p className="text-sm text-gray-500 mt-1">
                    Enter department information
                  </p>

                </div>

                <button
                  onClick={() => {
                    setShowModal(false)
                    resetForm()
                  }}
                  className="text-gray-500 text-2xl"
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

              {/* Department Name */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Department Name
                </label>

                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Example: Cardiology"
                  className="w-full border rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>

              {/* Department Code */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Department Code
                </label>

                <input
                  type="text"
                  name="code"
                  value={formData.code}
                  onChange={handleChange}
                  placeholder="Example: CARD"
                  className="w-full border rounded-lg px-4 py-2.5 uppercase outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>

              {/* Hospital */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Hospital
                </label>

                <select
                  name="hospital"
                  value={formData.hospital}
                  onChange={handleChange}
                  className="w-full border rounded-lg px-4 py-2.5"
                >

                  <option value="">
                    Select Hospital
                  </option>

                  {hospitals.map((hospital) => (
                    <option
                      key={hospital}
                      value={hospital}
                    >
                      {hospital}
                    </option>
                  ))}

                </select>

              </div>

              {/* Department Head */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Department Head
                </label>

                <input
                  type="text"
                  name="head"
                  value={formData.head}
                  onChange={handleChange}
                  placeholder="Enter department head"
                  className="w-full border rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>

              {/* Doctors */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Number of Doctors
                </label>

                <input
                  type="number"
                  name="doctors"
                  min="0"
                  value={formData.doctors}
                  onChange={handleChange}
                  className="w-full border rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
                />

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
                  className="w-full border rounded-lg px-4 py-2.5"
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
                  onClick={() => {
                    setShowModal(false)
                    resetForm()
                  }}
                  className="px-5 py-2.5 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                >
                  {editingDepartment
                    ? "Update Department"
                    : "Add Department"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  )
}

export default Departments