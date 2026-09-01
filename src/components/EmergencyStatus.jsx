function EmergencyStatus() {
  const emergencyPatients = 3
  const criticalPatients = 1
  const emergencyBeds = 4

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      <div className="mb-5">

        <h2 className="text-lg font-semibold text-gray-800">
          Emergency Status
        </h2>

        <p className="text-sm text-gray-500 mt-1">
          Current emergency department status
        </p>

      </div>


      <div className="space-y-4">

        <div className="flex justify-between items-center">
          <span className="text-gray-600">
            Emergency Patients
          </span>

          <span className="font-bold text-orange-500">
            {emergencyPatients}
          </span>
        </div>


        <div className="flex justify-between items-center">
          <span className="text-gray-600">
            Critical Patients
          </span>

          <span className="font-bold text-red-600">
            {criticalPatients}
          </span>
        </div>


        <div className="flex justify-between items-center">
          <span className="text-gray-600">
            Emergency Beds Available
          </span>

          <span className="font-bold text-green-600">
            {emergencyBeds}
          </span>
        </div>

      </div>

    </div>
  )
}

export default EmergencyStatus