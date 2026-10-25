import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useHospitals } from "../assets/context/HospitalsContext.jsx"
import { CarIcon, CheckIcon, HospitalIcon, LocateFixed, MapIcon, PhoneIcon, SearchIcon } from "lucide-react"
import { Alert, Badge, Button, Card, EmptyState, PageHeader, SearchInput, Toolbar } from "../components/ui"
import { useToast } from "../components/Toast.jsx"

function HospitalSelection() {
  const toast = useToast()

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
      toast.warning("Please select a hospital.")
      return
    }

    selectHospital(selectedHospital)

    navigate("/appointments")
  }

  // Coordinates when the hospital has them, otherwise its name and address.
  const mapQuery = (hospital) =>
    hospital.latitude != null && hospital.longitude != null
      ? `${hospital.latitude},${hospital.longitude}`
      : encodeURIComponent([hospital.name, hospital.address, hospital.city].filter(Boolean).join(", "))

  // Open map
  const handleOpenMap = (hospital) => {
    window.open(`https://www.google.com/maps/search/?api=1&query=${mapQuery(hospital)}`, "_blank", "noopener,noreferrer")
  }

  // Get directions
  const handleDirections = (hospital) => {
    const directionsUrl = userLocation
      ? `https://www.google.com/maps/dir/?api=1&origin=${userLocation.latitude},${userLocation.longitude}&destination=${mapQuery(hospital)}`
      : `https://www.google.com/maps/dir/?api=1&destination=${mapQuery(hospital)}`
    window.open(directionsUrl, "_blank", "noopener,noreferrer")
  }

  // Call hospital
  const handleCall = (phone) => {
    window.location.href =
      `tel:${phone}`
  }

  return (
    <div className="min-h-screen pb-24">
      <PageHeader
        title="Choose a hospital"
        description="Pick the hospital for your appointment. Share your location to sort by distance."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Choose hospital" }]}
      />

      <Card className="mb-5">
        <Toolbar
          actions={
            <Button variant="secondary" icon={LocateFixed} onClick={handleGetLocation} loading={locationLoading}>
              {userLocation ? "Sorted by distance" : "Use my location"}
            </Button>
          }
        >
          <SearchInput value={search} onChange={setSearch} placeholder="Hospital name or address" label="Search hospitals" className="w-full sm:max-w-md" />
        </Toolbar>
        {locationError && <Alert tone="warning" className="m-4">{locationError}</Alert>}
      </Card>

      {hospitalsError && <Alert tone="danger" className="mb-5">{hospitalsError}</Alert>}

      {hospitalsLoading ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton h-36 rounded-2xl" />)}
        </div>
      ) : filteredHospitals.length === 0 ? (
        <Card>
          <EmptyState icon={SearchIcon} title="No hospitals found" description={search ? "Try another name or location." : "No active hospitals are listed yet."} />
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2" role="radiogroup" aria-label="Hospitals">
          {filteredHospitals.map((hospital) => {
            const isSelected = selectedHospital?.id === hospital.id
            return (
              <li key={hospital.id}>
                <div className={`flex h-full flex-col rounded-2xl border bg-white transition-colors ${isSelected ? "border-brand-500 ring-2 ring-brand-500/20" : "border-line hover:border-line-strong"}`}>
                  <button
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    onClick={() => handleSelectHospital(hospital)}
                    className="flex flex-1 items-start gap-4 rounded-t-2xl p-5 text-left"
                  >
                    <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${isSelected ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-700"}`}>
                      {isSelected ? <CheckIcon size={20} aria-hidden="true" /> : <HospitalIcon size={20} aria-hidden="true" />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold text-ink-900">{hospital.name}</span>
                      {hospital.address && <span className="mt-0.5 block text-[13px] text-ink-600">{hospital.address}</span>}
                      <span className="mt-2 flex flex-wrap gap-1.5">
                        {hospital.city && <Badge tone="neutral">{hospital.city}</Badge>}
                        {hospital.type && <Badge tone="neutral">{hospital.type}</Badge>}
                        {hospital.distance !== null && (
                          <Badge tone="success">
                            {hospital.distance < 1 ? `${Math.round(hospital.distance * 1000)} m away` : `${hospital.distance.toFixed(1)} km away`}
                          </Badge>
                        )}
                      </span>
                    </span>
                  </button>
                  <div className="flex flex-wrap items-center gap-1 border-t border-line px-3 py-2">
                    {hospital.phone && (
                      <span className="mr-auto pl-2 text-[13px] text-ink-600 tabular-nums">{hospital.phone}</span>
                    )}
                    <Button size="sm" variant="ghost" icon={MapIcon} onClick={() => handleOpenMap(hospital)}>Map</Button>
                    <Button size="sm" variant="ghost" icon={CarIcon} onClick={() => handleDirections(hospital)}>Directions</Button>
                    {hospital.phone && <Button size="sm" variant="ghost" icon={PhoneIcon} onClick={() => handleCall(hospital.phone)}>Call</Button>}
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {selectedHospital && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-white/95 px-4 py-3 shadow-lg backdrop-blur lg:pl-[calc(var(--sidebar-w,16rem)+2rem)]">
          <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-3">
            <p className="min-w-0 truncate text-sm text-ink-700">
              Selected: <span className="font-semibold text-ink-900">{selectedHospital.name}</span>
            </p>
            <Button onClick={handleContinue}>Continue to appointment</Button>
          </div>
        </div>
      )}
    </div>
  )
}

export default HospitalSelection
