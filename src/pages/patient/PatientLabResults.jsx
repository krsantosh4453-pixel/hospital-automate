import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"

function PatientLabResults() {
  const { patient } = useAuth()
  const [labTests, setLabTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState("all")

  useEffect(() => {
    if (!patient?.id) return

    const fetchLabTests = async () => {
      setLoading(true)
      try {
        const data = await api.laboratory.tests.list()
        const allTests = data?.results || data || []
        const patientTests = allTests.filter(
          (t) => String(t.patient) === String(patient.id)
        )
        setLabTests(patientTests)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchLabTests()
  }, [patient?.id])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  const filteredTests = labTests.filter((test) => {
    if (filter === "all") return true
    if (filter === "pending") return test.status === "Pending"
    if (filter === "completed") return test.status === "Completed"
    return true
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Lab Results</h1>
          <p className="text-gray-500 mt-1">View your laboratory test results</p>
        </div>
        <div className="flex gap-2">
          {["all", "pending", "completed"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
                filter === f
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-200"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">⚠️ {error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : filteredTests.length > 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Test</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Date</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Status</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Result</th>
                  <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredTests.map((test) => (
                  <tr key={test.id} className="hover:bg-gray-50">
                    <td className="px-5 py-4">
                      <p className="font-medium text-gray-800">{test.test_name || test.name || "Lab Test"}</p>
                      {test.category && <p className="text-sm text-gray-500">{test.category}</p>}
                    </td>
                    <td className="px-5 py-4 text-gray-700">{formatDate(test.requested_date || test.created_at)}</td>
                    <td className="px-5 py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        test.status === "Pending" ? "bg-orange-100 text-orange-700" :
                        test.status === "Completed" ? "bg-green-100 text-green-700" :
                        "bg-gray-100 text-gray-700"
                      }`}>
                        {test.status}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      {test.result_value ? (
                        <span className="font-medium text-green-700">{test.result_value} {test.unit || ""}</span>
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      {test.status === "Completed" && test.result_file && (
                        <a href={test.result_file} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                          View Report
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
          <div className="text-4xl mb-3">🧪</div>
          <h3 className="font-bold text-gray-800">No lab results found</h3>
          <p className="text-sm text-gray-500 mt-1">You don't have any lab tests matching this filter.</p>
        </div>
      )}
    </div>
  )
}

export default PatientLabResults