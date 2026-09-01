import { useMemo, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"

function Patients() {
  const { selectedHospital } = usePatient()

  const [search, setSearch] = useState("")

  const patients = [
    {
      id: 1,
      name: "Rahul Kumar",
      age: 32,
      gender: "Male",
      phone: "9876543210",
      hospitalId: 1,
      condition: "General Checkup",
    },
    {
      id: 2,
      name: "Priya Singh",
      age: 28,
      gender: "Female",
      phone: "9876543211",
      hospitalId: 1,
      condition: "Fever",
    },
    {
      id: 3,
      name: "Amit Kumar",
      age: 45,
      gender: "Male",
      phone: "9876543212",
      hospitalId: 2,
      condition: "Diabetes",
    },
    {
      id: 4,
      name: "Neha Kumari",
      age: 36,
      gender: "Female",
      phone: "9876543213",
      hospitalId: 2,
      condition: "Follow-up",
    },
    {
      id: 5,
      name: "Ravi Sharma",
      age: 51,
      gender: "Male",
      phone: "9876543214",
      hospitalId: 3,
      condition: "Blood Pressure",
    },
  ]

  // Selected hospital ke patients
  const hospitalPatients = useMemo(() => {
    if (!selectedHospital) {
      return []
    }

    return patients.filter(
      (patient) =>
        patient.hospitalId === selectedHospital.id
    )
  }, [selectedHospital])

  // Search
  const filteredPatients = hospitalPatients.filter(
    (patient) =>
      `${patient.name} ${patient.phone} ${patient.condition}`
        .toLowerCase()
        .includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

        <div>

          <p className="text-blue-600 font-semibold text-sm">
            PATIENT MANAGEMENT
          </p>

          <h1 className="text-3xl font-bold text-gray-800 mt-1">
            Patients
          </h1>

          <p className="text-gray-500 mt-1">
            Manage patients for the selected hospital.
          </p>

        </div>


        <button className="px-5 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700">
          + Add Patient
        </button>

      </div>


      {/* Hospital */}
      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">

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

          <div className="text-orange-600">

            <p className="font-semibold">
              ⚠️ No hospital selected
            </p>

            <p className="text-sm mt-1">
              Select a hospital from the header first.
            </p>

          </div>

        )}

      </div>


      {/* Search + Stats */}
      {selectedHospital && (

        <>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

            <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">

              <p className="text-sm text-gray-500">
                Total Patients
              </p>

              <p className="text-3xl font-bold text-gray-800 mt-2">
                {hospitalPatients.length}
              </p>

            </div>


            <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">

              <p className="text-sm text-gray-500">
                Today's Patients
              </p>

              <p className="text-3xl font-bold text-blue-600 mt-2">
                {hospitalPatients.length}
              </p>

            </div>


            <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">

              <p className="text-sm text-gray-500">
                Search Results
              </p>

              <p className="text-3xl font-bold text-green-600 mt-2">
                {filteredPatients.length}
              </p>

            </div>

          </div>


          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">

            <div className="flex flex-col md:flex-row gap-4">

              <input
                type="text"
                value={search}
                onChange={(e) =>
                  setSearch(e.target.value)
                }
                placeholder="Search patient by name, phone or condition..."
                className="flex-1 border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              />

              <button
                onClick={() => setSearch("")}
                className="px-5 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200"
              >
                Clear
              </button>

            </div>

          </div>


          {/* Patient Table */}
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">

            <div className="p-5 border-b border-gray-100">

              <h2 className="text-lg font-bold text-gray-800">
                Hospital Patients
              </h2>

            </div>


            {filteredPatients.length > 0 ? (

              <div className="overflow-x-auto">

                <table className="w-full">

                  <thead className="bg-gray-50">

                    <tr>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Patient
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Age
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Gender
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Phone
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Condition
                      </th>

                      <th className="text-left px-5 py-4 text-sm font-semibold text-gray-600">
                        Action
                      </th>

                    </tr>

                  </thead>


                  <tbody>

                    {filteredPatients.map(
                      (patient) => (

                        <tr
                          key={patient.id}
                          className="border-t border-gray-100 hover:bg-gray-50"
                        >

                          <td className="px-5 py-4">

                            <div className="flex items-center gap-3">

                              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                                👤
                              </div>

                              <div>

                                <p className="font-semibold text-gray-800">
                                  {patient.name}
                                </p>

                                <p className="text-xs text-gray-500">
                                  ID: PAT-{patient.id}
                                </p>

                              </div>

                            </div>

                          </td>


                          <td className="px-5 py-4 text-sm text-gray-700">
                            {patient.age}
                          </td>


                          <td className="px-5 py-4 text-sm text-gray-700">
                            {patient.gender}
                          </td>


                          <td className="px-5 py-4 text-sm text-gray-700">
                            {patient.phone}
                          </td>


                          <td className="px-5 py-4">

                            <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                              {patient.condition}
                            </span>

                          </td>


                          <td className="px-5 py-4">

                            <button className="text-blue-600 font-medium text-sm hover:text-blue-800">
                              View
                            </button>

                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>

              </div>

            ) : (

              <div className="p-12 text-center">

                <div className="text-4xl mb-3">
                  👤
                </div>

                <h3 className="font-bold text-gray-800">
                  No patients found
                </h3>

                <p className="text-sm text-gray-500 mt-1">
                  There are no matching patients in this hospital.
                </p>

              </div>

            )}

          </div>

        </>

      )}

    </div>
  )
}

export default Patients