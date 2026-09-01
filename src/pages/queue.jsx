import { useState } from "react"

function Queue() {
  const [queue, setQueue] = useState([
    {
      token: 24,
      patient: "Rahul Kumar",
      doctor: "Dr. Sharma",
      department: "General Medicine",
      type: "Consultation",
      waiting: "14 min",
      status: "Waiting",
    },
    {
      token: 25,
      patient: "Priya Singh",
      doctor: "Dr. Sharma",
      department: "General Medicine",
      type: "Follow-up",
      waiting: "10 min",
      status: "Waiting",
    },
    {
      token: 26,
      patient: "Amit Kumar",
      doctor: "Dr. Verma",
      department: "Cardiology",
      type: "Consultation",
      waiting: "6 min",
      status: "Waiting",
    },
    {
      token: 27,
      patient: "Neha Singh",
      doctor: "Dr. Verma",
      department: "Cardiology",
      type: "Consultation",
      waiting: "2 min",
      status: "In Consultation",
    },
  ])

  const [departmentFilter, setDepartmentFilter] =
    useState("All Departments")

  const [statusFilter, setStatusFilter] =
    useState("All Status")

  const [search, setSearch] = useState("")

  const filteredQueue = queue.filter((item) => {
    const matchesSearch =
      item.patient
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      item.doctor
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      String(item.token).includes(search)

    const matchesDepartment =
      departmentFilter === "All Departments" ||
      item.department === departmentFilter

    const matchesStatus =
      statusFilter === "All Status" ||
      item.status === statusFilter

    return (
      matchesSearch &&
      matchesDepartment &&
      matchesStatus
    )
  })

  const waitingCount = queue.filter(
    (item) => item.status === "Waiting"
  ).length

  const consultationCount = queue.filter(
    (item) => item.status === "In Consultation"
  ).length

  const completedCount = queue.filter(
    (item) => item.status === "Completed"
  ).length

  const callNextPatient = () => {
    const nextPatient = queue.find(
      (item) => item.status === "Waiting"
    )

    if (!nextPatient) {
      alert("No waiting patient in the queue.")
      return
    }

    setQueue(
      queue.map((item) =>
        item.token === nextPatient.token
          ? {
            ...item,
            status: "In Consultation",
            waiting: "Now",
          }
          : item
      )
    )
  }

  const completePatient = (token) => {
    setQueue(
      queue.map((item) =>
        item.token === token
          ? {
            ...item,
            status: "Completed",
          }
          : item
      )
    )
  }

  const skipPatient = (token) => {
    setQueue(
      queue.map((item) =>
        item.token === token
          ? {
            ...item,
            status: "Skipped",
          }
          : item
      )
    )
  }

  const getStatusClass = (status) => {
    if (status === "Waiting") {
      return "bg-orange-100 text-orange-700"
    }

    if (status === "In Consultation") {
      return "bg-blue-100 text-blue-700"
    }

    if (status === "Completed") {
      return "bg-green-100 text-green-700"
    }

    return "bg-gray-100 text-gray-700"
  }

  return (
    <div>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">

        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            Queue Management
          </h1>

          <p className="text-gray-500 mt-1">
            Manage patient tokens and consultation queue
          </p>
        </div>

        <button
          onClick={callNextPatient}
          className="bg-blue-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-blue-700 transition"
        >
          📢 Call Next Patient
        </button>

      </div>


      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-6">

        {/* Current Token */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Current Token
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-blue-600">
              #27
            </h2>

            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-xl">
              🎫
            </div>

          </div>

        </div>


        {/* Waiting */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Waiting Patients
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-orange-500">
              {waitingCount}
            </h2>

            <div className="w-12 h-12 rounded-xl bg-orange-100 flex items-center justify-center text-xl">
              ⏳
            </div>

          </div>

        </div>


        {/* In Consultation */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            In Consultation
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-blue-600">
              {consultationCount}
            </h2>

            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-xl">
              👨‍⚕️
            </div>

          </div>

        </div>


        {/* Completed */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Completed
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-green-600">
              {completedCount}
            </h2>

            <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center text-xl">
              ✓
            </div>

          </div>

        </div>

      </div>


      {/* Current Queue Highlight */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5">

          <div>

            <p className="text-sm text-gray-500">
              Currently Serving
            </p>

            <h2 className="text-4xl font-bold text-blue-600 mt-2">
              Token #27
            </h2>

            <p className="text-gray-700 font-medium mt-2">
              Neha Singh
            </p>

            <p className="text-sm text-gray-500">
              Dr. Verma • Cardiology
            </p>

          </div>


          <div className="bg-blue-50 rounded-2xl p-6 text-center">

            <p className="text-sm text-gray-500">
              Status
            </p>

            <p className="text-blue-700 font-bold mt-1">
              In Consultation
            </p>

          </div>

        </div>

      </div>


      {/* Search & Filters */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <input
            type="text"
            placeholder="Search patient, doctor or token..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
          />


          <select
            value={departmentFilter}
            onChange={(e) =>
              setDepartmentFilter(e.target.value)
            }
            className="border border-gray-300 rounded-xl px-4 py-3"
          >

            <option>All Departments</option>
            <option>General Medicine</option>
            <option>Cardiology</option>
            <option>Neurology</option>

          </select>


          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value)
            }
            className="border border-gray-300 rounded-xl px-4 py-3"
          >

            <option>All Status</option>
            <option>Waiting</option>
            <option>In Consultation</option>
            <option>Completed</option>
            <option>Skipped</option>

          </select>

        </div>

      </div>


      {/* Queue Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

        <div className="p-6 border-b">

          <h2 className="text-xl font-bold text-gray-800">
            Patient Queue
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            {filteredQueue.length} patient(s) in queue
          </p>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-gray-50">

              <tr>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Token
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Patient
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Doctor
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Department
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Type
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Waiting
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

              {filteredQueue.length === 0 ? (

                <tr>

                  <td
                    colSpan="8"
                    className="text-center py-12 text-gray-500"
                  >
                    No patients found
                  </td>

                </tr>

              ) : (

                filteredQueue.map((item) => (

                  <tr
                    key={item.token}
                    className="border-t hover:bg-gray-50 transition"
                  >

                    {/* Token */}
                    <td className="px-6 py-4">

                      <span className="font-bold text-blue-600">
                        #{item.token}
                      </span>

                    </td>


                    {/* Patient */}
                    <td className="px-6 py-4">

                      <p className="font-semibold text-gray-800">
                        {item.patient}
                      </p>

                    </td>


                    {/* Doctor */}
                    <td className="px-6 py-4 text-gray-600">
                      {item.doctor}
                    </td>


                    {/* Department */}
                    <td className="px-6 py-4 text-gray-600">
                      {item.department}
                    </td>


                    {/* Type */}
                    <td className="px-6 py-4 text-gray-600">
                      {item.type}
                    </td>


                    {/* Waiting */}
                    <td className="px-6 py-4 text-gray-600">
                      {item.waiting}
                    </td>


                    {/* Status */}
                    <td className="px-6 py-4">

                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                          item.status
                        )}`}
                      >
                        {item.status}
                      </span>

                    </td>


                    {/* Actions */}
                    <td className="px-6 py-4">

                      <div className="flex gap-2">

                        {item.status === "Waiting" && (

                          <button
                            onClick={() => {
                              setQueue(
                                queue.map((patient) =>
                                  patient.token === item.token
                                    ? {
                                      ...patient,
                                      status:
                                        "In Consultation",
                                      waiting: "Now",
                                    }
                                    : patient
                                )
                              )
                            }}
                            className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100"
                          >
                            Call
                          </button>

                        )}


                        {item.status === "In Consultation" && (

                          <button
                            onClick={() =>
                              completePatient(item.token)
                            }
                            className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100"
                          >
                            Complete
                          </button>

                        )}


                        {item.status === "Waiting" && (

                          <button
                            onClick={() =>
                              skipPatient(item.token)
                            }
                            className="px-3 py-2 text-sm bg-orange-50 text-orange-700 rounded-lg hover:bg-orange-100"
                          >
                            Skip
                          </button>

                        )}

                      </div>

                    </td>

                  </tr>

                ))

              )}

            </tbody>

          </table>

        </div>

      </div>

    </div>
  )
}

export default Queue