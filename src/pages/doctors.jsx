import { useState } from "react"

function Doctors() {
  const [doctors, setDoctors] = useState([
    {
      id: "D001",
      name: "Dr. Sharma",
      specialization: "Cardiology",
      phone: "9876500001",
      experience: "12 Years",
      status: "Available",
      availability: "Mon - Sat, 10 AM - 2 PM",
    },
    {
      id: "D002",
      name: "Dr. Verma",
      specialization: "General Medicine",
      phone: "9876500002",
      experience: "8 Years",
      status: "Available",
      availability: "Mon - Fri, 9 AM - 1 PM",
    },
    {
      id: "D003",
      name: "Dr. Singh",
      specialization: "Neurology",
      phone: "9876500003",
      experience: "10 Years",
      status: "On Leave",
      availability: "Currently unavailable",
    },
  ])

  const [search, setSearch] = useState("")
  const [showForm, setShowForm] = useState(false)
  const [selectedDoctor, setSelectedDoctor] = useState(null)

  const [formData, setFormData] = useState({
    name: "",
    specialization: "",
    phone: "",
    experience: "",
    status: "Available",
    availability: "",
  })

  const filteredDoctors = doctors.filter((doctor) =>
    doctor.name.toLowerCase().includes(search.toLowerCase()) ||
    doctor.specialization.toLowerCase().includes(search.toLowerCase()) ||
    doctor.id.toLowerCase().includes(search.toLowerCase())
  )

  const handleChange = (e) => {
    const { name, value } = e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }

  const resetForm = () => {
    setFormData({
      name: "",
      specialization: "",
      phone: "",
      experience: "",
      status: "Available",
      availability: "",
    })

    setSelectedDoctor(null)
    setShowForm(false)
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    const newDoctor = {
      id: `D${String(doctors.length + 1).padStart(3, "0")}`,
      ...formData,
    }

    setDoctors([...doctors, newDoctor])

    resetForm()
  }

  const handleEdit = (doctor) => {
    setSelectedDoctor(doctor)

    setFormData({
      name: doctor.name,
      specialization: doctor.specialization,
      phone: doctor.phone,
      experience: doctor.experience,
      status: doctor.status,
      availability: doctor.availability,
    })

    setShowForm(true)
  }

  const handleUpdate = (e) => {
    e.preventDefault()

    const updatedDoctors = doctors.map((doctor) =>
      doctor.id === selectedDoctor.id
        ? {
          ...doctor,
          ...formData,
        }
        : doctor
    )

    setDoctors(updatedDoctors)

    resetForm()
  }

  const handleDelete = (id) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this doctor?"
    )

    if (!confirmed) {
      return
    }

    setDoctors(
      doctors.filter((doctor) => doctor.id !== id)
    )
  }

  const handleView = (doctor) => {
    setSelectedDoctor(doctor)
  }

  const availableDoctors = doctors.filter(
    (doctor) => doctor.status === "Available"
  ).length

  const onLeaveDoctors = doctors.filter(
    (doctor) => doctor.status === "On Leave"
  ).length

  return (
    <div>

      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            Doctors
          </h1>

          <p className="text-gray-500 mt-1">
            Manage doctors, specializations and availability
          </p>
        </div>

        <button
          onClick={() => {
            setSelectedDoctor(null)
            setFormData({
              name: "",
              specialization: "",
              phone: "",
              experience: "",
              status: "Available",
              availability: "",
            })
            setShowForm(true)
          }}
          className="bg-blue-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-blue-700 transition"
        >
          + Add Doctor
        </button>

      </div>


      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Total Doctors
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-gray-800">
              {doctors.length}
            </h2>

            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-2xl">
              👨‍⚕️
            </div>

          </div>

        </div>


        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Available Doctors
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-green-600">
              {availableDoctors}
            </h2>

            <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center text-2xl">
              ✓
            </div>

          </div>

        </div>


        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            On Leave
          </p>

          <div className="flex items-center justify-between mt-3">

            <h2 className="text-3xl font-bold text-orange-500">
              {onLeaveDoctors}
            </h2>

            <div className="w-12 h-12 rounded-xl bg-orange-100 flex items-center justify-center text-2xl">
              🕒
            </div>

          </div>

        </div>

      </div>


      {/* Search */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by doctor name, specialization or ID..."
          className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
        />

      </div>


      {/* Doctor Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

        <div className="p-6 border-b">

          <h2 className="text-xl font-bold text-gray-800">
            Doctor Directory
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            {filteredDoctors.length} doctor(s) found
          </p>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-gray-50">

              <tr>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  ID
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Doctor
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Specialization
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Phone
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Experience
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

              {filteredDoctors.length === 0 ? (

                <tr>

                  <td
                    colSpan="7"
                    className="text-center py-12 text-gray-500"
                  >
                    No doctors found
                  </td>

                </tr>

              ) : (

                filteredDoctors.map((doctor) => (

                  <tr
                    key={doctor.id}
                    className="border-t hover:bg-gray-50 transition"
                  >

                    <td className="px-6 py-4 font-semibold text-blue-600">
                      {doctor.id}
                    </td>


                    <td className="px-6 py-4">

                      <div className="flex items-center gap-3">

                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                          👨‍⚕️
                        </div>

                        <div>
                          <p className="font-semibold text-gray-800">
                            {doctor.name}
                          </p>

                          <p className="text-xs text-gray-500">
                            Hospital Staff
                          </p>
                        </div>

                      </div>

                    </td>


                    <td className="px-6 py-4 text-gray-600">
                      {doctor.specialization}
                    </td>


                    <td className="px-6 py-4 text-gray-600">
                      {doctor.phone}
                    </td>


                    <td className="px-6 py-4 text-gray-600">
                      {doctor.experience}
                    </td>


                    <td className="px-6 py-4">

                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${doctor.status === "Available"
                            ? "bg-green-100 text-green-700"
                            : "bg-orange-100 text-orange-700"
                          }`}
                      >
                        {doctor.status}
                      </span>

                    </td>


                    <td className="px-6 py-4">

                      <div className="flex gap-2">

                        <button
                          onClick={() => handleView(doctor)}
                          className="px-3 py-2 text-sm text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                        >
                          View
                        </button>

                        <button
                          onClick={() => handleEdit(doctor)}
                          className="px-3 py-2 text-sm text-green-600 bg-green-50 rounded-lg hover:bg-green-100"
                        >
                          Edit
                        </button>

                        <button
                          onClick={() => handleDelete(doctor.id)}
                          className="px-3 py-2 text-sm text-red-600 bg-red-50 rounded-lg hover:bg-red-100"
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

            <div className="flex items-center justify-between p-6 border-b">

              <div>

                <h2 className="text-xl font-bold text-gray-800">
                  {selectedDoctor
                    ? "Edit Doctor"
                    : "Add New Doctor"}
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  {selectedDoctor
                    ? "Update doctor information"
                    : "Enter doctor information"}
                </p>

              </div>

              <button
                onClick={resetForm}
                className="text-2xl text-gray-500 hover:text-gray-800"
              >
                ×
              </button>

            </div>


            <form
              onSubmit={
                selectedDoctor
                  ? handleUpdate
                  : handleSubmit
              }
              className="p-6 space-y-4"
            >

              {/* Doctor Name */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Doctor Name
                </label>

                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  placeholder="Dr. John Doe"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>


              {/* Specialization */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Specialization
                </label>

                <input
                  type="text"
                  name="specialization"
                  value={formData.specialization}
                  onChange={handleChange}
                  required
                  placeholder="Cardiology"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>


              {/* Phone */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Phone Number
                </label>

                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  required
                  placeholder="9876543210"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>


              {/* Experience */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Experience
                </label>

                <input
                  type="text"
                  name="experience"
                  value={formData.experience}
                  onChange={handleChange}
                  required
                  placeholder="5 Years"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>


              {/* Status */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>

                <select
                  name="status"
                  value={formData.status}
                  onChange={handleChange}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3"
                >

                  <option>Available</option>
                  <option>On Leave</option>

                </select>

              </div>


              {/* Availability */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Availability
                </label>

                <input
                  type="text"
                  name="availability"
                  value={formData.availability}
                  onChange={handleChange}
                  required
                  placeholder="Mon - Sat, 10 AM - 2 PM"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />

              </div>


              {/* Buttons */}
              <div className="flex justify-end gap-3 pt-4">

                <button
                  type="button"
                  onClick={resetForm}
                  className="px-5 py-3 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700"
                >
                  {selectedDoctor
                    ? "Save Changes"
                    : "Save Doctor"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}


      {/* View Doctor Modal */}
      {selectedDoctor && !showForm && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">

            <div className="flex items-center justify-between p-6 border-b">

              <div>

                <h2 className="text-xl font-bold text-gray-800">
                  Doctor Details
                </h2>

                <p className="text-sm text-blue-600 mt-1">
                  {selectedDoctor.id}
                </p>

              </div>

              <button
                onClick={() => setSelectedDoctor(null)}
                className="text-2xl text-gray-500 hover:text-gray-800"
              >
                ×
              </button>

            </div>


            <div className="p-6 space-y-5">

              <div className="flex items-center gap-4">

                <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center text-3xl">
                  👨‍⚕️
                </div>

                <div>

                  <h3 className="text-xl font-bold text-gray-800">
                    {selectedDoctor.name}
                  </h3>

                  <p className="text-gray-500">
                    {selectedDoctor.specialization}
                  </p>

                </div>

              </div>


              <div className="grid grid-cols-2 gap-4">

                <div className="bg-gray-50 rounded-xl p-4">

                  <p className="text-xs text-gray-500">
                    Phone
                  </p>

                  <p className="font-semibold text-gray-800 mt-1">
                    {selectedDoctor.phone}
                  </p>

                </div>


                <div className="bg-gray-50 rounded-xl p-4">

                  <p className="text-xs text-gray-500">
                    Experience
                  </p>

                  <p className="font-semibold text-gray-800 mt-1">
                    {selectedDoctor.experience}
                  </p>

                </div>

              </div>


              <div>

                <p className="text-sm text-gray-500">
                  Availability
                </p>

                <p className="font-semibold text-gray-800 mt-1">
                  {selectedDoctor.availability}
                </p>

              </div>


              <div>

                <p className="text-sm text-gray-500">
                  Current Status
                </p>

                <span
                  className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${selectedDoctor.status === "Available"
                      ? "bg-green-100 text-green-700"
                      : "bg-orange-100 text-orange-700"
                    }`}
                >
                  {selectedDoctor.status}
                </span>

              </div>

            </div>


            <div className="p-6 border-t flex justify-end">

              <button
                onClick={() => setSelectedDoctor(null)}
                className="px-5 py-3 bg-gray-800 text-white rounded-xl hover:bg-gray-900"
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

export default Doctors