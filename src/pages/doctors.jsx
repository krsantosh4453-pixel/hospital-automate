import { useEffect, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { usePrescription } from "../assets/context/PrescriptionContext.jsx"
import api from "../services/api.js"


// =====================================================
// Helpers — keep the existing (flat, display-oriented) UI
// shape while talking to the Django Doctor API.
// =====================================================

// The directory UI only knows "Available" / "On Leave".
// Any other backend value is normalised so the pills and
// the statistics cards keep working.
const DOCTOR_STATUSES = [
  "Available",
  "On Leave",
]

const normaliseDoctorStatus = (status) => {
  if (!status) {
    return "Available"
  }

  const match = DOCTOR_STATUSES.find(
    (item) =>
      item.toLowerCase() ===
      String(status).toLowerCase()
  )

  return match || status
}

// Map a Django Doctor record to the flat shape the existing
// table / modals expect. `apiId` keeps the real database id
// (used for update/delete) while `id` stays the readable
// display id so nothing else in the UI changes.
const mapDoctorFromApi = (record) => ({
  apiId: record.id,
  id: `D${String(record.id).padStart(3, "0")}`,
  name: record.name || "",
  specialization: record.specialization || "",
  phone: record.phone || "",
  experience: record.experience || "",
  status: normaliseDoctorStatus(record.status),
  availability: record.availability || "",
  hospitalId: record.hospital,
})

function Doctors() {

  // ==============================
  // HOSPITAL
  // ==============================

  const { selectedHospital } = usePatient()


  // ==============================
  // PRESCRIPTION
  // ==============================

  const { addPrescription } = usePrescription()


  // ==============================
  // CREATE PRESCRIPTION
  // ==============================

  const createPrescription = async ({
    patientId,
    patientName,
    medicines,
  }) => {

    if (!selectedHospital) {
      alert("Please select a hospital first.")
      return
    }

    if (!patientId || !patientName) {
      alert("Please select a patient.")
      return
    }

    if (!medicines || medicines.length === 0) {
      alert("Please add at least one medicine.")
      return
    }

    try {
      const prescription = await addPrescription({
        hospitalId: selectedHospital.id,
        patientId,
        patientName,
        medicines,
      })
      alert(
        `Prescription saved.\n\nPrescription ID: ${prescription.id}`
      )
    } catch (err) {
      alert(`Prescription was not saved: ${err.message}`)
    }
  }


  // ==============================
  // EXISTING DOCTORS CODE
  // ==============================

  // Offline / demo seed data — kept so the page still works
  // (exactly as before) when the Django API is unreachable.
  // No demo records: the page shows only data returned by the API.
  const fallbackDoctors = []

  const [doctors, setDoctors] = useState(
    fallbackDoctors
  )

  // API / UX states.
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [offlineMode, setOfflineMode] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")
  const [reloadToken, setReloadToken] = useState(0)


  const [search, setSearch] =
    useState("")

  const [showForm, setShowForm] =
    useState(false)

  const [selectedDoctor, setSelectedDoctor] =
    useState(null)


  const [formData, setFormData] =
    useState({

      name: "",
      specialization: "",
      phone: "",
      experience: "",
      status: "Available",
      availability: "",

    })


  // ==============================
  // LOAD DOCTORS FROM DJANGO
  // ==============================

  useEffect(() => {

    if (!selectedHospital) {
      setDoctors([])
      setLoadError("")
      setOfflineMode(false)
      return
    }

    let cancelled = false

    const loadDoctors = async () => {

      setLoading(true)
      setLoadError("")

      try {

        const data = await api.doctors.list(
          selectedHospital.id
        )

        const results = Array.isArray(data)
          ? data
          : data?.results || []

        if (cancelled) {
          return
        }

        setDoctors(
          results.map(mapDoctorFromApi)
        )

        setOfflineMode(false)

      } catch (error) {

        if (cancelled) {
          return
        }

        // Fall back to the demo seed data so the
        // existing behaviour keeps working.
        setDoctors(
          fallbackDoctors.filter(
            (doctor) =>
              String(doctor.hospitalId) ===
              String(selectedHospital.id)
          )
        )

        setOfflineMode(true)
        setLoadError(
          error.message ||
          "Unable to reach the server. Showing demo doctors."
        )

      } finally {

        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadDoctors()

    return () => {
      cancelled = true
    }

  }, [selectedHospital, reloadToken])


  // Auto-dismiss the success message.

  useEffect(() => {

    if (!successMessage) {
      return
    }

    const timer = setTimeout(
      () => setSuccessMessage(""),
      3000
    )

    return () => clearTimeout(timer)

  }, [successMessage])


  // ==============================
  // HOSPITAL FILTER
  // ==============================

  const hospitalDoctors =
    selectedHospital
      ? doctors.filter(
        (doctor) =>
          doctor.hospitalId ===
          selectedHospital.id
      )
      : []


  // ==============================
  // SEARCH
  // ==============================

  const filteredDoctors =
    hospitalDoctors.filter(
      (doctor) =>
        doctor.name
          .toLowerCase()
          .includes(
            search.toLowerCase()
          ) ||

        doctor.specialization
          .toLowerCase()
          .includes(
            search.toLowerCase()
          ) ||

        doctor.id
          .toLowerCase()
          .includes(
            search.toLowerCase()
          )
    )


  // ==============================
  // FORM CHANGE
  // ==============================

  const handleChange = (e) => {

    const {
      name,
      value,
    } = e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }


  // ==============================
  // RESET
  // ==============================

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


  // ==============================
  // ADD DOCTOR
  // ==============================

  const handleSubmit = async (e) => {

    e.preventDefault()


    if (!selectedHospital) {

      alert(
        "Please select a hospital before adding a doctor."
      )

      return
    }

    if (saving) {
      return
    }


    const payload = {
      name: formData.name,
      specialization: formData.specialization,
      phone: formData.phone,
      experience: formData.experience,
      availability: formData.availability,
      status: formData.status || "Available",
      hospital: selectedHospital.id,
    }


    setSaving(true)

    try {

      const created =
        await api.doctors.create(payload)

      const mapped =
        mapDoctorFromApi(created)

      setDoctors([
        ...doctors,
        mapped,
      ])

      setSuccessMessage(
        "Doctor saved successfully."
      )

      resetForm()

    } catch (error) {

      // Keep the previous behaviour: save locally so nothing
      // the user typed is lost, but be honest about it.
      const newDoctor = {

        id:
          `D${String(
            doctors.length + 1
          ).padStart(3, "0")}`,

        ...formData,

        hospitalId:
          selectedHospital.id,

      }

      setDoctors([
        ...doctors,
        newDoctor,
      ])

      setOfflineMode(true)
      setSuccessMessage(
        "Saved locally. The server could not be reached."
      )

      resetForm()

    } finally {

      setSaving(false)
    }
  }


  // ==============================
  // EDIT
  // ==============================

  const handleEdit = (doctor) => {

    setSelectedDoctor(
      doctor
    )


    setFormData({

      name:
        doctor.name,

      specialization:
        doctor.specialization,

      phone:
        doctor.phone,

      experience:
        doctor.experience,

      status:
        doctor.status,

      availability:
        doctor.availability,

    })


    setShowForm(true)
  }


  // ==============================
  // UPDATE
  // ==============================

  const handleUpdate = async (e) => {

    e.preventDefault()


    if (!selectedDoctor || saving) {
      return
    }


    const payload = {
      name: formData.name,
      specialization: formData.specialization,
      phone: formData.phone,
      experience: formData.experience,
      availability: formData.availability,
      status: formData.status || "Available",
      hospital:
        selectedHospital?.id ??
        selectedDoctor.hospitalId,
    }


    setSaving(true)

    try {

      // Only rows loaded from Django carry `apiId`. Demo /
      // offline rows are updated locally, exactly as before.
      if (selectedDoctor.apiId) {

        await api.doctors.update(
          selectedDoctor.apiId,
          payload
        )

        setSuccessMessage(
          "Doctor updated successfully."
        )

      }

      const updatedDoctors =
        doctors.map(
          (doctor) =>
            String(doctor.id) ===
              String(selectedDoctor.id)

              ? {
                ...doctor,
                ...formData,
              }

              : doctor
        )

      setDoctors(
        updatedDoctors
      )

      resetForm()

    } catch (error) {

      const updatedDoctors =
        doctors.map(
          (doctor) =>
            String(doctor.id) ===
              String(selectedDoctor.id)

              ? {
                ...doctor,
                ...formData,
              }

              : doctor
        )

      setDoctors(
        updatedDoctors
      )

      setOfflineMode(true)
      setSuccessMessage(
        "Saved locally. The server could not be reached."
      )

      resetForm()

    } finally {

      setSaving(false)
    }
  }


  // ==============================
  // DELETE
  // ==============================

  const handleDelete = async (id) => {

    const confirmed =
      window.confirm(
        "Are you sure you want to delete this doctor?"
      )


    if (!confirmed) {
      return
    }


    const target =
      doctors.find(
        (doctor) =>
          String(doctor.id) === String(id)
      )


    try {

      // Only rows loaded from Django carry `apiId`.
      if (target?.apiId) {

        await api.doctors.delete(
          target.apiId
        )
      }

      setDoctors(
        doctors.filter(
          (doctor) =>
            String(doctor.id) !== String(id)
        )
      )

      setSuccessMessage(
        "Doctor deleted."
      )

    } catch (error) {

      setOfflineMode(true)
      setSuccessMessage(
        "The server could not be reached. Please try again."
      )
    }
  }


  // ==============================
  // VIEW
  // ==============================

  const handleView = (
    doctor
  ) => {

    setSelectedDoctor(
      doctor
    )
  }


  // ==============================
  // STATISTICS
  // ==============================

  const availableDoctors =
    hospitalDoctors.filter(
      (doctor) =>
        doctor.status ===
        "Available"
    ).length


  const onLeaveDoctors =
    hospitalDoctors.filter(
      (doctor) =>
        doctor.status ===
        "On Leave"
    ).length


  return (

    <div>


      {/* ==============================
          HEADER
      ============================== */}

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

        <div>

          <p className="text-blue-600 font-semibold text-sm">
            DOCTOR MANAGEMENT
          </p>

          <h1 className="text-3xl font-bold text-gray-800">
            Doctors
          </h1>

          <p className="text-gray-500 mt-1">
            Manage doctors, specializations and availability
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


      {/* ==============================
          STATUS / ERROR BANNERS
      ============================== */}

      {successMessage && (

        <div className="mb-6 rounded-2xl border border-green-200 bg-green-50 p-4">

          <p className="text-sm font-medium text-green-700">
            ✅ {successMessage}
          </p>

        </div>

      )}

      {loadError && (

        <div className="mb-6 rounded-2xl border border-orange-200 bg-orange-50 p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">

          <p className="text-sm font-medium text-orange-700">
            ⚠️ {loadError}
            {offlineMode ? " (offline mode)" : ""}
          </p>

          <button
            onClick={() =>
              setReloadToken(
                (token) => token + 1
              )
            }
            className="self-start px-4 py-2 text-sm bg-orange-600 text-white rounded-lg"
          >
            Retry
          </button>

        </div>

      )}


      {/* ==============================
          CURRENT HOSPITAL
      ============================== */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        {selectedHospital ? (

          <div className="flex items-center gap-4">

            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-2xl">
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
              Select a hospital from the header to view doctors.
            </p>

          </div>

        )}

      </div>


      {/* ==============================
          DOCTORS CONTENT
      ============================== */}

      {selectedHospital && (

        <>

          {/* STATISTICS */}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">

            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

              <p className="text-sm text-gray-500">
                Total Doctors
              </p>

              <h2 className="text-3xl font-bold text-gray-800 mt-3">
                {loading
                  ? "…"
                  : hospitalDoctors.length}
              </h2>

            </div>


            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

              <p className="text-sm text-gray-500">
                Available Doctors
              </p>

              <h2 className="text-3xl font-bold text-green-600 mt-3">
                {availableDoctors}
              </h2>

            </div>


            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

              <p className="text-sm text-gray-500">
                On Leave
              </p>

              <h2 className="text-3xl font-bold text-orange-500 mt-3">
                {onLeaveDoctors}
              </h2>
            </div>

          </div>
          {/* SEARCH */}

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

            <input

              type="text"

              value={search}

              onChange={(e) =>
                setSearch(
                  e.target.value
                )
              }

              placeholder="Search by doctor name, specialization or ID..."

              className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"

            />

          </div>


          {loading && (

            <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-6">

              <p className="text-sm text-gray-500">
                Loading doctors…
              </p>

            </div>

          )}


          {/* DOCTOR TABLE */}

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

                    <th className="text-left px-6 py-4">
                      ID
                    </th>

                    <th className="text-left px-6 py-4">
                      Doctor
                    </th>

                    <th className="text-left px-6 py-4">
                      Specialization
                    </th>

                    <th className="text-left px-6 py-4">
                      Phone
                    </th>

                    <th className="text-left px-6 py-4">
                      Experience
                    </th>

                    <th className="text-left px-6 py-4">
                      Status
                    </th>

                    <th className="text-left px-6 py-4">
                      Actions
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {filteredDoctors.map(
                    (doctor) => (

                      <tr
                        key={doctor.id}
                        className="border-t hover:bg-gray-50"
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


                        <td className="px-6 py-4">
                          {doctor.specialization}
                        </td>


                        <td className="px-6 py-4">
                          {doctor.phone}
                        </td>


                        <td className="px-6 py-4">
                          {doctor.experience}
                        </td>


                        <td className="px-6 py-4">

                          <span
                            className={`px-3 py-1 rounded-full text-xs ${doctor.status ===
                              "Available"
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
                              onClick={() =>
                                handleView(
                                  doctor
                                )
                              }
                              className="px-3 py-2 text-sm text-blue-600 bg-blue-50 rounded-lg"
                            >
                              View
                            </button>


                            <button
                              onClick={() =>
                                handleEdit(
                                  doctor
                                )
                              }
                              className="px-3 py-2 text-sm text-green-600 bg-green-50 rounded-lg"
                            >
                              Edit
                            </button>


                            <button
                              onClick={() =>
                                handleDelete(
                                  doctor.id
                                )
                              }
                              className="px-3 py-2 text-sm text-red-600 bg-red-50 rounded-lg"
                            >
                              Delete
                            </button>

                          </div>

                        </td>

                      </tr>

                    )
                  )}


                  {!loading &&
                    filteredDoctors.length === 0 && (

                      <tr>

                        <td
                          colSpan="7"
                          className="px-6 py-10 text-center text-gray-500"
                        >

                          {hospitalDoctors.length === 0
                            ? "No doctors yet. Use “Add Doctor” to create one."
                            : "No doctors match your search."}

                        </td>

                      </tr>

                    )}

                </tbody>

              </table>

            </div>

          </div>


          {/* ==============================
              PRESCRIPTION SECTION
          ============================== */}

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mt-6">

            <div>

              <p className="text-blue-600 font-semibold text-sm">
                AI ASSISTED PRESCRIPTION
              </p>

              <h2 className="text-xl font-bold text-gray-800 mt-1">
                Doctor Prescription
              </h2>

              <p className="text-sm text-gray-500 mt-1">
                Confirm the patient&apos;s medicines after doctor review.
              </p>

            </div>


            <div className="mt-5 p-4 bg-blue-50 rounded-xl">

              <p className="text-sm text-gray-600">
                Current Hospital
              </p>

              <p className="font-bold text-gray-800">
                {selectedHospital.name}
              </p>

            </div>


            <button

              onClick={() =>
                createPrescription({

                  patientId: "P001",

                  patientName:
                    "Rahul Kumar",

                  medicines: [

                    {
                      name:
                        "Medicine A",

                      dosage:
                        "500 mg",

                      frequency:
                        "1-0-1",

                      duration:
                        "5 days",

                      quantity:
                        10,
                    },

                  ],

                })
              }

              className="mt-5 bg-blue-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-blue-700"

            >

              ✓ Confirm Prescription

            </button>

          </div>


          {/* ==============================
              ADD / EDIT MODAL
          ============================== */}

          {showForm && (

            <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

              <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl">

                <div className="flex justify-between items-center p-6 border-b">

                  <h2 className="text-xl font-bold">
                    {selectedDoctor
                      ? "Edit Doctor"
                      : "Add New Doctor"}
                  </h2>

                  <button
                    onClick={
                      resetForm
                    }
                    className="text-2xl"
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

                  <input
                    type="text"
                    name="name"
                    value={
                      formData.name
                    }
                    onChange={
                      handleChange
                    }
                    placeholder="Doctor Name"
                    required
                    className="w-full border rounded-xl px-4 py-3"
                  />


                  <input
                    type="text"
                    name="specialization"
                    value={
                      formData.specialization
                    }
                    onChange={
                      handleChange
                    }
                    placeholder="Specialization"
                    required
                    className="w-full border rounded-xl px-4 py-3"
                  />
                  <input
                    type="tel"
                    name="phone"
                    value={
                      formData.phone
                    }
                    onChange={
                      handleChange
                    }
                    placeholder="Phone"
                    required
                    className="w-full border rounded-xl px-4 py-3"
                  />
                  <input
                    type="text"
                    name="experience"
                    value={
                      formData.experience
                    }
                    onChange={
                      handleChange
                    }
                    placeholder="Experience"
                    required
                    className="w-full border rounded-xl px-4 py-3"
                  />
                  <select
                    name="status"
                    value={
                      formData.status
                    }
                    onChange={
                      handleChange
                    }
                    className="w-full border rounded-xl px-4 py-3"
                  >
                    <option>
                      Available
                    </option>

                    <option>
                      On Leave
                    </option>
                  </select>
                  <input
                    type="text"
                    name="availability"
                    value={
                      formData.availability
                    }
                    onChange={
                      handleChange
                    }
                    placeholder="Availability"
                    required
                    className="w-full border rounded-xl px-4 py-3"
                  />
                  <div className="flex justify-end gap-3 pt-4">

                    <button
                      type="button"
                      onClick={
                        resetForm
                      }
                      className="px-5 py-3 border rounded-xl"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={saving}
                      className="px-5 py-3 bg-blue-600 text-white rounded-xl disabled:opacity-60"
                    >
                      {saving
                        ? "Saving…"
                        : selectedDoctor
                          ? "Save Changes"
                          : "Save Doctor"}
                    </button>
                  </div>
                </form>

              </div>

            </div>

          )}
          {/* ==============================
              VIEW DOCTOR
          ============================== */}

          {selectedDoctor &&
            !showForm && (

              <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

                <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">

                  <div className="p-6 border-b flex justify-between">

                    <h2 className="text-xl font-bold">
                      Doctor Details
                    </h2>

                    <button
                      onClick={() =>
                        setSelectedDoctor(
                          null
                        )
                      }
                      className="text-2xl"
                    >
                      ×
                    </button>

                  </div>


                  <div className="p-6 space-y-4">

                    <div className="text-4xl">
                      👨‍⚕️
                    </div>

                    <h3 className="text-xl font-bold">
                      {selectedDoctor.name}
                    </h3>

                    <p className="text-gray-500">
                      {selectedDoctor.specialization}
                    </p>

                    <p>
                      📞 {selectedDoctor.phone}
                    </p>

                    <p>
                      💼 {selectedDoctor.experience}
                    </p>

                    <p>
                      🕒 {selectedDoctor.availability}
                    </p>

                  </div>


                  <div className="p-6 border-t">

                    <button
                      onClick={() =>
                        setSelectedDoctor(
                          null
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

export default Doctors