import { useNavigate } from "react-router-dom"
import { useHospitals } from "../assets/context/HospitalsContext.jsx"
import { usePatient } from "../assets/context/PatientContext.jsx"

function HospitalSelection() {
  const navigate = useNavigate()

  const { getActiveHospitals } = useHospitals()
  const { setSelectedHospital } = usePatient()

  const hospitals = getActiveHospitals()

  const handleSelectHospital = (hospital) => {
    // Selected hospital ko global context me save karo
    setSelectedHospital(hospital)

    // Appointment booking par bhejo
    navigate("/appointment")
  }

  return (
    <div className="min-h-screen bg-slate-100 p-6">

      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <button
          onClick={() => navigate(-1)}
          className="mb-4 text-blue-600 hover:text-blue-800"
        >
          ← Back
        </button>

        <h1 className="text-3xl font-bold text-slate-800">
          Select Hospital
        </h1>

        <p className="text-slate-500 mt-2">
          Choose a hospital to continue with appointment booking
        </p>
      </div>

      {/* Hospital List */}
      <div className="max-w-6xl mx-auto">

        {hospitals.length === 0 ? (
          <div className="bg-white rounded-xl shadow p-10 text-center">
            <div className="text-5xl mb-4">
              🏥
            </div>

            <h2 className="text-xl font-semibold text-slate-700">
              No Active Hospital Available
            </h2>

            <p className="text-slate-500 mt-2">
              Please try again later.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

            {hospitals.map((hospital) => (
              <div
                key={hospital.id}
                className="bg-white rounded-2xl shadow-md hover:shadow-xl transition overflow-hidden border border-slate-200"
              >

                {/* Hospital Header */}
                <div className="bg-blue-600 text-white p-5">
                  <div className="flex items-center gap-3">
                    <div className="text-4xl">
                      🏥
                    </div>

                    <div>
                      <h2 className="text-xl font-bold">
                        {hospital.name}
                      </h2>

                      <p className="text-blue-100 text-sm">
                        {hospital.code}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Hospital Details */}
                <div className="p-5">

                  <div className="space-y-3 text-sm">

                    <div className="flex gap-3">
                      <span>📍</span>
                      <span className="text-slate-600">
                        {hospital.address || "Address not available"}
                      </span>
                    </div>

                    <div className="flex gap-3">
                      <span>📞</span>
                      <span className="text-slate-600">
                        {hospital.phone || "Phone not available"}
                      </span>
                    </div>

                    <div className="flex gap-3">
                      <span>✉️</span>
                      <span className="text-slate-600">
                        {hospital.email || "Email not available"}
                      </span>
                    </div>

                    <div className="flex gap-3">
                      <span>🏷️</span>
                      <span className="text-slate-600">
                        {hospital.type || "Hospital"}
                      </span>
                    </div>

                  </div>

                  {/* Hospital Stats */}
                  <div className="grid grid-cols-3 gap-2 mt-5">

                    <div className="bg-blue-50 rounded-lg p-3 text-center">
                      <p className="text-lg font-bold text-blue-600">
                        {hospital.doctors || 0}
                      </p>
                      <p className="text-xs text-slate-500">
                        Doctors
                      </p>
                    </div>

                    <div className="bg-green-50 rounded-lg p-3 text-center">
                      <p className="text-lg font-bold text-green-600">
                        {hospital.nurses || 0}
                      </p>
                      <p className="text-xs text-slate-500">
                        Nurses
                      </p>
                    </div>

                    <div className="bg-purple-50 rounded-lg p-3 text-center">
                      <p className="text-lg font-bold text-purple-600">
                        {hospital.departments || 0}
                      </p>
                      <p className="text-xs text-slate-500">
                        Departments
                      </p>
                    </div>

                  </div>

                  {/* Select Button */}
                  <button
                    onClick={() => handleSelectHospital(hospital)}
                    className="w-full mt-5 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition"
                  >
                    Select Hospital →
                  </button>

                </div>
              </div>
            ))}

          </div>
        )}

      </div>
    </div>
  )
}

export default HospitalSelection