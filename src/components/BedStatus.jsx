function BedStatus() {
  const totalBeds = 320
  const occupiedBeds = 274
  const availableBeds = totalBeds - occupiedBeds

  const occupancyPercentage = Math.round(
    (occupiedBeds / totalBeds) * 100
  )

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

      <div className="flex items-center justify-between mb-5">

        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            Bed Occupancy
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Current hospital bed status
          </p>
        </div>

        <span className="text-2xl font-bold text-blue-600">
          {occupancyPercentage}%
        </span>

      </div>


      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-3">

        <div
          className="bg-blue-600 h-3 rounded-full"
          style={{ width: `${occupancyPercentage}%` }}
        ></div>

      </div>


      {/* Bed Information */}
      <div className="grid grid-cols-2 gap-4 mt-6">

        <div className="bg-gray-50 rounded-xl p-4">
          <p className="text-sm text-gray-500">
            Occupied
          </p>

          <p className="text-xl font-bold text-gray-800 mt-1">
            {occupiedBeds}
          </p>
        </div>


        <div className="bg-gray-50 rounded-xl p-4">
          <p className="text-sm text-gray-500">
            Available
          </p>

          <p className="text-xl font-bold text-green-600 mt-1">
            {availableBeds}
          </p>
        </div>

      </div>

    </div>
  )
}

export default BedStatus