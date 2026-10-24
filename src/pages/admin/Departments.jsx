import { useCallback, useEffect, useMemo, useState } from "react"
import { usePatient } from "../../assets/context/PatientContext.jsx"
import api from "../../services/api.js"

const EMPTY_FORM = { name: "", code: "", head: "", description: "", status: "Active" }
const rows = (data) => (Array.isArray(data) ? data : data?.results || [])

// Departments / clinics of the selected hospital, saved through the API.
// Only that hospital's Admin or Hospital Manager can change them (enforced
// by the backend; others see the server's refusal).
function Departments() {
  const { selectedHospital } = usePatient()
  const [departments, setDepartments] = useState([])
  const [doctors, setDoctors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("All")
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [formData, setFormData] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!selectedHospital) return
    setLoading(true)
    setError("")
    try {
      const [deptData, doctorData] = await Promise.all([
        api.departments.list(selectedHospital.id),
        api.doctors.list(selectedHospital.id),
      ])
      setDepartments(rows(deptData))
      setDoctors(rows(doctorData))
    } catch (err) {
      setError(err.message || "Could not load departments.")
    } finally {
      setLoading(false)
    }
  }, [selectedHospital])

  useEffect(() => {
    load()
  }, [load])

  const openAdd = () => {
    setEditing(null)
    setFormData(EMPTY_FORM)
    setShowModal(true)
  }

  const openEdit = (dept) => {
    setEditing(dept)
    setFormData({
      name: dept.name,
      code: dept.code || "",
      head: dept.head ? String(dept.head) : "",
      description: dept.description || "",
      status: dept.is_active ? "Active" : "Inactive",
    })
    setShowModal(true)
  }

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.name.trim()) {
      setError("Please enter department name")
      return
    }
    const payload = {
      hospital: selectedHospital.id,
      name: formData.name.trim(),
      code: formData.code.trim().toUpperCase(),
      head: formData.head ? Number(formData.head) : null,
      description: formData.description,
      is_active: formData.status === "Active",
    }
    setSaving(true)
    setError("")
    try {
      if (editing) {
        await api.departments.update(editing.id, payload)
      } else {
        await api.departments.create(payload)
      }
      setShowModal(false)
      await load()
    } catch (err) {
      setError(err.message || "Department was not saved.")
    } finally {
      setSaving(false)
    }
  }

  const toggleStatus = async (dept) => {
    setError("")
    try {
      await api.departments.update(dept.id, { is_active: !dept.is_active })
      await load()
    } catch (err) {
      setError(err.message || "Status was not changed.")
    }
  }

  const filtered = useMemo(() => {
    const text = search.toLowerCase().trim()
    return departments.filter((dept) => {
      const matchesSearch =
        !text || [dept.name, dept.code, dept.head_name].filter(Boolean).some((v) => v.toLowerCase().includes(text))
      const matchesStatus =
        statusFilter === "All" || (statusFilter === "Active" ? dept.is_active : !dept.is_active)
      return matchesSearch && matchesStatus
    })
  }, [departments, search, statusFilter])

  const activeCount = departments.filter((d) => d.is_active).length
  const doctorCount = departments.reduce((sum, d) => sum + (d.doctors || 0), 0)

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Departments</h1>
          <p className="text-gray-500 mt-1">Departments and clinics of {selectedHospital?.name || "the selected hospital"}</p>
        </div>
        <button onClick={openAdd} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium">
          + Add Department
        </button>
      </div>

      {error && !showModal && (
        <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">Total Departments</p>
          <h2 className="text-3xl font-bold mt-2">{departments.length}</h2>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">Active</p>
          <h2 className="text-3xl font-bold text-green-600 mt-2">{activeCount}</h2>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-gray-500 text-sm">Doctors Assigned</p>
          <h2 className="text-3xl font-bold text-blue-600 mt-2">{doctorCount}</h2>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          <input
            type="text"
            aria-label="Search departments"
            placeholder="Search by name, code or head"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2.5"
          />
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
          <p className="text-gray-500 text-sm" role="status">Loading departments…</p>
        ) : filtered.length === 0 ? (
          <p className="text-gray-500 text-sm">No departments yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4">Department</th>
                  <th className="py-2 pr-4">Code</th>
                  <th className="py-2 pr-4">Head</th>
                  <th className="py-2 pr-4">Doctors</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((dept) => (
                  <tr key={dept.id} className="border-b last:border-0">
                    <td className="py-3 pr-4 font-medium text-gray-800">{dept.name}</td>
                    <td className="py-3 pr-4">{dept.code || "—"}</td>
                    <td className="py-3 pr-4">{dept.head_name || "—"}</td>
                    <td className="py-3 pr-4">{dept.doctors}</td>
                    <td className="py-3 pr-4">
                      <button
                        onClick={() => toggleStatus(dept)}
                        className={`px-3 py-1 rounded-full text-xs font-medium ${dept.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}
                      >
                        {dept.is_active ? "Active" : "Inactive"}
                      </button>
                    </td>
                    <td className="py-3 text-right">
                      <button onClick={() => openEdit(dept)} className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg">
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" role="dialog" aria-modal="true">
          <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4">
            <h2 className="text-xl font-bold text-gray-800">{editing ? "Edit Department" : "Add Department"}</h2>
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
                {error}
              </div>
            )}
            <label className="block text-sm font-medium text-gray-700">
              Department Name
              <input name="name" value={formData.name} onChange={handleChange} required className="mt-1 w-full border border-gray-300 rounded-lg px-4 py-2.5" />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Code
              <input name="code" value={formData.code} onChange={handleChange} maxLength={20} className="mt-1 w-full border border-gray-300 rounded-lg px-4 py-2.5" />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Head of Department
              <select name="head" value={formData.head} onChange={handleChange} className="mt-1 w-full border border-gray-300 rounded-lg px-4 py-2.5">
                <option value="">Not assigned</option>
                {doctors.map((doctor) => (
                  <option key={doctor.id} value={doctor.id}>{doctor.name}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Description
              <textarea name="description" value={formData.description} onChange={handleChange} rows={2} className="mt-1 w-full border border-gray-300 rounded-lg px-4 py-2.5" />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Status
              <select name="status" value={formData.status} onChange={handleChange} className="mt-1 w-full border border-gray-300 rounded-lg px-4 py-2.5">
                <option>Active</option>
                <option>Inactive</option>
              </select>
            </label>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => { setShowModal(false); setError("") }} className="px-5 py-2.5 bg-gray-100 rounded-lg">Cancel</button>
              <button type="submit" disabled={saving} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50">
                {saving ? "Saving…" : editing ? "Update Department" : "Add Department"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

export default Departments
