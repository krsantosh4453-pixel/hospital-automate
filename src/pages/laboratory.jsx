import { useState, useEffect } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"

function Laboratory() {

  const { selectedHospital } = usePatient()

  const [tests, setTests] = useState([])
  const [patientOptions, setPatientOptions] = useState([])
  const [doctorOptions, setDoctorOptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)

  // Backend workflow status -> the three summary states this page shows.
  const SUMMARY = {
    Ordered: "Pending",
    "Sample Pending": "Pending",
    Collected: "Processing",
    Dispatched: "Processing",
    Received: "Processing",
    Processing: "Processing",
    "Result Entered": "Processing",
    Verified: "Processing",
    Released: "Completed",
    Cancelled: "Cancelled",
  }

  // Next lab action for each stage (label, client method, needs a result text).
  const NEXT_STEP = {
    Ordered: ["Collect Sample", "collectSample"],
    "Sample Pending": ["Collect Sample", "collectSample"],
    Collected: ["Dispatch Sample", "dispatchSample"],
    Dispatched: ["Receive in Lab", "receiveSample"],
    Received: ["Start Processing", "startProcessing"],
    Processing: ["Enter Result", "enterResult", true],
    "Result Entered": ["Verify Result", "verifyResult"],
    Verified: ["Release Result", "releaseResult"],
  }

  const rows = (data) => (Array.isArray(data) ? data : data?.results || [])

  const toRow = (t) => ({
    id: `LAB-${t.id}`,
    apiId: t.id,
    patient: t.patient_name || `Patient #${t.patient}`,
    patientId: t.patient,
    test: t.name,
    doctor: t.doctor_name || "",
    doctorId: t.doctor,
    date: t.test_date ? new Date(t.test_date).toLocaleDateString("en-IN") : "",
    priority: t.priority || "Normal",
    stage: t.status,
    status: SUMMARY[t.status] || t.status,
    result: t.status === "Released" ? t.result || "—" : "Pending",
    hospitalId: t.hospital,
  })

  const loadTests = async () => {
    if (!selectedHospital) return
    setLoading(true)
    setError(null)
    try {
      const [testData, patientData, doctorData] = await Promise.all([
        api.laboratory.tests.list(selectedHospital.id),
        api.patients.list(selectedHospital.id),
        api.doctors.list(selectedHospital.id),
      ])
      setTests(rows(testData).map(toRow))
      setPatientOptions(rows(patientData))
      setDoctorOptions(rows(doctorData))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTests()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHospital?.id])

  const testsData = tests

  const [search, setSearch] = useState("")

  const [statusFilter, setStatusFilter] =
    useState("All Status")

  const [priorityFilter, setPriorityFilter] =
    useState("All Priority")

  const [showForm, setShowForm] =
    useState(false)

  const [showView, setShowView] =
    useState(false)

  const [selectedTest, setSelectedTest] =
    useState(null)

  const [formData, setFormData] = useState({
    patient: "",
    test: "",
    doctor: "",
    date: "",
    priority: "Normal",
  })


  // =========================
  // Selected Hospital Tests
  // =========================

  const hospitalTests = selectedHospital
    ? testsData.filter(
      (test) =>
        test.hospitalId ===
        selectedHospital.id
    )
    : []


  // =========================
  // Filter Tests
  // =========================

  const filteredTests =
    hospitalTests.filter((test) => {

      const matchesSearch =
        test.patient
          .toLowerCase()
          .includes(
            search.toLowerCase()
          ) ||
        test.test
          .toLowerCase()
          .includes(
            search.toLowerCase()
          ) ||
        String(test.id)
          .toLowerCase()
          .includes(
            search.toLowerCase()
          )

      const matchesStatus =
        statusFilter ===
        "All Status" ||
        test.status ===
        statusFilter

      const matchesPriority =
        priorityFilter ===
        "All Priority" ||
        test.priority ===
        priorityFilter

      return (
        matchesSearch &&
        matchesStatus &&
        matchesPriority
      )
    })


  // =========================
  // Statistics
  // =========================

  const pendingCount =
    hospitalTests.filter(
      (test) =>
        test.status ===
        "Pending"
    ).length

  const processingCount =
    hospitalTests.filter(
      (test) =>
        test.status ===
        "Processing"
    ).length

  const completedCount =
    hospitalTests.filter(
      (test) =>
        test.status ===
        "Completed"
    ).length


  // =========================
  // Form Change
  // =========================

  const handleChange = (e) => {

    const { name, value } =
      e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }


  // =========================
  // Reset Form
  // =========================

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


  // =========================
  // New Lab Test
  // =========================

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!selectedHospital) {
      alert(
        "Please select a hospital first."
      )
      return
    }

    try {
      await api.laboratory.tests.create({
        hospital: selectedHospital.id,
        patient: Number(formData.patient),
        doctor: formData.doctor ? Number(formData.doctor) : null,
        name: formData.test,
        priority: formData.priority,
      })
      resetForm()
      await loadTests()
    } catch (err) {
      alert(`Lab order was not created: ${err.message}`)
    }
  }

  // =========================
  // View
  // =========================

  const handleView = (test) => {

    setSelectedTest(test)

    setShowView(true)
  }


  // =========================
  // Edit
  // =========================

  const handleEdit = (test) => {

    setSelectedTest(test)

    setFormData({

      patient:
        test.patient,

      test:
        test.test,

      doctor:
        test.doctor,

      date:
        test.date,

      priority:
        test.priority,
    })

    setShowForm(true)
  }


  // =========================
  // Update
  // =========================

  const handleUpdate = async (e) => {
    e.preventDefault()

    try {
      await api.laboratory.tests.update(selectedTest.apiId, {
        hospital: selectedHospital.id,
        patient: selectedTest.patientId,
        name: formData.test,
        doctor: formData.doctor ? Number(formData.doctor) : null,
        priority: formData.priority,
      })
      resetForm()
      await loadTests()
    } catch (err) {
      alert(`Lab order was not updated: ${err.message}`)
    }
  }

  // =========================
  // Delete
  // =========================

  const handleDelete = async (id) => {
    const test = tests.find((t) => t.id === id)
    const confirmed =
      window.confirm(
        "Cancel this laboratory order? It stays in the record as cancelled."
      )

    if (!confirmed || !test) {
      return
    }

    try {
      await api.laboratory.tests.cancel(test.apiId)
      await loadTests()
    } catch (err) {
      alert(`Order was not cancelled: ${err.message}`)
    }
  }

  // =========================
  // Process
  // =========================

  const handleProcess = async (id) => {
    const test = tests.find((t) => t.id === id)
    const step = test && NEXT_STEP[test.stage]
    if (!step) return
    const [label, method, needsResult] = step
    let payload = {}
    if (needsResult) {
      const resultText = window.prompt(`Result for ${test.test} (${test.patient}):`)
      if (!resultText || !resultText.trim()) return
      payload = { result_text: resultText.trim() }
    }
    setBusyId(id)
    try {
      await api.laboratory.tests[method](test.apiId, payload)
      await loadTests()
    } catch (err) {
      alert(`${label} failed: ${err.message}`)
    } finally {
      setBusyId(null)
    }
  }

  // =========================
  // Status Style
  // =========================

  const getStatusClass = (
    status
  ) => {

    if (
      status ===
      "Completed"
    ) {
      return "bg-green-100 text-green-700"
    }

    if (
      status ===
      "Processing"
    ) {
      return "bg-blue-100 text-blue-700"
    }

    return "bg-orange-100 text-orange-700"
  }


  return (

    <div>


      {/* =========================
          Header
      ========================= */}

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

            if (!selectedHospital) {

              alert(
                "Please select a hospital first."
              )

              return
            }

            setSelectedTest(null)

            setFormData({
              patient: "",
              test: "",
              doctor: "",
              date: "",
              priority: "Normal",
            })

            setShowForm(true)

          }}
          className="bg-blue-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-blue-700 transition"
        >
          + New Lab Test
        </button>

      </div>


      {/* =========================
          Current Hospital
      ========================= */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

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

          <div>

            <p className="font-semibold text-orange-600">
              ⚠️ No hospital selected
            </p>

            <p className="text-sm text-gray-500 mt-1">
              Select a hospital from the header first.
            </p>

          </div>

        )}

      </div>


      {/* =========================
          No Hospital
      ========================= */}

      {!selectedHospital ? (

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">

          <div className="text-5xl mb-4">
            🧪
          </div>

          <h2 className="text-xl font-bold text-gray-800">
            Select a Hospital
          </h2>

          <p className="text-gray-500 mt-2">
            Select a hospital from the header to view laboratory tests.
          </p>

        </div>

      ) : (

        <>


          {/* =========================
              Statistics
          ========================= */}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-6">

            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

              <p className="text-sm text-gray-500">
                Total Tests
              </p>

              <h2 className="text-3xl font-bold text-blue-600 mt-3">
                {hospitalTests.length}
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


          {/* =========================
              Search & Filters
          ========================= */}

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

              <input
                type="text"
                value={search}
                onChange={(e) =>
                  setSearch(
                    e.target.value
                  )
                }
                placeholder="Search patient, test or ID..."
                className="border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              />


              <select
                value={statusFilter}
                onChange={(e) =>
                  setStatusFilter(
                    e.target.value
                  )
                }
                className="border border-gray-300 rounded-xl px-4 py-3"
              >

                <option>
                  All Status
                </option>

                <option>
                  Pending
                </option>

                <option>
                  Processing
                </option>

                <option>
                  Completed
                </option>

              </select>


              <select
                value={priorityFilter}
                onChange={(e) =>
                  setPriorityFilter(
                    e.target.value
                  )
                }
                className="border border-gray-300 rounded-xl px-4 py-3"
              >

                <option>
                  All Priority
                </option>

                <option>
                  Normal
                </option>

                <option>
                  Urgent
                </option>

              </select>

            </div>

          </div>


          {/* =========================
              Laboratory Table
          ========================= */}

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

                    filteredTests.map(
                      (test) => (

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
                              className={`px-3 py-1 rounded-full text-xs font-medium ${test.priority ===
                                  "Urgent"
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
                                  handleView(
                                    test
                                  )
                                }
                                className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg"
                              >
                                View
                              </button>


                              <button
                                onClick={() =>
                                  handleEdit(
                                    test
                                  )
                                }
                                className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg"
                              >
                                Edit
                              </button>


                              {NEXT_STEP[test.stage] && (

                                  <button
                                    onClick={() =>
                                      handleProcess(
                                        test.id
                                      )
                                    }
                                    disabled={busyId === test.id}
                                    className="px-3 py-2 text-sm bg-indigo-50 text-indigo-700 rounded-lg disabled:opacity-50"
                                  >
                                    {NEXT_STEP[test.stage][0]}
                                  </button>

                                )}


                              <button
                                onClick={() =>
                                  handleDelete(
                                    test.id
                                  )
                                }
                                className="px-3 py-2 text-sm bg-red-50 text-red-700 rounded-lg"
                              >
                                Cancel Order
                              </button>

                            </div>

                          </td>

                        </tr>

                      )
                    )

                  )}

                </tbody>

              </table>

            </div>

          </div>


          {/* =========================
              Add / Edit Modal
          ========================= */}

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
                      {selectedHospital.name}
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
                      disabled={Boolean(selectedTest)}
                      value={
                        formData.patient
                      }
                      onChange={
                        handleChange
                      }
                      required
                      className="w-full border border-gray-300 rounded-xl px-4 py-3"
                    >

                      <option value="">
                        Select Patient
                      </option>

                      {patientOptions.map((patient) => (
                        <option key={patient.id} value={patient.id}>
                          {patient.name}
                        </option>
                      ))}

                    </select>

                  </div>


                  {/* Test */}

                  <div>

                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Laboratory Test
                    </label>

                    <select
                      name="test"
                      value={
                        formData.test
                      }
                      onChange={
                        handleChange
                      }
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
                      value={
                        formData.doctor
                      }
                      onChange={
                        handleChange
                      }
                      className="w-full border border-gray-300 rounded-xl px-4 py-3"
                    >

                      <option value="">
                        Select Doctor
                      </option>

                      {doctorOptions.map((doctor) => (
                        <option key={doctor.id} value={doctor.id}>
                          {doctor.name}
                        </option>
                      ))}

                    </select>

                  </div>


                  {/* The order date is set by the server when the order is created. */}


                  {/* Priority */}

                  <div>

                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Priority
                    </label>

                    <select
                      name="priority"
                      value={
                        formData.priority
                      }
                      onChange={
                        handleChange
                      }
                      className="w-full border border-gray-300 rounded-xl px-4 py-3"
                    >

                      <option>
                        Normal
                      </option>

                      <option>
                        Urgent
                      </option>

                    </select>

                  </div>


                  {/* Buttons */}

                  <div className="flex justify-end gap-3 pt-4">

                    <button
                      type="button"
                      onClick={
                        resetForm
                      }
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


          {/* =========================
              View Modal
          ========================= */}

          {showView &&
            selectedTest && (

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
                      onClick={() =>
                        setShowView(
                          false
                        )
                      }
                      className="text-2xl text-gray-500"
                    >
                      ×
                    </button>

                  </div>


                  <div className="p-6 space-y-5">

                    <div>

                      <p className="text-sm text-gray-500">
                        Hospital
                      </p>

                      <p className="font-semibold text-gray-800">
                        {selectedHospital.name}
                      </p>

                    </div>


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
                        {
                          selectedTest.status
                        }
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
                      onClick={() =>
                        setShowView(
                          false
                        )
                      }
                      className="px-5 py-3 bg-gray-800 text-white rounded-xl"
                    >
                      Close
                    </button>

                  </div>

                </div>

              </div>

            )}

        </>

      )}

    </div>
  )
}

export default Laboratory