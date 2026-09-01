import { useState } from "react"

function Laboratory() {
  const [tests, setTests] = useState([
    {
      id: "LAB001",
      patient: "Rahul Kumar",
      test: "Complete Blood Count",
      doctor: "Dr. Sharma",
      date: "01 Sep 2026",
      priority: "Normal",
      status: "Completed",
      result: "Normal",
    },
    {
      id: "LAB002",
      patient: "Priya Singh",
      test: "Blood Sugar",
      doctor: "Dr. Verma",
      date: "01 Sep 2026",
      priority: "Urgent",
      status: "Processing",
      result: "Pending",
    },
    {
      id: "LAB003",
      patient: "Amit Kumar",
      test: "Lipid Profile",
      doctor: "Dr. Singh",
      date: "01 Sep 2026",
      priority: "Normal",
      status: "Pending",
      result: "Pending",
    },
  ])

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] =
    useState("All Status")

  const [priorityFilter, setPriorityFilter] =
    useState("All Priority")

  const [showForm, setShowForm] = useState(false)
  const [showView, setShowView] = useState(false)

  const [selectedTest, setSelectedTest] =
    useState(null)

  const [formData, setFormData] = useState({
    patient: "",
    test: "",
    doctor: "",
    date: "",
    priority: "Normal",
  })

  const filteredTests = tests.filter((test) => {
    const matchesSearch =
      test.patient
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      test.test
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      test.id
        .toLowerCase()
        .includes(search.toLowerCase())

    const matchesStatus =
      statusFilter === "All Status" ||
      test.status === statusFilter

    const matchesPriority =
      priorityFilter === "All Priority" ||
      test.priority === priorityFilter

    return (
      matchesSearch &&
      matchesStatus &&
      matchesPriority
    )
  })

  const pendingCount = tests.filter(
    (test) => test.status === "Pending"
  ).length

  const processingCount = tests.filter(
    (test) => test.status === "Processing"
  ).length

  const completedCount = tests.filter(
    (test) => test.status === "Completed"
  ).length

  const handleChange = (e) => {
    const { name, value } = e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }

  const resetForm = () => {
    setFormData({
      patient: "",
      test: "",
      doctor: "",
      date: "",
      priority: "Normal",
    })

    setSelectedTest(null)
    setShowForm(false)
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    const newTest = {
      id: `LAB${String(tests.length + 1).padStart(3, "0")}`,
      patient: formData.patient,
      test: formData.test,
      doctor: formData.doctor,
      date: formData.date,
      priority: formData.priority,
      status: "Pending",
      result: "Pending",
    }

    setTests([...tests, newTest])

    resetForm()
  }

  const handleView = (test) => {
    setSelectedTest(test)
    setShowView(true)
  }

  const handleEdit = (test) => {
    setSelectedTest(test)

    setFormData({
      patient: test.patient,
      test: test.test,
      doctor: test.doctor,
      date: test.date,
      priority: test.priority,
    })

    setShowForm(true)
  }

  const handleUpdate = (e) => {
    e.preventDefault()

    const updatedTests = tests.map((test) =>
      test.id === selectedTest.id
        ? {
          ...test,
          patient: formData.patient,
          test: formData.test,
          doctor: formData.doctor,
          date: formData.date,
          priority: formData.priority,
        }
        : test
    )

    setTests(updatedTests)

    resetForm()
  }

  const handleDelete = (id) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this laboratory test?"
    )

    if (!confirmed) return

    setTests(
      tests.filter((test) => test.id !== id)
    )
  }

  const handleProcess = (id) => {
    setTests(
      tests.map((test) =>
        test.id === id
          ? {
            ...test,
            status: "Processing",
          }
          : test
      )
    )
  }

  const handleComplete = (id) => {
    setTests(
      tests.map((test) =>
        test.id === id
          ? {
            ...test,
            status: "Completed",
            result: "Normal",
          }
          : test
      )
    )
  }

  const getStatusClass = (status) => {
    if (status === "Completed") {
      return "bg-green-100 text-green-700"
    }

    if (status === "Processing") {
      return "bg-blue-100 text-blue-700"
    }

    return "bg-orange-100 text-orange-700"
  }

  return (
    <div>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">

        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            Laboratory
          </h1>

          <p className="text-gray-500 mt-1">
            Manage laboratory tests, samples and reports
          </p>
        </div>

        <button
          onClick={() => {
            setSelectedTest(null)
            setShowForm(true)
          }}
          className="bg-blue-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-blue-700 transition"
        >
          + New Lab Test
        </button>

      </div>


      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-6">

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Total Tests
          </p>

          <h2 className="text-3xl font-bold text-blue-600 mt-3">
            {tests.length}
          </h2>

        </div>


        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Pending
          </p>

          <h2 className="text-3xl font-bold text-orange-500 mt-3">
            {pendingCount}
          </h2>

        </div>


        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Processing
          </p>

          <h2 className="text-3xl font-bold text-blue-600 mt-3">
            {processingCount}
          </h2>

        </div>


        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Completed
          </p>

          <h2 className="text-3xl font-bold text-green-600 mt-3">
            {completedCount}
          </h2>

        </div>

      </div>


      {/* Search & Filters */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search patient, test or ID..."
            className="border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
          />

          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value)
            }
            className="border border-gray-300 rounded-xl px-4 py-3"
          >
            <option>All Status</option>
            <option>Pending</option>
            <option>Processing</option>
            <option>Completed</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) =>
              setPriorityFilter(e.target.value)
            }
            className="border border-gray-300 rounded-xl px-4 py-3"
          >
            <option>All Priority</option>
            <option>Normal</option>
            <option>Urgent</option>
          </select>

        </div>

      </div>


      {/* Laboratory Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

        <div className="p-6 border-b">

          <h2 className="text-xl font-bold text-gray-800">
            Laboratory Tests
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            {filteredTests.length} test(s) found
          </p>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-gray-50">

              <tr>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Test ID
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Patient
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Test
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Doctor
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Date
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Priority
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Status
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Actions
                </th>

              </tr>

            </thead>


            <tbody>

              {filteredTests.length === 0 ? (

                <tr>

                  <td
                    colSpan="8"
                    className="text-center py-12 text-gray-500"
                  >
                    No laboratory tests found
                  </td>

                </tr>

              ) : (

                filteredTests.map((test) => (

                  <tr
                    key={test.id}
                    className="border-t hover:bg-gray-50"
                  >

                    <td className="px-6 py-4 font-semibold text-blue-600">
                      {test.id}
                    </td>


                    <td className="px-6 py-4">

                      <p className="font-semibold text-gray-800">
                        {test.patient}
                      </p>

                    </td>


                    <td className="px-6 py-4 text-gray-700">
                      {test.test}
                    </td>


                    <td className="px-6 py-4 text-gray-600">
                      {test.doctor}
                    </td>


                    <td className="px-6 py-4 text-gray-600">
                      {test.date}
                    </td>


                    <td className="px-6 py-4">

                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${test.priority === "Urgent"
                            ? "bg-red-100 text-red-700"
                            : "bg-gray-100 text-gray-700"
                          }`}
                      >
                        {test.priority}
                      </span>

                    </td>


                    <td className="px-6 py-4">

                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                          test.status
                        )}`}
                      >
                        {test.status}
                      </span>

                    </td>


                    <td className="px-6 py-4">

                      <div className="flex gap-2 flex-wrap">

                        <button
                          onClick={() =>
                            handleView(test)
                          }
                          className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg"
                        >
                          View
                        </button>


                        <button
                          onClick={() =>
                            handleEdit(test)
                          }
                          className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg"
                        >
                          Edit
                        </button>


                        {test.status === "Pending" && (

                          <button
                            onClick={() =>
                              handleProcess(test.id)
                            }
                            className="px-3 py-2 text-sm bg-indigo-50 text-indigo-700 rounded-lg"
                          >
                            Process
                          </button>

                        )}


                        {test.status === "Processing" && (

                          <button
                            onClick={() =>
                              handleComplete(test.id)
                            }
                            className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg"
                          >
                            Complete
                          </button>

                        )}


                        <button
                          onClick={() =>
                            handleDelete(test.id)
                          }
                          className="px-3 py-2 text-sm bg-red-50 text-red-700 rounded-lg"
                        >
                          Delete
                        </button>

                      </div>

                    </td>

                  </tr>

                ))

              )}

            </tbody>

          </table>

        </div>

      </div>


      {/* Add / Edit Modal */}
      {showForm && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">

            <div className="flex justify-between items-center p-6 border-b">

              <div>

                <h2 className="text-xl font-bold text-gray-800">
                  {selectedTest
                    ? "Edit Lab Test"
                    : "New Lab Test"}
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Enter laboratory test details
                </p>

              </div>

              <button
                onClick={resetForm}
                className="text-2xl text-gray-500"
              >
                ×
              </button>

            </div>


            <form
              onSubmit={
                selectedTest
                  ? handleUpdate
                  : handleSubmit
              }
              className="p-6 space-y-4"
            >

              {/* Patient */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Patient
                </label>

                <select
                  name="patient"
                  value={formData.patient}
                  onChange={handleChange}
                  required
                  className="w-full border border-gray-300 rounded-xl px-4 py-3"
                >

                  <option value="">
                    Select Patient
                  </option>

                  <option>Rahul Kumar</option>
                  <option>Priya Singh</option>
                  <option>Amit Kumar</option>

                </select>

              </div>


              {/* Test */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Laboratory Test
                </label>

                <select
                  name="test"
                  value={formData.test}
                  onChange={handleChange}
                  required
                  className="w-full border border-gray-300 rounded-xl px-4 py-3"
                >

                  <option value="">
                    Select Test
                  </option>

                  <option>
                    Complete Blood Count
                  </option>

                  <option>
                    Blood Sugar
                  </option>

                  <option>
                    Lipid Profile
                  </option>

                  <option>
                    Liver Function Test
                  </option>

                  <option>
                    Kidney Function Test
                  </option>

                  <option>
                    Thyroid Profile
                  </option>

                </select>

              </div>


              {/* Doctor */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Referring Doctor
                </label>

                <select
                  name="doctor"
                  value={formData.doctor}
                  onChange={handleChange}
                  required
                  className="w-full border border-gray-300 rounded-xl px-4 py-3"
                >

                  <option value="">
                    Select Doctor
                  </option>

                  <option>Dr. Sharma</option>
                  <option>Dr. Verma</option>
                  <option>Dr. Singh</option>

                </select>

              </div>


              {/* Date */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Test Date
                </label>

                <input
                  type="date"
                  name="date"
                  value={formData.date}
                  onChange={handleChange}
                  required
                  className="w-full border border-gray-300 rounded-xl px-4 py-3"
                />

              </div>


              {/* Priority */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Priority
                </label>

                <select
                  name="priority"
                  value={formData.priority}
                  onChange={handleChange}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3"
                >

                  <option>Normal</option>
                  <option>Urgent</option>

                </select>

              </div>


              {/* Buttons */}
              <div className="flex justify-end gap-3 pt-4">

                <button
                  type="button"
                  onClick={resetForm}
                  className="px-5 py-3 border border-gray-300 rounded-xl"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700"
                >
                  {selectedTest
                    ? "Save Changes"
                    : "Create Test"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}


      {/* View Modal */}
      {showView && selectedTest && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">

            <div className="flex justify-between items-center p-6 border-b">

              <div>

                <h2 className="text-xl font-bold text-gray-800">
                  Laboratory Test
                </h2>

                <p className="text-sm text-blue-600 mt-1">
                  {selectedTest.id}
                </p>

              </div>

              <button
                onClick={() => setShowView(false)}
                className="text-2xl text-gray-500"
              >
                ×
              </button>

            </div>


            <div className="p-6 space-y-5">

              <div>
                <p className="text-sm text-gray-500">
                  Patient
                </p>

                <p className="font-semibold text-gray-800">
                  {selectedTest.patient}
                </p>
              </div>


              <div>
                <p className="text-sm text-gray-500">
                  Laboratory Test
                </p>

                <p className="font-semibold text-gray-800">
                  {selectedTest.test}
                </p>
              </div>


              <div>
                <p className="text-sm text-gray-500">
                  Referring Doctor
                </p>

                <p className="font-semibold text-gray-800">
                  {selectedTest.doctor}
                </p>
              </div>


              <div className="grid grid-cols-2 gap-4">

                <div className="bg-gray-50 rounded-xl p-4">

                  <p className="text-xs text-gray-500">
                    Date
                  </p>

                  <p className="font-semibold mt-1">
                    {selectedTest.date}
                  </p>

                </div>


                <div className="bg-gray-50 rounded-xl p-4">

                  <p className="text-xs text-gray-500">
                    Priority
                  </p>

                  <p className="font-semibold mt-1">
                    {selectedTest.priority}
                  </p>

                </div>

              </div>


              <div>

                <p className="text-sm text-gray-500">
                  Status
                </p>

                <span
                  className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                    selectedTest.status
                  )}`}
                >
                  {selectedTest.status}
                </span>

              </div>


              <div>

                <p className="text-sm text-gray-500">
                  Result
                </p>

                <p className="font-semibold text-gray-800 mt-1">
                  {selectedTest.result}
                </p>

              </div>

            </div>


            <div className="p-6 border-t flex justify-end">

              <button
                onClick={() => setShowView(false)}
                className="px-5 py-3 bg-gray-800 text-white rounded-xl"
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

export default Laboratory