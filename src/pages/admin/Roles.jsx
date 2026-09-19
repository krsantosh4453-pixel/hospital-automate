import { useState } from "react"

function Roles() {
  const [roles, setRoles] = useState([
    {
      id: 1,
      name: "Admin",
      description: "Full hospital system access",
      users: 2,
      status: "Active",
      permissions: [
        "Users",
        "Hospitals",
        "Doctors",
        "Nurses",
        "Compounders",
        "Departments",
        "Permissions",
      ],
    },
    {
      id: 2,
      name: "Doctor",
      description: "Manage patients, appointments and prescriptions",
      users: 12,
      status: "Active",
      permissions: [
        "Patients",
        "Appointments",
        "Prescriptions",
        "Laboratory",
      ],
    },
    {
      id: 3,
      name: "Nurse",
      description: "Manage patients and nursing activities",
      users: 25,
      status: "Active",
      permissions: [
        "Patients",
        "Vitals",
        "Nursing Notes",
        "Medication",
      ],
    },
    {
      id: 4,
      name: "Compounder",
      description: "Manage medicines and prescriptions",
      users: 8,
      status: "Active",
      permissions: [
        "Prescriptions",
        "Pharmacy",
        "Inventory",
      ],
    },
    {
      id: 5,
      name: "Reception",
      description: "Manage registration and appointments",
      users: 6,
      status: "Active",
      permissions: [
        "Patients",
        "Appointments",
        "Queue",
        "Billing",
      ],
    },
    {
      id: 6,
      name: "Patient",
      description: "Access personal healthcare services",
      users: 150,
      status: "Active",
      permissions: [
        "Appointments",
        "Prescriptions",
        "Laboratory",
        "Bills",
      ],
    },
  ])

  const availablePermissions = [
    "Dashboard",
    "Users",
    "Roles",
    "Hospitals",
    "Departments",
    "Doctors",
    "Nurses",
    "Compounders",
    "Patients",
    "Appointments",
    "Queue",
    "Pharmacy",
    "Laboratory",
    "Billing",
    "Inventory",
    "Prescriptions",
    "Reports",
    "Vitals",
    "Nursing Notes",
    "Medication",
    "Permissions",
  ]

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("All")

  const [showModal, setShowModal] = useState(false)
  const [showPermissionModal, setShowPermissionModal] = useState(false)

  const [editingRole, setEditingRole] = useState(null)
  const [selectedRole, setSelectedRole] = useState(null)

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    status: "Active",
    permissions: [],
  })

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      status: "Active",
      permissions: [],
    })

    setEditingRole(null)
  }

  const openAddModal = () => {
    resetForm()
    setShowModal(true)
  }

  const openEditModal = (role) => {
    setEditingRole(role)

    setFormData({
      name: role.name,
      description: role.description,
      status: role.status,
      permissions: [...role.permissions],
    })

    setShowModal(true)
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const togglePermission = (permission) => {
    setFormData((previous) => {
      const exists =
        previous.permissions.includes(permission)

      return {
        ...previous,
        permissions: exists
          ? previous.permissions.filter(
            (item) => item !== permission
          )
          : [
            ...previous.permissions,
            permission,
          ],
      }
    })
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      alert("Please enter role name")
      return
    }

    if (!formData.description.trim()) {
      alert("Please enter role description")
      return
    }

    if (editingRole) {
      setRoles(
        roles.map((role) =>
          role.id === editingRole.id
            ? {
              ...role,
              name: formData.name,
              description: formData.description,
              status: formData.status,
              permissions:
                formData.permissions,
            }
            : role
        )
      )
    } else {
      const newRole = {
        id: Date.now(),
        name: formData.name,
        description: formData.description,
        users: 0,
        status: formData.status,
        permissions: formData.permissions,
      }

      setRoles([newRole, ...roles])
    }

    setShowModal(false)
    resetForm()
  }

  const deleteRole = (id) => {
    const role = roles.find(
      (item) => item.id === id
    )

    if (!role) return

    if (role.users > 0) {
      alert(
        "This role is assigned to users. Remove users from this role before deleting it."
      )
      return
    }

    const confirmDelete = window.confirm(
      "Are you sure you want to delete this role?"
    )

    if (!confirmDelete) return

    setRoles(
      roles.filter((item) => item.id !== id)
    )
  }

  const toggleStatus = (id) => {
    setRoles(
      roles.map((role) =>
        role.id === id
          ? {
            ...role,
            status:
              role.status === "Active"
                ? "Inactive"
                : "Active",
          }
          : role
      )
    )
  }

  const openPermissionView = (role) => {
    setSelectedRole(role)
    setShowPermissionModal(true)
  }

  const filteredRoles = roles.filter((role) => {
    const searchText = search.toLowerCase()

    const matchesSearch =
      role.name
        .toLowerCase()
        .includes(searchText) ||
      role.description
        .toLowerCase()
        .includes(searchText)

    const matchesStatus =
      statusFilter === "All" ||
      role.status === statusFilter

    return (
      matchesSearch &&
      matchesStatus
    )
  })

  return (
    <div className="p-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            Roles
          </h1>

          <p className="text-gray-500 mt-1">
            Manage user roles and access levels
          </p>
        </div>

        <button
          onClick={openAddModal}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium"
        >
          + Add Role
        </button>

      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Total Roles
          </p>

          <h2 className="text-3xl font-bold mt-2">
            {roles.length}
          </h2>
        </div>

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Active Roles
          </p>

          <h2 className="text-3xl font-bold text-green-600 mt-2">
            {
              roles.filter(
                (role) =>
                  role.status === "Active"
              ).length
            }
          </h2>
        </div>

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Assigned Users
          </p>

          <h2 className="text-3xl font-bold text-blue-600 mt-2">
            {roles.reduce(
              (total, role) =>
                total + role.users,
              0
            )}
          </h2>
        </div>

      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow p-4 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          <input
            type="text"
            placeholder="Search role..."
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
            className="border rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
          />

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

      {/* Roles Table */}
      <div className="bg-white rounded-xl shadow overflow-x-auto">

        <table className="w-full min-w-[1000px]">

          <thead className="bg-gray-100">

            <tr>

              <th className="p-4 text-left">
                Role
              </th>

              <th className="p-4 text-left">
                Description
              </th>

              <th className="p-4 text-left">
                Users
              </th>

              <th className="p-4 text-left">
                Permissions
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

            {filteredRoles.length === 0 ? (

              <tr>

                <td
                  colSpan="6"
                  className="p-8 text-center text-gray-500"
                >
                  No roles found
                </td>

              </tr>

            ) : (

              filteredRoles.map((role) => (

                <tr
                  key={role.id}
                  className="border-t hover:bg-gray-50"
                >

                  <td className="p-4">

                    <div className="font-semibold text-gray-800">
                      {role.name}
                    </div>

                  </td>

                  <td className="p-4 max-w-xs">
                    <span className="text-gray-600">
                      {role.description}
                    </span>
                  </td>

                  <td className="p-4">
                    {role.users}
                  </td>

                  <td className="p-4">

                    <button
                      onClick={() =>
                        openPermissionView(role)
                      }
                      className="text-blue-600 hover:underline"
                    >
                      View{" "}
                      {role.permissions.length}{" "}
                      permissions
                    </button>

                  </td>

                  <td className="p-4">

                    <button
                      onClick={() =>
                        toggleStatus(role.id)
                      }
                      className={
                        role.status === "Active"
                          ? "text-green-600 font-medium"
                          : "text-red-600 font-medium"
                      }
                    >
                      {role.status}
                    </button>

                  </td>

                  <td className="p-4">

                    <button
                      onClick={() =>
                        openEditModal(role)
                      }
                      className="text-blue-600 mr-4"
                    >
                      Edit
                    </button>

                    <button
                      onClick={() =>
                        deleteRole(role.id)
                      }
                      className="text-red-600"
                    >
                      Delete
                    </button>

                  </td>

                </tr>

              ))

            )}

          </tbody>

        </table>

      </div>

      {/* Add / Edit Role Modal */}
      {showModal && (

        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">

          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">

            <div className="p-6 border-b">

              <div className="flex justify-between items-center">

                <div>
                  <h2 className="text-xl font-bold">
                    {editingRole
                      ? "Edit Role"
                      : "Add Role"}
                  </h2>

                  <p className="text-sm text-gray-500 mt-1">
                    Configure role and permissions
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

            <form
              onSubmit={handleSubmit}
              className="p-6 space-y-5"
            >

              {/* Role Name */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Role Name
                </label>

                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Enter role name"
                  className="w-full border rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>

              {/* Description */}
              <div>

                <label className="block text-sm font-medium mb-1">
                  Description
                </label>

                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  placeholder="Enter role description"
                  rows="3"
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

              {/* Permissions */}
              <div>

                <div className="flex justify-between items-center mb-2">

                  <label className="block text-sm font-medium">
                    Permissions
                  </label>

                  <span className="text-sm text-blue-600">
                    {formData.permissions.length} selected
                  </span>

                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 border rounded-xl p-4 max-h-64 overflow-y-auto">

                  {availablePermissions.map(
                    (permission) => {

                      const checked =
                        formData.permissions.includes(
                          permission
                        )

                      return (
                        <label
                          key={permission}
                          className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer"
                        >

                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() =>
                              togglePermission(
                                permission
                              )
                            }
                            className="w-4 h-4"
                          />

                          <span className="text-sm">
                            {permission}
                          </span>

                        </label>
                      )
                    }
                  )}

                </div>

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
                  {editingRole
                    ? "Update Role"
                    : "Create Role"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

      {/* Permission View Modal */}
      {showPermissionModal &&
        selectedRole && (

          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">

            <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">

              <div className="p-6 border-b">

                <div className="flex justify-between items-center">

                  <div>
                    <h2 className="text-xl font-bold">
                      {selectedRole.name}
                    </h2>

                    <p className="text-gray-500 text-sm mt-1">
                      Assigned Permissions
                    </p>
                  </div>

                  <button
                    onClick={() => {
                      setShowPermissionModal(false)
                      setSelectedRole(null)
                    }}
                    className="text-gray-500 text-2xl"
                  >
                    ×
                  </button>

                </div>

              </div>

              <div className="p-6">

                {selectedRole.permissions.length ===
                  0 ? (

                  <p className="text-gray-500 text-center">
                    No permissions assigned
                  </p>

                ) : (

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">

                    {selectedRole.permissions.map(
                      (permission) => (

                        <div
                          key={permission}
                          className="border rounded-lg px-4 py-3"
                        >
                          ✓ {permission}
                        </div>

                      )
                    )}

                  </div>

                )}

              </div>

              <div className="p-6 border-t flex justify-end">

                <button
                  onClick={() => {
                    setShowPermissionModal(false)
                    setSelectedRole(null)
                  }}
                  className="px-5 py-2.5 bg-gray-800 text-white rounded-lg"
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

export default Roles