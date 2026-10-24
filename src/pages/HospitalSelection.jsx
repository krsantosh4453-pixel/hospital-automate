import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useHospitals } from "../assets/context/HospitalsContext.jsx"

function HospitalSelection() {
  const navigate = useNavigate()
  const { selectHospital } = usePatient()

  const [search, setSearch] = useState("")
  const [selectedHospital, setSelectedHospital] = useState(null)
  const [userLocation, setUserLocation] = useState(null)
  const [locationLoading, setLocationLoading] = useState(false)
  const [locationError, setLocationError] = useState("")

  // Real hospitals from the API (public directory for patients). Ratings
  // and doctor counts are not invented; distance needs real coordinates.
  const { hospitals: contextHospitals, loading: hospitalsLoading, error: hospitalsError } = useHospitals()
  const hospitals = contextHospitals.filter((hospital) => hospital.status === "Active")

  // Calculate distance between patient and hospital
  const calculateDistance = (
    lat1,
    lon1,
    lat2,
    lon2
  ) => {
    const R = 6371

    const dLat =
      ((lat2 - lat1) * Math.PI) / 180

    const dLon =
      ((lon2 - lon1) * Math.PI) / 180

    const a =
      Math.sin(dLat / 2) *
      Math.sin(dLat / 2) +
      Math.cos(
        (lat1 * Math.PI) / 180
      ) *
      Math.cos(
        (lat2 * Math.PI) / 180
      ) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2)

    const c =
      2 *
      Math.atan2(
        Math.sqrt(a),
        Math.sqrt(1 - a)
      )

    return R * c
  }

  // Get current browser location
  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setLocationError(
        "Location is not supported by this browser."
      )
      return
    }

    setLocationLoading(true)
    setLocationError("")

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const location = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        }

        setUserLocation(location)
        setLocationLoading(false)
      },
      () => {
        setLocationLoading(false)

        setLocationError(
          "Location permission was denied. You can search hospitals manually."
        )
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    )
  }

  // Add distance when location is available
  const hospitalsWithDistance =
    hospitals.map((hospital) => {

      if (!userLocation || hospital.latitude == null || hospital.longitude == null) {
        return {
          ...hospital,
          distance: null,
        }
      }

      const distance =
        calculateDistance(
          userLocation.latitude,
          userLocation.longitude,
          hospital.latitude,
          hospital.longitude
        )

      return {
        ...hospital,
        distance,
      }
    })

  // Sort nearest hospital first
  const sortedHospitals =
    [...hospitalsWithDistance].sort(
      (a, b) => {

        if (
          a.distance === null ||
          b.distance === null
        ) {
          return 0
        }

        return a.distance - b.distance
      }
    )

  // Search hospital
  const filteredHospitals =
    sortedHospitals.filter(
      (hospital) =>
        `${hospital.name} ${hospital.address}`
          .toLowerCase()
          .includes(search.toLowerCase())
    )

  // Select hospital
  const handleSelectHospital = (
    hospital
  ) => {
    setSelectedHospital(hospital)
  }

  // Continue
  const handleContinue = () => {

    if (!selectedHospital) {
      alert("Please select a hospital.")
      return
    }

    selectHospital(selectedHospital)

    navigate("/appointments")
  }

  // Open map
  const handleOpenMap = (hospital) => {

    const mapUrl =
      `https://www.google.com/maps/search/?api=1&query=${hospital.latitude},${hospital.longitude}`

    window.open(
      mapUrl,
      "_blank",
      "noopener,noreferrer"
    )
  }

  // Get directions
  const handleDirections = (
    hospital
  ) => {

    const destination =
      `${hospital.latitude},${hospital.longitude}`

    let directionsUrl

    if (userLocation) {

      directionsUrl =
        `https://www.google.com/maps/dir/?api=1&origin=${userLocation.latitude},${userLocation.longitude}&destination=${destination}`

    } else {

      directionsUrl =
        `https://www.google.com/maps/dir/?api=1&destination=${destination}`
    }

    window.open(
      directionsUrl,
      "_blank",
      "noopener,noreferrer"
    )
  }

  // Call hospital
  const handleCall = (phone) => {
    window.location.href =
      `tel:${phone}`
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">

      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div className="mb-8">

          <p className="text-blue-600 font-semibold text-sm">
            PATIENT PORTAL
          </p>

          <h1 className="text-3xl font-bold text-gray-800 mt-2">
            Select Hospital
          </h1>

          <p className="text-gray-500 mt-2">
            Find and select a nearby hospital for your appointment.
          </p>

        </div>


        {/* Location + Search */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 mb-6">

          <div className="flex flex-col lg:flex-row gap-4">

            {/* Search */}
            <div className="flex-1">

              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Hospital
              </label>

              <input
                type="text"
                value={search}
                onChange={(e) =>
                  setSearch(e.target.value)
                }
                placeholder="Search hospital or location..."
                className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              />

            </div>


            {/* Location Button */}
            <div className="flex items-end">

              <button
                onClick={handleGetLocation}
                disabled={locationLoading}
                className="w-full lg:w-auto px-5 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-60"
              >
                {locationLoading
                  ? "Getting Location..."
                  : "📍 Use My Location"}
              </button>

            </div>

          </div>


          {/* Location status */}
          {userLocation && (

            <div className="mt-4 bg-green-50 border border-green-100 rounded-xl p-4">

              <p className="text-green-700 font-medium">
                📍 Your location detected
              </p>

              <p className="text-xs text-green-600 mt-1">
                Hospitals are now sorted by distance.
              </p>

            </div>

          )}


          {locationError && (

            <div className="mt-4 bg-orange-50 border border-orange-100 rounded-xl p-4">

              <p className="text-orange-700 text-sm">
                {locationError}
              </p>

            </div>

          )}

        </div>


        {/* Selected Hospital */}
        {selectedHospital && (

          <div className="bg-blue-50 border border-blue-200 rounded-2xl p-5 mb-6">

            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

              <div>

                <p className="text-xs font-semibold text-blue-600 uppercase">
                  Selected Hospital
                </p>

                <h2 className="text-xl font-bold text-gray-800 mt-1">
                  {selectedHospital.name}
                </h2>

                <p className="text-sm text-gray-600 mt-1">
                  📍 {selectedHospital.address}
                </p>

              </div>

              <button
                onClick={() =>
                  handleContinue()
                }
                className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700"
              >
                Continue →
              </button>

            </div>

          </div>

        )}


        {/* Hospital List */}
        <div>

          <div className="flex items-center justify-between mb-4">

            <div>

              <h2 className="text-xl font-bold text-gray-800">
                {userLocation
                  ? "Nearby Hospitals"
                  : "Available Hospitals"}
              </h2>

              <p className="text-sm text-gray-500 mt-1">
                {filteredHospitals.length} hospital(s) found
              </p>

            </div>

          </div>


          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {filteredHospitals.map(
              (hospital) => {

                const isSelected =
                  selectedHospital?.id ===
                  hospital.id

                return (

                  <div
                    key={hospital.id}
                    className={`bg-white rounded-2xl border-2 p-5 shadow-sm transition ${isSelected
                        ? "border-blue-600"
                        : "border-gray-100"
                      }`}
                  >

                    {/* Hospital top */}
                    <div className="flex gap-4">

                      <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center text-3xl flex-shrink-0">
                        🏥
                      </div>


                      <div className="flex-1">

                        <div className="flex justify-between gap-3">

                          <div>

                            <h3 className="font-bold text-lg text-gray-800">
                              {hospital.name}
                            </h3>

                            <p className="text-sm text-gray-500 mt-1">
                              📍 {hospital.address}
                            </p>

                          </div>


                          {isSelected && (

                            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center flex-shrink-0">
                              ✓
                            </div>

                          )}

                        </div>


                        {/* Distance */}
                        {hospital.distance !== null && (

                          <div className="mt-3">

                            <span className="inline-flex items-center px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold">
                              📏{" "}
                              {hospital.distance < 1
                                ? `${Math.round(
                                  hospital.distance *
                                  1000
                                )} m away`
                                : `${hospital.distance.toFixed(
                                  1
                                )} km away`}
                            </span>

                          </div>

                        )}

                      </div>

                    </div>


                    {/* Tags */}
                    <div className="flex flex-wrap gap-2 mt-5">

                      {hospital.type && (
                        <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-xs">
                          {hospital.type}
                        </span>
                      )}

                      {hospital.registered && (
                        <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                          ✓ Registered
                        </span>
                      )}

                      {hospital.city && (
                        <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs">
                          📍 {hospital.city}
                        </span>
                      )}

                    </div>


                    {/* Hospital information */}
                    <div className="grid grid-cols-2 gap-3 mt-5">

                      <div className="bg-gray-50 rounded-xl p-3">

                        <p className="text-xs text-gray-500">
                          Address
                        </p>

                        <p className="text-sm font-medium text-gray-700 mt-1">
                          {hospital.address}
                        </p>

                      </div>

                      <div className="bg-gray-50 rounded-xl p-3">

                        <p className="text-xs text-gray-500">
                          Contact
                        </p>

                        <p className="text-sm font-medium text-gray-700 mt-1">
                          +91 {hospital.phone}
                        </p>

                      </div>

                    </div>


                    {/* Actions */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-5">

                      <button
                        onClick={() =>
                          handleSelectHospital(
                            hospital
                          )
                        }
                        className={`px-3 py-2 rounded-lg text-sm font-semibold ${isSelected
                            ? "bg-blue-600 text-white"
                            : "bg-blue-50 text-blue-700 hover:bg-blue-100"
                          }`}
                      >
                        {isSelected
                          ? "✓ Selected"
                          : "Select"}
                      </button>


                      <button
                        onClick={() =>
                          handleOpenMap(
                            hospital
                          )
                        }
                        className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-200"
                      >
                        🗺️ Map
                      </button>


                      <button
                        onClick={() =>
                          handleDirections(
                            hospital
                          )
                        }
                        className="px-3 py-2 bg-green-50 text-green-700 rounded-lg text-sm font-semibold hover:bg-green-100"
                      >
                        🚗 Directions
                      </button>


                      <button
                        onClick={() =>
                          handleCall(
                            hospital.phone
                          )
                        }
                        className="px-3 py-2 bg-purple-50 text-purple-700 rounded-lg text-sm font-semibold hover:bg-purple-100"
                      >
                        📞 Call
                      </button>

                    </div>

                  </div>

                )
              }
            )}

          </div>


          {/* No result */}
          {hospitalsError && (
            <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm" role="alert">
              {hospitalsError}
            </div>
          )}
          {hospitalsLoading && (
            <p className="text-sm text-gray-500" role="status">Loading hospitals…</p>
          )}
          {!hospitalsLoading && filteredHospitals.length === 0 && (

            <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">

              <div className="text-4xl mb-3">
                🔍
              </div>

              <h3 className="font-bold text-gray-800">
                No hospitals found
              </h3>

              <p className="text-sm text-gray-500 mt-1">
                Try another hospital name or location.
              </p>

            </div>

          )}

        </div>


        {/* Bottom Continue */}
        <div className="flex justify-end mt-8">

          <button
            onClick={handleContinue}
            disabled={!selectedHospital}
            className={`px-7 py-3 rounded-xl font-semibold ${selectedHospital
                ? "bg-blue-600 text-white hover:bg-blue-700"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
              }`}
          >
            Continue to Appointment →
          </button>

        </div>

      </div>

    </div>
  )
}

export default HospitalSelection