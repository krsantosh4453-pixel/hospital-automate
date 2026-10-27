import { useCallback, useEffect, useMemo, useState } from "react"
import { usePatient } from "../../assets/context/PatientContext.jsx"
import api from "../../services/api.js"
import { UserPlus } from "lucide-react"
import { Alert, Badge, Button, Card, CardBody, CardHeader, PageHeader, useConfirm } from "../../components/ui"
import InviteStaffForm, { InviteLink } from "../../components/admin/InviteStaffForm.jsx"
import { STAFF_ROLES as ROLES } from "../../config/staffRoles.js"

// Staff of the selected hospital, managed through /api/users/. Staff are
// invited here (they set a password from the link) or register themselves
// and are approved here; the backend only lets this hospital's Admin or
// Hospital Manager make these changes.
function Users() {
  const [confirm, confirmDialog] = useConfirm()

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
  const [departments, setDepartments] = useState([])
  const [showInvite, setShowInvite] = useState(false)
  const [newLink, setNewLink] = useState(null)

  const load = useCallback(async () => {
    if (!selectedHospital) return
    setLoading(true)
    setError("")
    try {
      const [data, deptData] = await Promise.all([
        api.users.list(),
        // The staff list still loads if departments cannot be read.
        api.departments.list(selectedHospital.id).catch(() => []),
      ])
      setStaff(data.staff || [])
      setPending(data.pending || [])
      setDepartments(Array.isArray(deptData) ? deptData : deptData?.results || [])
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

  // A Receptionist or Nurse with a department sees only that department's queue.
  const changeDepartment = (member, departmentId) => {
    const name = departments.find((d) => String(d.id) === departmentId)?.name
    run(
      member.id,
      () => api.users.updateMembership(member.id, { department: departmentId ? Number(departmentId) : null }),
      name ? `${member.name} now works in ${name}.` : `${member.name} now works across all departments.`,
    )
  }

  const toggleActive = async (member) => {
    const active = !member.membership?.is_active
    if (!active && !(await confirm(`Remove ${member.name}'s access to this hospital?`))) return
    run(
      member.id,
      () => api.users.updateMembership(member.id, { is_active: active }),
      active ? `${member.name} can sign in to this hospital again.` : `${member.name}'s access was removed.`,
    )
  }

  const resendInvite = (member) =>
    run(
      member.id,
      async () => setNewLink(await api.users.resendInvite(member.id)),
      `New invitation link for ${member.name} is below.`,
    )

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
    <>{confirmDialog}<div className="space-y-5">
      <PageHeader
        title="Users"
        description={`Staff of ${selectedHospital?.name || "the selected hospital"}. Invite staff with a role, or approve people who created an account.`}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Administration", to: "/admin" }, { label: "Users" }]}
        actions={
          <Button icon={UserPlus} onClick={() => setShowInvite(!showInvite)} aria-expanded={showInvite}>
            Invite staff
          </Button>
        }
      />

      {error && <Alert tone="danger">{error}</Alert>}
      {notice && !error && <Alert tone="success">{notice}</Alert>}
      <InviteLink key={newLink?.invite_url} result={newLink} />

      {showInvite && (
        <Card>
          <CardHeader
            title="Invite staff"
            icon={UserPlus}
            description="They get a link to set their password, then sign in with the role you choose."
          />
          <CardBody>
            <InviteStaffForm departments={departments} onInvited={load} />
          </CardBody>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="rounded-2xl border border-line bg-white p-5">
          <p className="text-gray-500 text-sm">Total Staff</p>
          <h2 className="text-3xl font-bold mt-2">{staff.length}</h2>
        </div>
        <div className="rounded-2xl border border-line bg-white p-5">
          <p className="text-gray-500 text-sm">Active</p>
          <h2 className="text-3xl font-bold text-green-600 mt-2">{activeCount}</h2>
        </div>
        <div className="rounded-2xl border border-line bg-white p-5">
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
                        className="hms-input"
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

      <div className="rounded-2xl border border-line bg-white p-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <input
            type="text"
            aria-label="Search staff"
            placeholder="Search by name, username, email or employee ID"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="hms-input"
          />
          <select
            aria-label="Filter by role"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="hms-input"
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
            className="hms-input"
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
                  <th className="py-2 pr-4">Department</th>
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
                          className="hms-input"
                        >
                          {ROLES.map((role) => (
                            <option key={role}>{role}</option>
                          ))}
                        </select>
                      </td>
                      <td className="py-3 pr-4">
                        <select
                          aria-label={`Department of ${member.name}`}
                          value={member.membership?.department ? String(member.membership.department) : ""}
                          disabled={busyId === member.id}
                          onChange={(e) => changeDepartment(member, e.target.value)}
                          className="hms-input"
                        >
                          <option value="">All departments</option>
                          {departments.map((dept) => (
                            <option key={dept.id} value={dept.id}>{dept.name}</option>
                          ))}
                        </select>
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}
                        >
                          {active ? "Active" : "Inactive"}
                        </span>
                        {member.invite_pending && (
                          <Badge tone="warning" className="ml-2">Invite pending</Badge>
                        )}
                      </td>
                      <td className="py-3 text-right whitespace-nowrap">
                        {member.invite_pending && active && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="mr-2"
                            disabled={busyId === member.id}
                            onClick={() => resendInvite(member)}
                          >
                            New link
                          </Button>
                        )}
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
    </div></>
  )
}

export default Users
