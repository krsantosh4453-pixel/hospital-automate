import { useMemo } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"

function BedStatus() {
  const { selectedHospital } = usePatient()

  // Hospital-wise bed data
  const hospitalBeds = [
    {
      hospitalId: 1,
      totalBeds: 320,
      occupiedBeds: 274,
    },
    {
      hospitalId: 2,
      totalBeds: 200,
      occupiedBeds: 156,
    },
    {
      hospitalId: 3,
      totalBeds: 150,
      occupiedBeds: 98,
    },
  ]

  // Selected hospital ka bed data
  const bedData = useMemo(() => {
    if (!selectedHospital) {
      return null
    }

    return hospitalBeds.find(
      (hospital) =>
        hospital.hospitalId === selectedHospital.id
    )
  }, [selectedHospital])

  // Hospital select nahi hai
  if (!selectedHospital) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-800">
          Bed Occupancy
        </h2>

        <p className="text-sm text-gray-500 mt-2">
          Please select a hospital to view bed status.
        </p>
      </div>
    )
  }

  // Agar selected hospital ka data nahi mila
  if (!bedData) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-800">
          Bed Occupancy
        </h2>

        <p className="text-sm text-gray-500 mt-2">
          Bed information is not available for{" "}
          {selectedHospital.name}.
        </p>
      </div>
    )
  }

  const totalBeds = bedData.totalBeds
  const occupiedBeds = bedData.occupiedBeds
  const availableBeds = totalBeds - occupiedBeds

  const occupancyPercentage =
    totalBeds > 0
      ? Math.round(
        (occupiedBeds / totalBeds) * 100
      )
      : 0

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      {/* Header */}
      <div className="flex items-center justify-between mb-5">

        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            Bed Occupancy
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Current bed status — {selectedHospital.name}
          </p>
        </div>

        <span className="text-2xl font-bold text-blue-600">
          {occupancyPercentage}%
        </span>

      </div>


      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-3">

        <div
          className="bg-blue-600 h-3 rounded-full transition-all duration-500"
          style={{
            width: `${occupancyPercentage}%`,
          }}
        ></div>

      </div>


      {/* Bed Information */}
      <div className="grid grid-cols-2 gap-4 mt-6">

        {/* Occupied */}
        <div className="bg-gray-50 rounded-xl p-4">

          <p className="text-sm text-gray-500">
            Occupied
          </p>

          <p className="text-xl font-bold text-gray-800 mt-1">
            {occupiedBeds}
          </p>

          <p className="text-xs text-gray-400 mt-1">
            of {totalBeds} beds
          </p>

        </div>


        {/* Available */}
        <div className="bg-gray-50 rounded-xl p-4">

          <p className="text-sm text-gray-500">
            Available
          </p>

          <p className="text-xl font-bold text-green-600 mt-1">
            {availableBeds}
          </p>

          <p className="text-xs text-gray-400 mt-1">
            of {totalBeds} beds
          </p>

        </div>

      </div>

    </div>
  )
}

export default BedStatus