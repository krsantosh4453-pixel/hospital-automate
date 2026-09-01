import { useState } from "react"

function Appointments() {
  const [appointments, setAppointments] = useState([
    {
      id: "A001",
      patient: "Rahul Kumar",
      doctor: "Dr. Sharma",
      date: "01 Sep 2026",
      time: "10:30 AM",
      reason: "General Checkup",
      status: "Confirmed",
    },
    {
      id: "A002",
      patient: "Priya Singh",
      doctor: "Dr. Verma",
      date: "01 Sep 2026",
      time: "11:00 AM",
      reason: "Cardiology",
      status: "Waiting",
    },
    {
      id: "A003",
      patient: "Amit Kumar",
      doctor: "Dr. Singh",
      date: "01 Sep 2026",
      time: "11:30 AM",
      reason: "Follow-up",
      status: "Completed",
    },
  ])

  const [search, setSearch] = useState("")
  const [doctorFilter, setDoctorFilter] = useState("All Doctors")
  const [statusFilter, setStatusFilter] = useState("All Status")

  const [showForm, setShowForm] = useState(false)
  const [showView, setShowView] = useState(false)

  const [selectedAppointment, setSelectedAppointment] = useState(null)

  const [formData, setFormData] = useState({
    patient: "",
    doctor: "",
    date: "",
    time: "",
    reason: "",
  })

  // -------------------------
  // Search + Filter
  // -------------------------

  const filteredAppointments = appointments.filter((appointment) => {
    const matchesSearch =
      appointment.patient
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      appointment.id
        .toLowerCase()
        .includes(search.toLowerCase())

    const matchesDoctor =
      doctorFilter === "All Doctors" ||
      appointment.doctor === doctorFilter

    const matchesStatus =
      statusFilter === "All Status" ||
      appointment.status === statusFilter

    return (
      matchesSearch &&
      matchesDoctor &&
      matchesStatus
    )
  })

  // -------------------------
  // Form Change
  // -------------------------

  const handleChange = (e) => {
    const { name, value } = e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }

  // -------------------------
  // Add Appointment
  // -------------------------

  const handleSubmit = (e) => {
    e.preventDefault()

    const newAppointment = {
      id: `A${String(appointments.length + 1).padStart(3, "0")}`,
      patient: formData.patient,
      doctor: formData.doctor,
      date: formData.date,
      time: formData.time,
      reason: formData.reason,
      status: "Confirmed",
    }

    setAppointments([
      ...appointments,
      newAppointment,
    ])

    resetForm()
  }

  // -------------------------
  // Delete Appointment
  // -------------------------

  const handleDelete = (id) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this appointment?"
    )

    if (!confirmDelete) {
      return
    }

    const updatedAppointments =
      appointments.filter(
        (appointment) => appointment.id !== id
      )

    setAppointments(updatedAppointments)
  }

  // -------------------------
  // Cancel Appointment
  // -------------------------

  const handleCancel = (id) => {
    const updatedAppointments =
      appointments.map((appointment) =>
        appointment.id === id
          ? {
            ...appointment,
            status: "Cancelled",
          }
          : appointment
      )

    setAppointments(updatedAppointments)
  }

  // -------------------------
  // View Appointment
  // -------------------------

  const handleView = (appointment) => {
    setSelectedAppointment(appointment)
    setShowView(true)
  }

  // -------------------------
  // Edit Appointment
  // -------------------------

  const handleEdit = (appointment) => {
    setSelectedAppointment(appointment)

    setFormData({
      patient: appointment.patient,
      doctor: appointment.doctor,
      date: appointment.date,
      time: appointment.time,
      reason: appointment.reason,
    })

    setShowForm(true)
  }

  // -------------------------
  // Save Edit
  // -------------------------

  const handleUpdate = (e) => {
    e.preventDefault()

    const updatedAppointments =
      appointments.map((appointment) =>
        appointment.id === selectedAppointment.id
          ? {
            ...appointment,
            patient: formData.patient,
            doctor: formData.doctor,
            date: formData.date,
            time: formData.time,
            reason: formData.reason,
          }
          : appointment
      )

    setAppointments(updatedAppointments)

    resetForm()
  }

  // -------------------------
  // Reset
  // -------------------------

  const resetForm = () => {
    setFormData({
      patient: "",
      doctor: "",
      date: "",
      time: "",
      reason: "",
    })

    setSelectedAppointment(null)
    setShowForm(false)
  }

  return (
    <div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

        <div>

          <h1 className="text-3xl font-bold text-gray-800">
            Appointments
          </h1>

          <p className="text-gray-500 mt-1">
            Schedule and manage hospital appointments
          </p>

        </div>

        <button
          onClick={() => {
            setSelectedAppointment(null)
            setShowForm(true)
          }}
          className="bg-blue-600 text-white px-5 py-3 rounded-lg font-medium hover:bg-blue-700"
        >
          + New Appointment
        </button>

      </div>


      {/* Search & Filters */}
      <div className="bg-white rounded-xl shadow-sm p-5 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <input
            type="text"
            placeholder="Search patient or appointment ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
          />

          <select
            value={doctorFilter}
            onChange={(e) => setDoctorFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-3"
          >

            <option>All Doctors</option>
            <option>Dr. Sharma</option>
            <option>Dr. Verma</option>
            <option>Dr. Singh</option>

          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-3"
          >

            <option>All Status</option>
            <option>Confirmed</option>
            <option>Waiting</option>
            <option>Completed</option>
            <option>Cancelled</option>

          </select>

        </div>

      </div>


      {/* Appointment Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">

        <div className="p-5 border-b">

          <h2 className="text-lg font-semibold text-gray-800">
            Appointment List
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            {filteredAppointments.length} appointment(s) found
          </p>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-gray-50">

              <tr>

                <th className="text-left px-5 py-4 text-sm text-gray-600">
                  ID
                </th>

                <th className="text-left px-5 py-4 text-sm text-gray-600">
                  Patient
                </th>

                <th className="text-left px-5 py-4 text-sm text-gray-600">
                  Doctor
                </th>

                <th className="text-left px-5 py-4 text-sm text-gray-600">
                  Date
                </th>

                <th className="text-left px-5 py-4 text-sm text-gray-600">
                  Time
                </th>

                <th className="text-left px-5 py-4 text-sm text-gray-600">
                  Status
                </th>

                <th className="text-left px-5 py-4 text-sm text-gray-600">
                  Actions
                </th>

              </tr>

            </thead>


            <tbody>

              {filteredAppointments.length === 0 ? (

                <tr>

                  <td
                    colSpan="7"
                    className="text-center py-10 text-gray-500"
                  >
                    No appointments found
                  </td>

                </tr>

              ) : (

                filteredAppointments.map((appointment) => (

                  <tr
                    key={appointment.id}
                    className="border-t hover:bg-gray-50"
                  >

                    <td className="px-5 py-4 font-medium text-blue-600">
                      {appointment.id}
                    </td>

                    <td className="px-5 py-4">

                      <div className="font-medium text-gray-800">
                        {appointment.patient}
                      </div>

                      <div className="text-sm text-gray-500">
                        {appointment.reason}
                      </div>

                    </td>

                    <td className="px-5 py-4 text-gray-600">
                      {appointment.doctor}
                    </td>

                    <td className="px-5 py-4 text-gray-600">
                      {appointment.date}
                    </td>

                    <td className="px-5 py-4 text-gray-600">
                      {appointment.time}
                    </td>

                    <td className="px-5 py-4">

                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${appointment.status === "Confirmed"
                          ? "bg-blue-100 text-blue-700"
                          : appointment.status === "Waiting"
                            ? "bg-orange-100 text-orange-700"
                            : appointment.status === "Completed"
                              ? "bg-green-100 text-green-700"
                              : "bg-red-100 text-red-700"
                          }`}
                      >
                        {appointment.status}
                      </span>

                    </td>

                    <td className="px-5 py-4">

                      <div className="flex gap-2">

                        <button
                          onClick={() =>
                            handleView(appointment)
                          }
                          className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
                        >
                          View
                        </button>

                        <button
                          onClick={() =>
                            handleEdit(appointment)
                          }
                          className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                        >
                          Edit
                        </button>

                        <button
                          onClick={() =>
                            handleCancel(appointment.id)
                          }
                          disabled={
                            appointment.status ===
                            "Cancelled" ||
                            appointment.status ===
                            "Completed"
                          }
                          className="px-3 py-1 text-sm bg-orange-100 text-orange-700 rounded hover:bg-orange-200 disabled:opacity-40"
                        >
                          Cancel
                        </button>

                        <button
                          onClick={() =>
                            handleDelete(appointment.id)
                          }
                          className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
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

          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl">

            <div className="flex justify-between items-center p-6 border-b">

              <div>

                <h2 className="text-xl font-bold text-gray-800">
                  {selectedAppointment
                    ? "Edit Appointment"
                    : "New Appointment"}
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Enter appointment details
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
                selectedAppointment
                  ? handleUpdate
                  : handleSubmit
              }
              className="p-6 space-y-4"
            >

              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Patient
                </label>

                <select
                  name="patient"
                  value={formData.patient}
                  onChange={handleChange}
                  required
                  className="w-full border rounded-lg px-4 py-3"
                >

                  <option value="">
                    Select Patient
                  </option>

                  <option>Rahul Kumar</option>
                  <option>Priya Singh</option>
                  <option>Amit Kumar</option>

                </select>

              </div>


              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Doctor
                </label>

                <select
                  name="doctor"
                  value={formData.doctor}
                  onChange={handleChange}
                  required
                  className="w-full border rounded-lg px-4 py-3"
                >

                  <option value="">
                    Select Doctor
                  </option>

                  <option>Dr. Sharma</option>
                  <option>Dr. Verma</option>
                  <option>Dr. Singh</option>

                </select>

              </div>


              <div className="grid grid-cols-2 gap-4">

                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date
                  </label>

                  <input
                    type="date"
                    name="date"
                    value={formData.date}
                    onChange={handleChange}
                    required
                    className="w-full border rounded-lg px-4 py-3"
                  />

                </div>


                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Time
                  </label>

                  <input
                    type="time"
                    name="time"
                    value={formData.time}
                    onChange={handleChange}
                    required
                    className="w-full border rounded-lg px-4 py-3"
                  />

                </div>

              </div>


              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason
                </label>

                <textarea
                  name="reason"
                  value={formData.reason}
                  onChange={handleChange}
                  required
                  rows="3"
                  placeholder="Enter appointment reason"
                  className="w-full border rounded-lg px-4 py-3"
                />

              </div>


              <div className="flex justify-end gap-3 pt-3">

                <button
                  type="button"
                  onClick={resetForm}
                  className="px-5 py-3 border rounded-lg"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-5 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  {selectedAppointment
                    ? "Save Changes"
                    : "Book Appointment"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}


      {/* View Modal */}
      {showView && selectedAppointment && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">

            <div className="p-6 border-b">

              <div className="flex justify-between">

                <div>

                  <h2 className="text-xl font-bold text-gray-800">
                    Appointment Details
                  </h2>

                  <p className="text-blue-600 mt-1">
                    {selectedAppointment.id}
                  </p>

                </div>

                <button
                  onClick={() => setShowView(false)}
                  className="text-2xl text-gray-500"
                >
                  ×
                </button>

              </div>

            </div>


            <div className="p-6 space-y-4">

              <div>
                <p className="text-sm text-gray-500">
                  Patient
                </p>

                <p className="font-semibold">
                  {selectedAppointment.patient}
                </p>
              </div>


              <div>
                <p className="text-sm text-gray-500">
                  Doctor
                </p>

                <p className="font-semibold">
                  {selectedAppointment.doctor}
                </p>
              </div>


              <div className="grid grid-cols-2 gap-4">

                <div>

                  <p className="text-sm text-gray-500">
                    Date
                  </p>

                  <p className="font-semibold">
                    {selectedAppointment.date}
                  </p>

                </div>


                <div>

                  <p className="text-sm text-gray-500">
                    Time
                  </p>

                  <p className="font-semibold">
                    {selectedAppointment.time}
                  </p>

                </div>

              </div>


              <div>

                <p className="text-sm text-gray-500">
                  Reason
                </p>

                <p className="font-semibold">
                  {selectedAppointment.reason}
                </p>

              </div>


              <div>

                <p className="text-sm text-gray-500">
                  Status
                </p>

                <p className="font-semibold">
                  {selectedAppointment.status}
                </p>

              </div>

            </div>


            <div className="p-6 border-t text-right">

              <button
                onClick={() => setShowView(false)}
                className="px-5 py-2 bg-gray-100 rounded-lg"
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

export default Appointments