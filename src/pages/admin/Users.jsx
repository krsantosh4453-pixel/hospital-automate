import { useCallback, useEffect, useMemo, useState } from "react"
import { usePatient } from "../../assets/context/PatientContext.jsx"
import api from "../../services/api.js"

// Roles a hospital membership can hold (users.models.StaffRole).
const ROLES = [
  "Admin",
  "Hospital Manager",
  "Doctor",
  "Nurse",
  "Receptionist",
  "Pharmacist",
  "Compounder",
  "Lab Staff",
  "Billing Staff",
  "Inventory Staff",
  "Blood Bank Staff",
]

// Staff of the selected hospital, managed through /api/users/. New staff
// register themselves (Create Account) and are approved here; the backend
// only lets this hospital's Admin or Hospital Manager make these changes.
function Users() {
  const { selectedHospital } = usePatient()
  const [staff, setStaff] = useState([])
  const [pending, setPending] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busyId, setBusyId] = useState(null)
  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState("All")
  const [statusFilter, setStatusFilter] = useState("All")
  const [approveRoles, setApproveRoles] = useState({})

  const load = useCallback(async () => {
    if (!selectedHospital) return
    setLoading(true)
    setError("")
    try {
      const data = await api.users.list()
      setStaff(data.staff || [])
      setPending(data.pending || [])
    } catch (err) {
      setStaff([])
      setPending([])
      setError(err.message || "Could not load staff.")
    } finally {
      setLoading(false)
    }
  }, [selectedHospital])

  useEffect(() => {
    load()
  }, [load])

  const run = async (userId, action, success) => {
    setBusyId(userId)
    setError("")
    setNotice("")
    try {
      await action()
      setNotice(success)
      await load()
    } catch (err) {
      setError(err.message || "The change was not saved.")
    } finally {
      setBusyId(null)
    }
  }

  const changeRole = (member, role) =>
    run(member.id, () => api.users.updateMembership(member.id, { role }), `${member.name} is now ${role}.`)

  const toggleActive = (member) => {
    const active = !member.membership?.is_active
    if (!active && !window.confirm(`Remove ${member.name}'s access to this hospital?`)) return
    run(
      member.id,
      () => api.users.updateMembership(member.id, { is_active: active }),
      active ? `${member.name} can sign in to this hospital again.` : `${member.name}'s access was removed.`,
    )
  }

  const approve = (applicant) => {
    const role = approveRoles[applicant.id] || applicant.requested_role
    run(applicant.id, () => api.users.approve(applicant.id, { role }), `${applicant.name} approved as ${role}.`)
  }

  const filteredStaff = useMemo(() => {
    const text = search.toLowerCase().trim()
    return staff.filter((member) => {
      const matchesSearch =
        !text ||
        [member.name, member.username, member.email, member.employee_id]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(text))
      const matchesRole = roleFilter === "All" || member.membership?.role === roleFilter
      const isActive = Boolean(member.membership?.is_active)
      const matchesStatus =
        statusFilter === "All" || (statusFilter === "Active" ? isActive : !isActive)
      return matchesSearch && matchesRole && matchesStatus
    })
  }, [staff, search, roleFilter, statusFilter])

  const activeCount = staff.filter((member) => member.membership?.is_active).length

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Users</h1>
          <p className="text-gray-500 mt-1">
            Staff of {selectedHospital?.name || "the selected hospital"}. New staff create an
            account and are approved here.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
          {error}
        </div>
      )}
      {notice && !error && (
        <div className="mb-6 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm" role="status">
          {notice}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">Total Staff</p>
          <h2 className="text-3xl font-bold mt-2">{staff.length}</h2>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">Active</p>
          <h2 className="text-3xl font-bold text-green-600 mt-2">{activeCount}</h2>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">Awaiting Approval</p>
          <h2 className="text-3xl font-bold text-orange-600 mt-2">{pending.length}</h2>
        </div>
      </div>

      {pending.length > 0 && (
        <div className="bg-white rounded-xl shadow p-5 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Pending Registrations</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Email / Mobile</th>
                  <th className="py-2 pr-4">Requested Role</th>
                  <th className="py-2 pr-4">Approve As</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody>
                {pending.map((applicant) => (
                  <tr key={applicant.id} className="border-b last:border-0">
                    <td className="py-3 pr-4 font-medium text-gray-800">{applicant.name}</td>
                    <td className="py-3 pr-4 text-gray-600">
                      {applicant.email || "—"}
                      <br />
                      {applicant.phone || ""}
                    </td>
                    <td className="py-3 pr-4">{applicant.requested_role}</td>
                    <td className="py-3 pr-4">
                      <select
                        aria-label={`Role for ${applicant.name}`}
                        value={approveRoles[applicant.id] || applicant.requested_role}
                        onChange={(e) => setApproveRoles({ ...approveRoles, [applicant.id]: e.target.value })}
                        className="border border-gray-300 rounded-lg px-3 py-2"
                      >
                        {ROLES.map((role) => (
                          <option key={role}>{role}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => approve(applicant)}
                        disabled={busyId === applicant.id}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
                      >
                        Approve
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow p-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <input
            type="text"
            aria-label="Search staff"
            placeholder="Search by name, username, email or employee ID"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2.5"
          />
          <select
            aria-label="Filter by role"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2.5"
          >
            <option value="All">All Roles</option>
            {ROLES.map((role) => (
              <option key={role}>{role}</option>
            ))}
          </select>
          <select
            aria-label="Filter by status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2.5"
          >
            <option value="All">All Status</option>
            <option>Active</option>
            <option>Inactive</option>
          </select>
        </div>

        {loading ? (
          <p className="text-gray-500 text-sm" role="status">Loading staff…</p>
        ) : filteredStaff.length === 0 ? (
          <p className="text-gray-500 text-sm">No staff match.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Username</th>
                  <th className="py-2 pr-4">Contact</th>
                  <th className="py-2 pr-4">Role</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody>
                {filteredStaff.map((member) => {
                  const active = Boolean(member.membership?.is_active)
                  return (
                    <tr key={member.id} className="border-b last:border-0">
                      <td className="py-3 pr-4 font-medium text-gray-800">
                        {member.name}
                        {member.employee_id && (
                          <span className="block text-xs text-gray-400">{member.employee_id}</span>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-gray-600">{member.username}</td>
                      <td className="py-3 pr-4 text-gray-600">
                        {member.email || "—"}
                        <br />
                        {member.phone || ""}
                      </td>
                      <td className="py-3 pr-4">
                        <select
                          aria-label={`Role of ${member.name}`}
                          value={member.membership?.role || ""}
                          disabled={busyId === member.id}
                          onChange={(e) => changeRole(member, e.target.value)}
                          className="border border-gray-300 rounded-lg px-3 py-2"
                        >
                          {ROLES.map((role) => (
                            <option key={role}>{role}</option>
                          ))}
                        </select>
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}
                        >
                          {active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => toggleActive(member)}
                          disabled={busyId === member.id}
                          className={`px-4 py-2 rounded-lg text-sm disabled:opacity-50 ${active ? "bg-red-50 text-red-700 hover:bg-red-100" : "bg-green-50 text-green-700 hover:bg-green-100"}`}
                        >
                          {active ? "Remove Access" : "Restore Access"}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Users
