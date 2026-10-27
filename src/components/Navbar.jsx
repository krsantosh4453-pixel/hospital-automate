import { useState, useEffect, useMemo } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { Check, ChevronDown, CornerDownLeft, Hospital, LocateFixed, MapPin, Menu, Navigation, Search } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useHospitals } from "../assets/context/HospitalsContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { useSidebar } from "../assets/context/SidebarContext.jsx"
import { guestStaffNav, visibleStaffNav } from "../config/navigation.js"
import { Modal } from "./ui"
import { HeaderActions, popoverPanel, usePopover } from "./HeaderMenus.jsx"

/* ---------------- Quick jump (Ctrl/⌘ K) ---------------- */
function QuickJump({ open, onClose, groups, t }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const [index, setIndex] = useState(0)

  const items = useMemo(() => {
    const all = groups.flatMap((g) => g.items.map((item) => ({ ...item, group: t(g.label), title: t(item.label) })))
    const q = query.trim().toLowerCase()
    return q ? all.filter((i) => `${i.title} ${i.label} ${i.group}`.toLowerCase().includes(q)) : all
  }, [groups, query, t])

  const go = (item) => {
    onClose()
    setQuery("")
    navigate(item.to)
  }

  return (
    <Modal open={open} onClose={onClose} title="Jump to a page" size="md">
      <div className="-mx-1">
        <div className="relative">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" aria-hidden="true" />
          <input
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setIndex(0)
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault()
                setIndex((i) => Math.min(i + 1, items.length - 1))
              } else if (e.key === "ArrowUp") {
                e.preventDefault()
                setIndex((i) => Math.max(i - 1, 0))
              } else if (e.key === "Enter" && items[index]) {
                e.preventDefault()
                go(items[index])
              }
            }}
            placeholder="Type a module name…"
            aria-label="Search pages"
            aria-controls="quick-jump-list"
            className="hms-input w-full pl-9"
          />
        </div>
        <ul id="quick-jump-list" role="listbox" className="mt-3 max-h-[50vh] space-y-0.5 overflow-y-auto">
          {items.length === 0 && <li className="px-3 py-6 text-center text-sm text-ink-500">No page matches “{query}”.</li>}
          {items.map((item, i) => {
            const Icon = item.icon
            const active = i === index
            return (
              <li key={item.to} role="option" aria-selected={active}>
                <button
                  type="button"
                  onMouseEnter={() => setIndex(i)}
                  onClick={() => go(item)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm ${active ? "bg-brand-50 text-brand-800" : "text-ink-700"}`}
                >
                  <Icon size={17} className={active ? "text-brand-600" : "text-ink-400"} aria-hidden="true" />
                  <span className="flex-1 font-medium">{item.title}</span>
                  <span className="text-xs text-ink-400">{item.group}</span>
                  {active && <CornerDownLeft size={14} className="text-brand-500" aria-hidden="true" />}
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    </Modal>
  )
}

/* ---------------- Hospital switcher ---------------- */
function HospitalSwitcher({ hospitals, selectedHospital, onSelect, t }) {
  const { open, setOpen, ref } = usePopover()
  const [search, setSearch] = useState("")
  const [userLocation, setUserLocation] = useState(null)
  const [locationLoading, setLocationLoading] = useState(false)
  const [locationError, setLocationError] = useState("")

  const calculateDistance = (lat1, lon1, lat2, lon2) => {
    const R = 6371
    const dLat = ((lat2 - lat1) * Math.PI) / 180
    const dLon = ((lon2 - lon1) * Math.PI) / 180
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2)
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  }

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setLocationError("Location is not supported by your browser.")
      return
    }
    setLocationLoading(true)
    setLocationError("")
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({ latitude: position.coords.latitude, longitude: position.coords.longitude })
        setLocationLoading(false)
      },
      () => {
        setLocationLoading(false)
        setLocationError("Location permission was denied.")
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    )
  }

  // Distance only for hospitals with real coordinates; none are invented.
  const hasCoords = (h) =>
    h.latitude !== null && h.latitude !== undefined && Number.isFinite(Number(h.latitude)) && Number.isFinite(Number(h.longitude))

  const mapQuery = (h) =>
    hasCoords(h)
      ? `${h.latitude},${h.longitude}`
      : encodeURIComponent([h.name, h.address, h.city, h.state].filter(Boolean).join(", "))

  const list = hospitals
    .map((h) => ({
      ...h,
      distance: userLocation && hasCoords(h) ? calculateDistance(userLocation.latitude, userLocation.longitude, h.latitude, h.longitude) : null,
    }))
    .sort((a, b) => (a.distance === null || b.distance === null ? 0 : a.distance - b.distance))
    .filter((h) => `${h.name} ${h.address || ""} ${h.city || ""}`.toLowerCase().includes(search.toLowerCase()))

  const openUrl = (url) => window.open(url, "_blank", "noopener,noreferrer")

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="flex h-10 max-w-[15rem] items-center gap-2.5 rounded-lg border border-line bg-white pl-2.5 pr-2 text-left hover:border-line-strong hover:bg-ink-50"
      >
        <Hospital size={18} className="shrink-0 text-brand-600" aria-hidden="true" />
        <span className="hidden min-w-0 sm:block">
          <span className="block text-[10.5px] font-medium uppercase tracking-wide text-ink-500">Hospital</span>
          <span className="block truncate text-[13px] font-semibold leading-4 text-ink-900">
            {selectedHospital ? selectedHospital.name : t("Select Hospital")}
          </span>
        </span>
        <ChevronDown size={16} className={`shrink-0 text-ink-400 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden="true" />
      </button>

      {open && (
        <div className={`${popoverPanel} w-[22rem] max-w-[calc(100vw-2rem)]`} role="dialog" aria-label="Select hospital">
          <div className="border-b border-line p-3">
            <div className="relative">
              <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" aria-hidden="true" />
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or city"
                aria-label="Search hospitals"
                className="hms-input h-9 min-h-0 w-full pl-8 text-[13px]"
              />
            </div>
            <button
              type="button"
              onClick={handleGetLocation}
              disabled={locationLoading}
              className="mt-2 inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50 disabled:opacity-60"
            >
              <LocateFixed size={14} aria-hidden="true" />
              {locationLoading ? "Detecting location…" : userLocation ? "Sorted by distance" : "Sort by distance from me"}
            </button>
            {locationError && <p className="mt-1 px-1.5 text-xs text-amber-700">{locationError}</p>}
          </div>

          <ul className="max-h-80 overflow-y-auto p-1.5">
            {list.length === 0 && (
              <li className="px-3 py-8 text-center text-[13px] text-ink-500">
                {hospitals.length === 0 ? "You are not a member of any hospital yet." : "No hospital matches your search."}
              </li>
            )}
            {list.map((h) => {
              const isSelected = String(selectedHospital?.id) === String(h.id)
              const location = [h.address, h.city, h.state].filter(Boolean).join(", ")
              return (
                <li key={h.id} className={`rounded-lg ${isSelected ? "bg-brand-50" : "hover:bg-ink-50"}`}>
                  <button
                    type="button"
                    onClick={() => {
                      onSelect(h)
                      setOpen(false)
                      setSearch("")
                    }}
                    className="flex w-full items-start gap-2.5 px-2.5 pb-1 pt-2.5 text-left"
                    aria-current={isSelected ? "true" : undefined}
                  >
                    <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${isSelected ? "bg-brand-600 text-white" : "bg-ink-100 text-ink-500"}`}>
                      {isSelected ? <Check size={15} aria-hidden="true" /> : <Hospital size={15} aria-hidden="true" />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px] font-semibold text-ink-900">{h.name}</span>
                      {location && <span className="block truncate text-xs text-ink-500">{location}</span>}
                      {h.distance !== null && (
                        <span className="block text-xs font-medium text-green-700">
                          {h.distance < 1 ? `${Math.round(h.distance * 1000)} m away` : `${h.distance.toFixed(1)} km away`}
                        </span>
                      )}
                    </span>
                  </button>
                  <div className="flex gap-1 pb-2 pl-12">
                    <button
                      type="button"
                      onClick={() => openUrl(`https://www.google.com/maps/search/?api=1&query=${mapQuery(h)}`)}
                      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11.5px] text-ink-600 hover:bg-ink-100"
                    >
                      <MapPin size={12} aria-hidden="true" /> Map
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        openUrl(
                          userLocation
                            ? `https://www.google.com/maps/dir/?api=1&origin=${userLocation.latitude},${userLocation.longitude}&destination=${mapQuery(h)}`
                            : `https://www.google.com/maps/dir/?api=1&destination=${mapQuery(h)}`,
                        )
                      }
                      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11.5px] text-ink-600 hover:bg-ink-100"
                    >
                      <Navigation size={12} aria-hidden="true" /> Directions
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
          <p className="border-t border-line bg-ink-50 px-3 py-2 text-[11.5px] text-ink-500">
            Switching hospital changes every list you see to that hospital&apos;s records.
          </p>
        </div>
      )}
    </div>
  )
}

/* ---------------- Top bar ---------------- */
function Navbar() {
  const location = useLocation()
  const { selectedHospital, selectHospital } = usePatient()
  const { hospitals: contextHospitals } = useHospitals()
  const { canView } = useRole()
  const { isStaff } = useAuth()
  const { t } = useLanguage()
  const { openMobile } = useSidebar()
  const [jumpOpen, setJumpOpen] = useState(false)

  const hospitalsList = useMemo(() => contextHospitals || [], [contextHospitals])
  const groups = isStaff ? visibleStaffNav(canView) : guestStaffNav()

  // Select the first hospital if none is selected yet, replace a stale
  // selection that is no longer in the user's list, and refresh a saved
  // selection whose name has changed on the server.
  useEffect(() => {
    if (hospitalsList.length === 0) return
    const current = selectedHospital && hospitalsList.find((h) => String(h.id) === String(selectedHospital.id))
    if (!current) selectHospital(hospitalsList[0])
    else if (current.name !== selectedHospital.name) selectHospital(current)
  }, [selectedHospital, hospitalsList, selectHospital])

  // Ctrl/⌘ K opens quick jump.
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setJumpOpen(true)
      }
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [])

  useEffect(() => setJumpOpen(false), [location.pathname])

  return (
    <header className="hms-surface-dark sticky top-0 z-20 h-16 border-b border-line">
      <div className="flex h-full items-center gap-2 px-3 sm:gap-3 sm:px-6">
        <button
          type="button"
          onClick={openMobile}
          className="flex h-10 w-10 items-center justify-center rounded-lg text-ink-700 hover:bg-ink-100 lg:hidden"
          aria-label="Open navigation"
        >
          <Menu size={20} aria-hidden="true" />
        </button>

        <button
          type="button"
          onClick={() => setJumpOpen(true)}
          className="hidden h-10 w-full max-w-xs items-center gap-2 rounded-lg border border-line bg-ink-50 px-3 text-[13px] text-ink-500 hover:border-line-strong hover:bg-white md:flex"
        >
          <Search size={16} aria-hidden="true" />
          <span className="flex-1 text-left">Jump to…</span>
          <kbd className="rounded border border-line bg-white px-1.5 py-px font-sans text-[11px] text-ink-500">Ctrl K</kbd>
        </button>
        <button
          type="button"
          onClick={() => setJumpOpen(true)}
          className="flex h-10 w-10 items-center justify-center rounded-lg text-ink-600 hover:bg-ink-100 md:hidden"
          aria-label="Jump to a page"
        >
          <Search size={19} aria-hidden="true" />
        </button>

        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <HospitalSwitcher hospitals={hospitalsList} selectedHospital={selectedHospital} onSelect={selectHospital} t={t} />

          <HeaderActions hospitalId={selectedHospital?.id} />
        </div>
      </div>

      <QuickJump open={jumpOpen} onClose={() => setJumpOpen(false)} groups={groups} t={t} />
    </header>
  )
}

export default Navbar
