import { useState } from "react"

function Users() {
  const [users, setUsers] = useState([
    {
      id: 1,
      name: "Rahul Kumar",
      email: "rahul@gmail.com",
      mobile: "9876543210",
      role: "Patient",
      hospital: "City Hospital Begusarai",
      status: "Active",
    },
    {
      id: 2,
      name: "Dr. Sharma",
      email: "sharma@hospital.com",
      mobile: "9876543211",
      role: "Doctor",
      hospital: "City Hospital Begusarai",
      status: "Active",
    },
    {
      id: 3,
      name: "Priya Singh",
      email: "priya@hospital.com",
      mobile: "9876543212",
      role: "Nurse",
      hospital: "Sadar Hospital Begusarai",
      status: "Active",
    },
    {
      id: 4,
      name: "Amit Kumar",
      email: "amit@hospital.com",
      mobile: "9876543213",
      role: "Compounder",
      hospital: "Medicare Hospital Begusarai",
      status: "Inactive",
    },
  ])

  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState("All")
  const [statusFilter, setStatusFilter] = useState("All")

  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    mobile: "",
    role: "Patient",
    hospital: "",
    status: "Active",
  })

  const resetForm = () => {
    setFormData({
      name: "",
      email: "",
      mobile: "",
      role: "Patient",
      hospital: "",
      status: "Active",
    })

    setEditingUser(null)
  }

  const openAddModal = () => {
    resetForm()
    setShowModal(true)
  }

  const openEditModal = (user) => {
    setEditingUser(user)

    setFormData({
      name: user.name,
      email: user.email,
      mobile: user.mobile,
      role: user.role,
      hospital: user.hospital,
      status: user.status,
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
      alert("Please enter user name")
      return
    }

    if (!formData.email.trim()) {
      alert("Please enter email")
      return
    }

    if (formData.mobile.length !== 10) {
      alert("Please enter valid 10 digit mobile number")
      return
    }

    if (editingUser) {
      setUsers(
        users.map((user) =>
          user.id === editingUser.id
            ? {
              ...user,
              ...formData,
            }
            : user
        )
      )
    } else {
      const newUser = {
        id: Date.now(),
        ...formData,
      }

      setUsers([newUser, ...users])
    }

    setShowModal(false)
    resetForm()
  }

  const deleteUser = (id) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this user?"
    )

    if (!confirmDelete) return

    setUsers(
      users.filter((user) => user.id !== id)
    )
  }

  const toggleStatus = (id) => {
    setUsers(
      users.map((user) =>
        user.id === id
          ? {
            ...user,
            status:
              user.status === "Active"
                ? "Inactive"
                : "Active",
          }
          : user
      )
    )
  }

  const filteredUsers = users.filter((user) => {
    const searchText = search.toLowerCase()

    const matchesSearch =
      user.name.toLowerCase().includes(searchText) ||
      user.email.toLowerCase().includes(searchText) ||
      user.mobile.includes(searchText)

    const matchesRole =
      roleFilter === "All" ||
      user.role === roleFilter

    const matchesStatus =
      statusFilter === "All" ||
      user.status === statusFilter

    return (
      matchesSearch &&
      matchesRole &&
      matchesStatus
    )
  })

  return (
    <div className="p-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            Users
          </h1>

          <p className="text-gray-500 mt-1">
            Manage all hospital system users
          </p>
        </div>

        <button
          onClick={openAddModal}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium"
        >
          + Add User
        </button>

      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Total Users
          </p>

          <h2 className="text-3xl font-bold mt-2">
            {users.length}
          </h2>
        </div>

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Active Users
          </p>

          <h2 className="text-3xl font-bold text-green-600 mt-2">
            {
              users.filter(
                (user) => user.status === "Active"
              ).length
            }
          </h2>
        </div>

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Doctors
          </p>

          <h2 className="text-3xl font-bold text-blue-600 mt-2">
            {
              users.filter(
                (user) => user.role === "Doctor"
              ).length
            }
          </h2>
        </div>

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">
            Staff
          </p>

          <h2 className="text-3xl font-bold text-purple-600 mt-2">
            {
              users.filter(
                (user) =>
                  user.role === "Nurse" ||
                  user.role === "Compounder"
              ).length
            }
          </h2>
        </div>

      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow p-4 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <input
            type="text"
            placeholder="Search name, email or mobile..."
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
            className="border rounded-lg px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
          />

          <select
            value={roleFilter}
            onChange={(e) =>
              setRoleFilter(e.target.value)
            }
            className="border rounded-lg px-4 py-2.5"
          >
            <option value="All">All Roles</option>
            <option value="Admin">Admin</option>
            <option value="Doctor">Doctor</option>
            <option value="Nurse">Nurse</option>
            <option value="Compounder">Compounder</option>
            <option value="Reception">Reception</option>
            <option value="Patient">Patient</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value)
            }
            className="border rounded-lg px-4 py-2.5"
          >
            <option value="All">All Status</option>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </select>

        </div>

      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl shadow overflow-x-auto">

        <table className="w-full min-w-[1000px]">

          <thead className="bg-gray-100">

            <tr>
              <th className="p-4 text-left">
                User
              </th>

              <th className="p-4 text-left">
                Mobile
              </th>

              <th className="p-4 text-left">
                Role
              </th>

              <th className="p-4 text-left">
                Hospital
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

            {filteredUsers.length === 0 ? (

              <tr>
                <td
                  colSpan="6"
                  className="p-8 text-center text-gray-500"
                >
                  No users found
                </td>
              </tr>

            ) : (

              filteredUsers.map((user) => (

                <tr
                  key={user.id}
                  className="border-t hover:bg-gray-50"
                >

                  <td className="p-4">

                    <div className="font-medium text-gray-800">
                      {user.name}
                    </div>

                    <div className="text-sm text-gray-500">
                      {user.email}
                    </div>

                  </td>

                  <td className="p-4">
                    {user.mobile}
                  </td>

                  <td className="p-4">

                    <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-sm">
                      {user.role}
                    </span>

                  </td>

                  <td className="p-4">
                    {user.hospital || "—"}
                  </td>

                  <td className="p-4">

                    <button
                      onClick={() =>
                        toggleStatus(user.id)
                      }
                      className={
                        user.status === "Active"
                          ? "text-green-600 font-medium"
                          : "text-red-600 font-medium"
                      }
                    >
                      {user.status}
                    </button>

                  </td>

                  <td className="p-4">

                    <button
                      onClick={() =>
                        openEditModal(user)
                      }
                      className="text-blue-600 mr-4"
                    >
                      Edit
                    </button>

                    <button
                      onClick={() =>
                        deleteUser(user.id)
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

      {/* Add / Edit Modal */}
      {showModal && (

        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">

          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">

            <div className="p-6 border-b">

              <div className="flex justify-between items-center">

                <h2 className="text-xl font-bold">
                  {editingUser
                    ? "Edit User"
                    : "Add User"}
                </h2>

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
              className="p-6 space-y-4"
            >

              <div>
                <label className="block text-sm font-medium mb-1">
                  Full Name
                </label>

                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  className="w-full border rounded-lg px-4 py-2.5"
                  placeholder="Enter full name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Email
                </label>

                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full border rounded-lg px-4 py-2.5"
                  placeholder="Enter email"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Mobile Number
                </label>

                <input
                  type="tel"
                  name="mobile"
                  value={formData.mobile}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      mobile: e.target.value
                        .replace(/\D/g, "")
                        .slice(0, 10),
                    })
                  }
                  className="w-full border rounded-lg px-4 py-2.5"
                  placeholder="10 digit mobile number"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Role
                </label>

                <select
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                  className="w-full border rounded-lg px-4 py-2.5"
                >
                  <option>Admin</option>
                  <option>Doctor</option>
                  <option>Nurse</option>
                  <option>Compounder</option>
                  <option>Reception</option>
                  <option>Patient</option>
                </select>
              </div>

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

                  <option>
                    City Hospital Begusarai
                  </option>

                  <option>
                    Sadar Hospital Begusarai
                  </option>

                  <option>
                    Medicare Hospital Begusarai
                  </option>
                </select>
              </div>

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
                  <option>Active</option>
                  <option>Inactive</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-4">

                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false)
                    resetForm()
                  }}
                  className="px-5 py-2.5 border rounded-lg"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-5 py-2.5 bg-blue-600 text-white rounded-lg"
                >
                  {editingUser
                    ? "Update User"
                    : "Add User"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  )
}

export default Users