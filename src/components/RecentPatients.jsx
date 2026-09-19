import { useMemo } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"

function RecentPatients() {
  const { patients, selectedHospital } = usePatient()

  // Selected hospital ke patients
  const hospitalPatients = useMemo(() => {
    if (!selectedHospital) {
      return []
    }

    return patients.filter(
      (patient) =>
        patient.hospitalId === selectedHospital.id
    )
  }, [patients, selectedHospital])

  // Sirf recently registered patients
  const recentPatients = useMemo(() => {
    return hospitalPatients.slice(0, 5)
  }, [hospitalPatients])

  // Hospital select nahi hai
  if (!selectedHospital) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100">

        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-800">
            Recent Patients
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Please select a hospital to view recent patients.
          </p>
        </div>

      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100">

      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b">

        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            Recent Patients
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Recently registered patients —{" "}
            {selectedHospital.name}
          </p>
        </div>

        <button className="text-sm text-blue-600 font-medium hover:text-blue-700">
          View All
        </button>

      </div>


      {/* Patient List */}
      <div className="divide-y">

        {recentPatients.length > 0 ? (
          recentPatients.map((patient) => (
            <div
              key={patient.id}
              className="p-5 flex items-center justify-between"
            >

              {/* Patient */}
              <div className="flex items-center gap-4">

                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                  👤
                </div>

                <div>
                  <p className="font-medium text-gray-800">
                    {patient.name}
                  </p>

                  <p className="text-sm text-gray-500">
                    {patient.id}
                  </p>
                </div>

              </div>


              {/* Department */}
              <span className="text-sm text-gray-600">
                {patient.department || "General"}
              </span>

            </div>
          ))
        ) : (
          <div className="p-6 text-center">

            <p className="text-gray-500">
              No patients found
            </p>

            <p className="text-sm text-gray-400 mt-1">
              No patients are registered in{" "}
              {selectedHospital.name}.
            </p>

          </div>
        )}

      </div>

    </div>
  )
}

export default RecentPatients