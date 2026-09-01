import { useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"

function Navbar() {
  const {
    selectedHospital,
    selectHospital,
  } = usePatient()

  const [isHospitalOpen, setIsHospitalOpen] =
    useState(false)

  const [search, setSearch] = useState("")

  const [userLocation, setUserLocation] =
    useState(null)

  const [locationLoading, setLocationLoading] =
    useState(false)

  const [locationError, setLocationError] =
    useState("")


  // Demo hospital data
  // Later Django API se aayega
  const hospitals = [
    {
      id: 1,
      name: "City Care Hospital",
      address: "Main Road, Begusarai, Bihar",
      phone: "9876543210",
      latitude: 25.4182,
      longitude: 86.1272,
      type: "Multi-Speciality",
    },
    {
      id: 2,
      name: "LifeLine Hospital",
      address: "Station Road, Begusarai, Bihar",
      phone: "9876543211",
      latitude: 25.4145,
      longitude: 86.1215,
      type: "General & Multi-Speciality",
    },
    {
      id: 3,
      name: "Shanti Medical Centre",
      address: "NH-31, Begusarai, Bihar",
      phone: "9876543212",
      latitude: 25.4112,
      longitude: 86.1352,
      type: "Multi-Speciality",
    },
    {
      id: 4,
      name: "Apollo Care Hospital",
      address: "Station Road, Patna, Bihar",
      phone: "9876543213",
      latitude: 25.5941,
      longitude: 85.1376,
      type: "Multi-Speciality",
    },
    {
      id: 5,
      name: "City Medical Centre",
      address: "Gandhi Maidan, Patna, Bihar",
      phone: "9876543214",
      latitude: 25.6127,
      longitude: 85.1589,
      type: "General Hospital",
    },
  ]


  // Distance calculation
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


  // Get user location
  const handleGetLocation = () => {

    if (!navigator.geolocation) {

      setLocationError(
        "Location is not supported by your browser."
      )

      return
    }

    setLocationLoading(true)
    setLocationError("")

    navigator.geolocation.getCurrentPosition(
      (position) => {

        setUserLocation({
          latitude:
            position.coords.latitude,

          longitude:
            position.coords.longitude,
        })

        setLocationLoading(false)
      },

      () => {

        setLocationLoading(false)

        setLocationError(
          "Location permission was denied."
        )
      },

      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    )
  }


  // Add distance
  const hospitalsWithDistance =
    hospitals.map((hospital) => {

      if (!userLocation) {

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


  // Sort nearest first
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


  // Search
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

    selectHospital(hospital)

    setIsHospitalOpen(false)
    setSearch("")
  }


  // Open map
  const handleMap = (hospital) => {

    const url =
      `https://www.google.com/maps/search/?api=1&query=${hospital.latitude},${hospital.longitude}`

    window.open(
      url,
      "_blank",
      "noopener,noreferrer"
    )
  }


  // Directions
  const handleDirections = (
    hospital
  ) => {

    let url

    if (userLocation) {

      url =
        `https://www.google.com/maps/dir/?api=1&origin=${userLocation.latitude},${userLocation.longitude}&destination=${hospital.latitude},${hospital.longitude}`

    } else {

      url =
        `https://www.google.com/maps/dir/?api=1&destination=${hospital.latitude},${hospital.longitude}`
    }

    window.open(
      url,
      "_blank",
      "noopener,noreferrer"
    )
  }


  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">

      <div className="px-5 py-4 flex items-center justify-between gap-4">

        {/* LEFT - Logo */}
        <div className="flex items-center gap-3">

          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-2xl">
            🏥
          </div>

          <div>

            <h1 className="text-xl font-bold text-gray-800">
              HMS
            </h1>

            <p className="text-sm text-gray-500">
              Hospital Management System
            </p>

          </div>

        </div>


        {/* RIGHT */}
        <div className="flex items-center gap-3">


          {/* Hospital Selector */}
          <div className="relative">

            <button
              onClick={() =>
                setIsHospitalOpen(
                  !isHospitalOpen
                )
              }
              className="flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl hover:bg-blue-50 transition"
            >

              <span className="text-xl">
                🏥
              </span>

              <div className="hidden sm:block text-left">

                <p className="text-xs text-gray-500">
                  Hospital
                </p>

                <p className="text-sm font-semibold text-gray-800 max-w-[180px] truncate">

                  {selectedHospital
                    ? selectedHospital.name
                    : "Select Hospital"}

                </p>

              </div>

              <span className="text-gray-500 text-xs">
                ▼
              </span>

            </button>


            {/* Dropdown */}
            {isHospitalOpen && (

              <div className="absolute right-0 top-14 w-[350px] max-w-[90vw] bg-white border border-gray-200 rounded-2xl shadow-xl z-50 overflow-hidden">

                {/* Dropdown Header */}
                <div className="p-4 border-b border-gray-100">

                  <h3 className="font-bold text-gray-800">
                    Select Hospital
                  </h3>

                  <p className="text-xs text-gray-500 mt-1">
                    Search or find a nearby hospital
                  </p>

                </div>


                {/* Search */}
                <div className="p-3">

                  <div className="relative">

                    <span className="absolute left-3 top-1/2 -translate-y-1/2">
                      🔍
                    </span>

                    <input
                      type="text"
                      value={search}
                      onChange={(e) =>
                        setSearch(
                          e.target.value
                        )
                      }
                      placeholder="Search hospital..."
                      className="w-full border border-gray-300 rounded-xl pl-10 pr-3 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                    />

                  </div>

                </div>


                {/* Location */}
                <div className="px-3">

                  <button
                    onClick={handleGetLocation}
                    disabled={locationLoading}
                    className="w-full flex items-center gap-3 px-4 py-3 bg-blue-50 text-blue-700 rounded-xl font-semibold text-sm hover:bg-blue-100 disabled:opacity-60"
                  >

                    <span className="text-lg">
                      📍
                    </span>

                    <span>
                      {locationLoading
                        ? "Getting your location..."
                        : "Use My Current Location"}
                    </span>

                  </button>


                  {locationError && (

                    <p className="text-xs text-orange-600 mt-2 px-1">
                      {locationError}
                    </p>

                  )}

                  {userLocation && (

                    <p className="text-xs text-green-600 mt-2 px-1">
                      ✓ Location detected — nearest hospitals shown first
                    </p>

                  )}

                </div>


                {/* Hospital List */}
                <div className="max-h-[400px] overflow-y-auto p-3">

                  {filteredHospitals.length > 0 ? (

                    filteredHospitals.map(
                      (hospital) => {

                        const isSelected =
                          selectedHospital?.id ===
                          hospital.id

                        return (

                          <div
                            key={hospital.id}
                            className={`p-3 rounded-xl mb-2 border transition ${isSelected
                                ? "border-blue-500 bg-blue-50"
                                : "border-gray-100 hover:border-blue-200 hover:bg-gray-50"
                              }`}
                          >

                            <button
                              onClick={() =>
                                handleSelectHospital(
                                  hospital
                                )
                              }
                              className="w-full text-left"
                            >

                              <div className="flex gap-3">

                                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                                  🏥
                                </div>


                                <div className="flex-1 min-w-0">

                                  <div className="flex items-center justify-between gap-2">

                                    <p className="font-semibold text-gray-800 text-sm truncate">
                                      {hospital.name}
                                    </p>

                                    {isSelected && (

                                      <span className="text-blue-600 font-bold">
                                        ✓
                                      </span>

                                    )}

                                  </div>


                                  <p className="text-xs text-gray-500 mt-1">
                                    📍 {hospital.address}
                                  </p>


                                  {hospital.distance !== null && (

                                    <p className="text-xs text-green-600 font-semibold mt-1">

                                      📏{" "}

                                      {hospital.distance < 1
                                        ? `${Math.round(
                                          hospital.distance *
                                          1000
                                        )} m away`
                                        : `${hospital.distance.toFixed(
                                          1
                                        )} km away`}

                                    </p>

                                  )}

                                </div>

                              </div>

                            </button>


                            {/* Hospital actions */}
                            <div className="flex gap-2 mt-3 ml-13">

                              <button
                                onClick={() =>
                                  handleMap(
                                    hospital
                                  )
                                }
                                className="text-xs px-3 py-1.5 bg-gray-100 rounded-lg hover:bg-gray-200"
                              >
                                🗺️ Map
                              </button>


                              <button
                                onClick={() =>
                                  handleDirections(
                                    hospital
                                  )
                                }
                                className="text-xs px-3 py-1.5 bg-green-50 text-green-700 rounded-lg hover:bg-green-100"
                              >
                                🚗 Directions
                              </button>

                            </div>

                          </div>

                        )
                      }
                    )

                  ) : (

                    <div className="text-center py-8">

                      <div className="text-3xl">
                        🔍
                      </div>

                      <p className="font-semibold text-gray-700 mt-2">
                        No hospital found
                      </p>

                      <p className="text-xs text-gray-500 mt-1">
                        Try another search
                      </p>

                    </div>

                  )}

                </div>


                {/* Footer */}
                <div className="border-t border-gray-100 p-3">

                  <p className="text-xs text-center text-gray-400">
                    Hospital locations will be loaded from the hospital database.
                  </p>

                </div>

              </div>

            )}

          </div>


          {/* Language */}
          <div className="hidden sm:flex bg-gray-100 rounded-xl p-1">

            <button className="px-3 py-2 bg-white rounded-lg text-blue-600 font-semibold text-sm shadow-sm">
              EN
            </button>

            <button className="px-3 py-2 text-gray-600 text-sm">
              हिंदी
            </button>

          </div>


          {/* Notification */}
          <button className="relative w-10 h-10 rounded-full hover:bg-gray-100 flex items-center justify-center text-xl">
            🔔

            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />

          </button>


          {/* User */}
          <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-gray-200">

            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center text-xl">
              👤
            </div>

            <span className="font-semibold text-gray-700">
              Admin
            </span>

          </div>

        </div>

      </div>

    </header>
  )
}

export default Navbar