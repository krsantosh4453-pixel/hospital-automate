function RecentPatients() {
  const patients = [
    {
      id: "P001",
      name: "Rahul Kumar",
      department: "General Medicine",
    },
    {
      id: "P002",
      name: "Patient B",
      department: "Cardiology",
    },
    {
      id: "P003",
      name: "Patient C",
      department: "Orthopedics",
    },
  ]

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100">

      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b">

        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            Recent Patients
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Recently registered patients
          </p>
        </div>

        <button className="text-sm text-blue-600 font-medium hover:text-blue-700">
          View All
        </button>

      </div>


      {/* Patient List */}
      <div className="divide-y">

        {patients.map((patient) => (
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
              {patient.department}
            </span>

          </div>
        ))}

      </div>

    </div>
  )
}

export default RecentPatients