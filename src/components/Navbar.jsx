import { useState, useEffect, useRef, useMemo, useCallback } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import {
  Bell,
  Check,
  ChevronDown,
  CornerDownLeft,
  Hospital,
  LocateFixed,
  LogOut,
  MapPin,
  Menu,
  Navigation,
  Search,
  Settings,
  UserCog,
} from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useHospitals } from "../assets/context/HospitalsContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { useSidebar } from "../assets/context/SidebarContext.jsx"
import { visibleStaffNav } from "../config/navigation.js"
import { Avatar, Modal } from "./ui"
import api from "../services/api.js"

/** Closes a popover when the user clicks outside it or presses Escape. */
function usePopover() {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    const onDown = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false)
    const onKey = (e) => e.key === "Escape" && setOpen(false)
    document.addEventListener("mousedown", onDown)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onDown)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])
  return { open, setOpen, ref }
}

const popoverPanel =
  "absolute right-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-line bg-white shadow-xl animate-rise-in"

const toList = (data) => (Array.isArray(data) ? data : data?.results || [])

function timeAgo(value) {
  const then = new Date(value).getTime()
  if (!Number.isFinite(then)) return ""
  const mins = Math.round((Date.now() - then) / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs} h ago`
  return new Date(value).toLocaleDateString()
}

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
            className="hms-input pl-9"
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
                className="hms-input h-9 min-h-0 pl-8 text-[13px]"
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

/* ---------------- Notifications (real API) ---------------- */
function NotificationsMenu({ hospitalId, t }) {
  const { open, setOpen, ref } = usePopover()
  const [items, setItems] = useState([])
  const [status, setStatus] = useState("idle") // idle | loading | ready | error

  const load = useCallback(async () => {
    if (!hospitalId) return
    setStatus("loading")
    try {
      const data = await api.notifications.list(hospitalId)
      setItems(toList(data))
      setStatus("ready")
    } catch {
      setStatus("error")
    }
  }, [hospitalId])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (open) load()
  }, [open, load])

  const unread = items.filter((n) => !n.is_read).length

  const markRead = async (n) => {
    try {
      await api.notifications.markRead(n.id)
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)))
    } catch {
      // leave it unread; the next refresh shows the server's state
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={unread ? `${t("Notifications")}, ${unread} unread` : t("Notifications")}
        className="relative flex h-10 w-10 items-center justify-center rounded-lg text-ink-600 hover:bg-ink-100 hover:text-ink-900"
      >
        <Bell size={19} aria-hidden="true" />
        {unread > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white tabular-nums">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className={`${popoverPanel} w-80 max-w-[calc(100vw-2rem)]`} role="dialog" aria-label={t("Notifications")}>
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <p className="text-sm font-semibold text-ink-900">{t("Notifications")}</p>
            {unread > 0 && <span className="text-xs text-ink-500">{unread} unread</span>}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {status === "loading" && items.length === 0 && <p className="px-4 py-8 text-center text-[13px] text-ink-500">Loading…</p>}
            {status === "error" && <p className="px-4 py-8 text-center text-[13px] text-ink-500">Notifications could not be loaded.</p>}
            {status === "ready" && items.length === 0 && (
              <div className="px-4 py-8 text-center">
                <Bell size={20} className="mx-auto text-ink-300" aria-hidden="true" />
                <p className="mt-2 text-[13px] text-ink-500">You&apos;re all caught up.</p>
              </div>
            )}
            {!hospitalId && <p className="px-4 py-8 text-center text-[13px] text-ink-500">Select a hospital to see notifications.</p>}
            <ul className="divide-y divide-ink-100">
              {items.slice(0, 20).map((n) => (
                <li key={n.id} className={`flex gap-3 px-4 py-3 ${n.is_read ? "" : "bg-brand-50/50"}`}>
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.is_read ? "bg-transparent" : "bg-brand-500"}`} aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium text-ink-900">{n.title}</p>
                    {n.message && <p className="mt-0.5 line-clamp-2 text-xs text-ink-600">{n.message}</p>}
                    <p className="mt-1 text-[11px] text-ink-400">
                      {n.notification_type ? `${n.notification_type} · ` : ""}
                      {timeAgo(n.created_at)}
                    </p>
                  </div>
                  {!n.is_read && (
                    <button
                      type="button"
                      onClick={() => markRead(n)}
                      className="h-7 shrink-0 self-start rounded-md px-2 text-[11.5px] font-medium text-brand-700 hover:bg-brand-100"
                    >
                      Mark read
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

/* ---------------- User menu (role + sign out) ---------------- */
function UserMenu({ t }) {
  const navigate = useNavigate()
  const { open, setOpen, ref } = usePopover()
  const { activeRoleName, switchRole, roles } = useRole()
  const { isStaff, user, logout, isLoggedIn, patient } = useAuth()

  const displayName = user?.username || user?.user?.username || activeRoleName || "User"

  const availableRoles = (roles || []).filter((role) => {
    if (isStaff) {
      const backendRoles = user?.user?.roles || user?.roles || []
      if (!backendRoles.length) return role.name === activeRoleName
      return backendRoles.some(
        (item) => String(item).toLowerCase() === role.name.toLowerCase() || (item === "Reception" && role.name === "Receptionist"),
      )
    }
    if (isLoggedIn && patient && !isStaff) return role.name === "Patient"
    return false
  })

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-10 items-center gap-2.5 rounded-lg pl-1 pr-2 hover:bg-ink-100"
      >
        <Avatar name={displayName} size="sm" />
        <span className="hidden text-left leading-tight md:block">
          <span className="block max-w-[8rem] truncate text-[13px] font-semibold text-ink-900">{displayName}</span>
          <span className="block max-w-[8rem] truncate text-[11.5px] text-ink-500">{activeRoleName || "Guest"}</span>
        </span>
        <ChevronDown size={15} className="hidden text-ink-400 md:block" aria-hidden="true" />
      </button>

      {open && (
        <div className={`${popoverPanel} w-60`} role="menu">
          <div className="border-b border-line px-4 py-3">
            <p className="truncate text-sm font-semibold text-ink-900">{displayName}</p>
            <p className="text-xs text-ink-500">Acting as {activeRoleName || "Guest"}</p>
          </div>
          {availableRoles.length > 1 && (
            <div className="border-b border-line py-1.5">
              <p className="px-4 pb-1 pt-1 text-[11px] font-semibold uppercase tracking-wide text-ink-400">Switch role</p>
              {availableRoles.map((role) => (
                <button
                  key={role.id}
                  type="button"
                  role="menuitemradio"
                  aria-checked={role.name === activeRoleName}
                  onClick={() => {
                    switchRole(role.name)
                    setOpen(false)
                  }}
                  className="flex w-full items-center gap-2 px-4 py-1.5 text-left text-[13px] text-ink-700 hover:bg-ink-50"
                >
                  <UserCog size={15} className="text-ink-400" aria-hidden="true" />
                  <span className="flex-1">{role.name}</span>
                  {role.name === activeRoleName && <Check size={15} className="text-brand-600" aria-hidden="true" />}
                </button>
              ))}
            </div>
          )}
          <div className="py-1.5">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false)
                navigate("/settings")
              }}
              className="flex w-full items-center gap-2 px-4 py-1.5 text-left text-[13px] text-ink-700 hover:bg-ink-50"
            >
              <Settings size={15} className="text-ink-400" aria-hidden="true" />
              {t("Settings")}
            </button>
            {isStaff && (
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false)
                  logout()
                  navigate("/")
                }}
                className="flex w-full items-center gap-2 px-4 py-1.5 text-left text-[13px] text-red-700 hover:bg-red-50"
              >
                <LogOut size={15} aria-hidden="true" />
                {t("Logout")}
              </button>
            )}
          </div>
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
  const { language, setLanguage, t } = useLanguage()
  const { openMobile } = useSidebar()
  const [jumpOpen, setJumpOpen] = useState(false)

  const hospitalsList = useMemo(() => contextHospitals || [], [contextHospitals])
  const groups = visibleStaffNav(canView)

  // Select the first hospital if none is selected yet, and replace a stale
  // selection that is no longer in the user's list.
  useEffect(() => {
    if (hospitalsList.length === 0) return
    const stillValid = selectedHospital && hospitalsList.some((h) => String(h.id) === String(selectedHospital.id))
    if (!stillValid) selectHospital(hospitalsList[0])
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
    <header className="sticky top-0 z-20 h-16 border-b border-line bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/85">
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

          <div className="hidden rounded-lg bg-ink-100 p-0.5 sm:flex" role="radiogroup" aria-label="Interface language">
            {[
              { id: "en", label: "EN" },
              { id: "hi", label: "हिं" },
            ].map((lang) => (
              <button
                key={lang.id}
                type="button"
                role="radio"
                aria-checked={language === lang.id}
                onClick={() => setLanguage(lang.id)}
                className={`rounded-md px-2.5 py-1 text-xs font-semibold ${
                  language === lang.id ? "bg-white text-brand-700 shadow-sm" : "text-ink-600 hover:text-ink-900"
                }`}
              >
                {lang.label}
              </button>
            ))}
          </div>

          <NotificationsMenu hospitalId={selectedHospital?.id} t={t} />
          <div className="mx-1 hidden h-6 w-px bg-line sm:block" aria-hidden="true" />
          <UserMenu t={t} />
        </div>
      </div>

      <QuickJump open={jumpOpen} onClose={() => setJumpOpen(false)} groups={groups} t={t} />
    </header>
  )
}

export default Navbar
