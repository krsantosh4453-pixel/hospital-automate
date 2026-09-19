import { useMemo } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"

function EmergencyStatus() {
  const { selectedHospital } = usePatient()

  // Hospital-wise emergency data
  const hospitalEmergencyData = [
    {
      hospitalId: 1,
      emergencyPatients: 3,
      criticalPatients: 1,
      emergencyBeds: 4,
    },
    {
      hospitalId: 2,
      emergencyPatients: 5,
      criticalPatients: 2,
      emergencyBeds: 2,
    },
    {
      hospitalId: 3,
      emergencyPatients: 2,
      criticalPatients: 0,
      emergencyBeds: 6,
    },
  ]

  // Selected hospital ka emergency data
  const emergencyData = useMemo(() => {
    if (!selectedHospital) {
      return null
    }

    return hospitalEmergencyData.find(
      (hospital) =>
        hospital.hospitalId === selectedHospital.id
    )
  }, [selectedHospital])

  // Hospital select nahi hai
  if (!selectedHospital) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

        <h2 className="text-lg font-semibold text-gray-800">
          Emergency Status
        </h2>

        <p className="text-sm text-gray-500 mt-2">
          Please select a hospital to view emergency status.
        </p>

      </div>
    )
  }

  // Data available nahi hai
  if (!emergencyData) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

        <h2 className="text-lg font-semibold text-gray-800">
          Emergency Status
        </h2>

        <p className="text-sm text-gray-500 mt-2">
          Emergency information is not available for{" "}
          {selectedHospital.name}.
        </p>

      </div>
    )
  }

  const {
    emergencyPatients,
    criticalPatients,
    emergencyBeds,
  } = emergencyData

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      {/* Header */}
      <div className="mb-5">

        <h2 className="text-lg font-semibold text-gray-800">
          Emergency Status
        </h2>

        <p className="text-sm text-gray-500 mt-1">
          Current emergency department status —{" "}
          {selectedHospital.name}
        </p>

      </div>


      {/* Emergency Information */}
      <div className="space-y-4">

        {/* Emergency Patients */}
        <div className="flex justify-between items-center">

          <span className="text-gray-600">
            Emergency Patients
          </span>

          <span className="font-bold text-orange-500">
            {emergencyPatients}
          </span>

        </div>


        {/* Critical Patients */}
        <div className="flex justify-between items-center">

          <span className="text-gray-600">
            Critical Patients
          </span>

          <span className="font-bold text-red-600">
            {criticalPatients}
          </span>

        </div>


        {/* Emergency Beds */}
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