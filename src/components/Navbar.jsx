import { useState, useEffect, useRef, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useHospitals } from "../assets/context/HospitalsContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"

function Navbar() {
  const navigate = useNavigate()
  const {
    selectedHospital,
    selectHospital,
  } = usePatient()

  const { hospitals: contextHospitals } = useHospitals()
  const { activeRoleName, switchRole, roles } = useRole()
  const { isStaff, user, logout, isLoggedIn, patient } = useAuth()

  const [isHospitalOpen, setIsHospitalOpen] = useState(false)
  const [isRoleMenuOpen, setIsRoleMenuOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [userLocation, setUserLocation] = useState(null)
  const [locationLoading, setLocationLoading] = useState(false)
  const [locationError, setLocationError] = useState("")
  const { language, setLanguage } = useLanguage()
  const [isNotificationOpen, setIsNotificationOpen] = useState(false)

  const dropdownRef = useRef(null)
  const notificationRef = useRef(null)
  const roleRef = useRef(null)

  // Hospitals the user may act in (from the API). Distance is only shown for
  // hospitals that have real coordinates; none are invented here.
  const hospitalsList = useMemo(() => contextHospitals || [], [contextHospitals])

  // Automatically select first hospital if none is selected yet
  // (also replaces a stale selection that is no longer in the user's list)
  useEffect(() => {
    if (hospitalsList.length === 0) return
    const stillValid =
      selectedHospital && hospitalsList.some((h) => String(h.id) === String(selectedHospital.id))
    if (!stillValid) {
      selectHospital(hospitalsList[0])
    }
  }, [selectedHospital, hospitalsList, selectHospital])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsHospitalOpen(false)
      }
      if (notificationRef.current && !notificationRef.current.contains(event.target)) {
        setIsNotificationOpen(false)
      }
      if (roleRef.current && !roleRef.current.contains(event.target)) {
        setIsRoleMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Distance calculation
  const calculateDistance = (lat1, lon1, lat2, lon2) => {
    const R = 6371
    const dLat = ((lat2 - lat1) * Math.PI) / 180
    const dLon = ((lon2 - lon1) * Math.PI) / 180
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    return R * c
  }

  // Get user location
  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setLocationError("Location is not supported by your browser.")
      return
    }

    setLocationLoading(true)
    setLocationError("")

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        })
        setLocationLoading(false)
      },
      () => {
        setLocationLoading(false)
        setLocationError("Location permission was denied.")
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    )
  }

  // Add distance
  const hasCoords = (hospital) =>
    Number.isFinite(Number(hospital.latitude)) && Number.isFinite(Number(hospital.longitude)) &&
    hospital.latitude !== null && hospital.latitude !== undefined

  const mapQuery = (hospital) =>
    hasCoords(hospital)
      ? `${hospital.latitude},${hospital.longitude}`
      : encodeURIComponent([hospital.name, hospital.address, hospital.city, hospital.state].filter(Boolean).join(", "))

  const hospitalsWithDistance = hospitalsList.map((hospital) => {
    if (!userLocation || !hasCoords(hospital)) {
      return {
        ...hospital,
        distance: null,
      }
    }

    const distance = calculateDistance(
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
  const sortedHospitals = [...hospitalsWithDistance].sort((a, b) => {
    if (a.distance === null || b.distance === null) {
      return 0
    }
    return a.distance - b.distance
  })

  // Search filter
  const filteredHospitals = sortedHospitals.filter((hospital) =>
    `${hospital.name} ${hospital.address}`
      .toLowerCase()
      .includes(search.toLowerCase())
  )

  // Select hospital
  const handleSelectHospital = (hospital) => {
    selectHospital(hospital)
    setIsHospitalOpen(false)
    setSearch("")
  }

  // Open map
  const handleMap = (hospital) => {
    const url = `https://www.google.com/maps/search/?api=1&query=${mapQuery(hospital)}`
    window.open(url, "_blank", "noopener,noreferrer")
  }

  // Directions
  const handleDirections = (hospital) => {
    let url = userLocation
      ? `https://www.google.com/maps/dir/?api=1&origin=${userLocation.latitude},${userLocation.longitude}&destination=${mapQuery(hospital)}`
      : `https://www.google.com/maps/dir/?api=1&destination=${mapQuery(hospital)}`
    window.open(url, "_blank", "noopener,noreferrer")
  }

  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-white border-b border-gray-200 shadow-sm z-40">
      <div className="h-full px-3 sm:px-6 flex items-center justify-between gap-4">

        {/* LEFT - Branding */}
        <div className="flex items-center gap-2 sm:gap-3">

          {/* Logo & Title */}
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center text-lg shadow-sm text-white flex-shrink-0">
              🏥
            </div>
            <div>
              <h1 className="text-base font-bold text-gray-800 leading-tight">
                HMS
              </h1>
              <p className="text-[11px] text-gray-500 hidden md:block leading-none">
                Hospital Management
              </p>
            </div>
          </div>

        </div>

        {/* RIGHT - Actions & Profile */}
        <div className="flex items-center gap-3">

          {/* Hospital Selector */}
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsHospitalOpen(!isHospitalOpen)}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-xl hover:bg-blue-50 transition cursor-pointer"
              title="Select Active Hospital"
            >
              <span className="text-lg">🏥</span>
              <div className="hidden sm:block text-left">
                <p className="text-[10px] uppercase font-semibold text-gray-500 tracking-wider">
                  Hospital
                </p>
                <p className="text-xs font-semibold text-gray-800 max-w-[170px] truncate">
                  {selectedHospital ? selectedHospital.name : "Select Hospital"}
                </p>
              </div>
              <span className="text-gray-400 text-xs ml-1">
                {isHospitalOpen ? "▲" : "▼"}
              </span>
            </button>

            {/* Dropdown Menu */}
            {isHospitalOpen && (
              <div className="absolute right-0 top-12 mt-1 w-[360px] max-w-[90vw] bg-white border border-gray-200 rounded-2xl shadow-2xl z-50 overflow-hidden">
                {/* Dropdown Header */}
                <div className="p-4 border-b border-gray-100 bg-gray-50/70">
                  <h3 className="font-bold text-gray-800 text-sm">
                    Select Hospital
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Search or find a nearby hospital
                  </p>
                </div>

                {/* Search Box */}
                <div className="p-3 border-b border-gray-100">
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">
                      🔍
                    </span>
                    <input
                      type="text"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search hospital name or city..."
                      className="w-full border border-gray-300 rounded-xl pl-9 pr-3 py-2 text-xs outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                {/* Location Detection */}
                <div className="p-3 border-b border-gray-100 bg-blue-50/40">
                  <button
                    type="button"
                    onClick={handleGetLocation}
                    disabled={locationLoading}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-xl font-medium text-xs hover:bg-blue-700 disabled:opacity-60 transition cursor-pointer shadow-sm"
                  >
                    <span>📍</span>
                    <span>
                      {locationLoading
                        ? "Detecting location..."
                        : "Use Current Location"}
                    </span>
                  </button>

                  {locationError && (
                    <p className="text-[11px] text-orange-600 mt-1.5 px-1 font-medium">
                      ⚠️ {locationError}
                    </p>
                  )}

                  {userLocation && (
                    <p className="text-[11px] text-green-600 mt-1.5 px-1 font-medium">
                      ✓ Location active — showing nearest hospitals first
                    </p>
                  )}
                </div>

                {/* Hospital List */}
                <div className="max-h-[300px] overflow-y-auto p-2 divide-y divide-gray-50">
                  {filteredHospitals.length > 0 ? (
                    filteredHospitals.map((hospital) => {
                      const isSelected = selectedHospital?.id === hospital.id

                      return (
                        <div
                          key={hospital.id}
                          className={`p-2.5 rounded-xl transition ${isSelected
                            ? "bg-blue-50/80 border border-blue-200"
                            : "hover:bg-gray-50 border border-transparent"
                            }`}
                        >
                          <button
                            type="button"
                            onClick={() => handleSelectHospital(hospital)}
                            className="w-full text-left cursor-pointer"
                          >
                            <div className="flex gap-2.5 items-start">
                              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0 text-base">
                                🏥
                              </div>

                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-1">
                                  <p className="font-semibold text-gray-800 text-xs truncate">
                                    {hospital.name}
                                  </p>
                                  {isSelected && (
                                    <span className="text-blue-600 font-bold text-xs bg-blue-100 px-1.5 py-0.5 rounded-full">
                                      Active
                                    </span>
                                  )}
                                </div>

                                <p className="text-[11px] text-gray-500 truncate mt-0.5">
                                  📍 {hospital.address || "Begusarai, Bihar"}
                                </p>

                                {hospital.distance !== null && (
                                  <p className="text-[11px] text-green-600 font-medium mt-0.5">
                                    📏{" "}
                                    {hospital.distance < 1
                                      ? `${Math.round(hospital.distance * 1000)} m away`
                                      : `${hospital.distance.toFixed(1)} km away`}
                                  </p>
                                )}
                              </div>
                            </div>
                          </button>

                          {/* Quick Map Actions */}
                          <div className="flex gap-1.5 mt-2 pl-10">
                            <button
                              type="button"
                              onClick={() => handleMap(hospital)}
                              className="text-[11px] px-2 py-1 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition cursor-pointer"
                            >
                              🗺️ Map
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDirections(hospital)}
                              className="text-[11px] px-2 py-1 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition cursor-pointer font-medium"
                            >
                              🚗 Directions
                            </button>
                          </div>
                        </div>
                      )
                    })
                  ) : (
                    <div className="text-center py-6">
                      <p className="text-gray-400 text-2xl">🔍</p>
                      <p className="font-medium text-gray-600 text-xs mt-1">
                        No hospital found
                      </p>
                      <p className="text-[11px] text-gray-400">
                        Try a different search term
                      </p>
                    </div>
                  )}
                </div>

                {/* Dropdown Footer */}
                <div className="border-t border-gray-100 p-2.5 bg-gray-50/50 text-center">
                  <p className="text-[10px] text-gray-400">
                    Switching hospitals updates patients, appointments & queue
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Language Switcher */}
          <div className="hidden sm:flex bg-gray-100 rounded-xl p-0.5">
            <button
              type="button"
              onClick={() => setLanguage("en")}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${language === "en"
                ? "bg-white text-blue-600 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
                }`}
            >
              EN
            </button>
            <button
              type="button"
              onClick={() => setLanguage("hi")}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${language === "hi"
                ? "bg-white text-blue-600 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
                }`}
            >
              हिंदी
            </button>
          </div>

          {/* Notifications Button */}
          <div className="relative" ref={notificationRef}>
            <button
              type="button"
              onClick={() => setIsNotificationOpen(!isNotificationOpen)}
              className="relative w-9 h-9 rounded-full hover:bg-gray-100 flex items-center justify-center text-lg text-gray-600 transition cursor-pointer"
              title="Notifications"
            >
              🔔
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
            </button>

            {isNotificationOpen && (
              <div className="absolute right-0 top-12 mt-1 w-72 bg-white border border-gray-200 rounded-2xl shadow-xl z-50 p-3">
                <div className="flex items-center justify-between pb-2 border-b border-gray-100">
                  <h4 className="text-xs font-bold text-gray-800">Notifications</h4>
                  <span className="text-[10px] text-blue-600 font-medium">Mark all read</span>
                </div>
                <div className="divide-y divide-gray-50 max-h-48 overflow-y-auto">
                  <div className="py-2">
                    <p className="text-xs font-medium text-gray-800">New appointment booked</p>
                    <p className="text-[10px] text-gray-400">Dr. Sharma • 10 mins ago</p>
                  </div>
                  <div className="py-2">
                    <p className="text-xs font-medium text-gray-800">Pharmacy stock alert</p>
                    <p className="text-[10px] text-gray-400">Paracetamol below minimum • 1 hr ago</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Role Switcher */}
          <div className="relative" ref={roleRef}>
            <button
              type="button"
              onClick={() => setIsRoleMenuOpen(!isRoleMenuOpen)}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-xl hover:bg-blue-50 transition cursor-pointer"
              title="Switch role"
            >
              <span className="text-sm">👤</span>
              <div className="hidden sm:block text-left">
                <p className="text-[10px] uppercase font-semibold text-gray-500 tracking-wider">
                  Role
                </p>
                <p className="text-xs font-semibold text-gray-800 max-w-[90px] truncate">
                  {activeRoleName || "Admin"}
                </p>
              </div>
            </button>
            {isRoleMenuOpen && (
              <div className="absolute right-0 top-12 mt-1 w-48 bg-white border border-gray-200 rounded-2xl shadow-xl z-50 py-1">
                {(roles || [])
                  .filter((role) => {
                    if (isStaff) {
                      const backendRoles = user?.user?.roles || user?.roles || []
                      if (!backendRoles.length) return role.name === activeRoleName
                      return backendRoles.some(
                        (item) =>
                          String(item).toLowerCase() === role.name.toLowerCase() ||
                          (item === "Reception" && role.name === "Receptionist")
                      )
                    }
                    if (isLoggedIn && patient && !isStaff) {
                      return role.name === "Patient"
                    }
                    return false
                  })
                  .map((role) => (
                  <button
                    key={role.id}
                    type="button"
                    onClick={() => {
                      switchRole(role.name)
                      setIsRoleMenuOpen(false)
                    }}
                    className={`w-full text-left px-4 py-2 text-xs hover:bg-blue-50 ${
                      role.name === activeRoleName
                        ? "text-blue-600 font-semibold"
                        : "text-gray-700"
                    }`}
                  >
                    {role.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* User Profile */}
          <div className="flex items-center gap-2 pl-2 sm:pl-3 border-l border-gray-200">
            <div className="w-8 h-8 bg-blue-100 text-blue-700 font-bold rounded-full flex items-center justify-center text-xs shadow-sm">
              {(user?.username || activeRoleName || "A").charAt(0).toUpperCase()}
            </div>
            <div className="hidden sm:block text-left">
              <span className="text-xs font-semibold text-gray-800 block leading-tight">
                {user?.username || activeRoleName || "Admin"}
              </span>
              <span className="text-[10px] text-gray-500 block leading-tight">
                {activeRoleName || "Guest"}
              </span>
            </div>
            {isStaff && (
              <button
                type="button"
                onClick={() => {
                  logout()
                  navigate("/")
                }}
                className="hidden md:inline text-[10px] text-gray-500 hover:text-red-600"
              >
                Logout
              </button>
            )}
          </div>

        </div>

      </div>
    </header>
  )
}

export default Navbar