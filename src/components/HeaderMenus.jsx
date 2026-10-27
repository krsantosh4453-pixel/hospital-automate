import { useCallback, useEffect, useRef, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Bell, Check, ChevronDown, LogIn, LogOut, Settings, UserCog } from "lucide-react"
import { useRole } from "../assets/context/RoleContext.jsx"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { Avatar } from "./ui"
import api from "../services/api.js"

/*
 * Right side of the top header, shared by the staff layout and the patient
 * portal: language switch, notifications bell, then the profile avatar
 * whose menu holds role switching, settings and sign-out.
 */

/** Closes a popover when the user clicks outside it or presses Escape. */
export function usePopover() {
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

export const popoverPanel =
  "absolute right-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-line bg-white shadow-xl animate-rise-in"

const LANGUAGES = [
  { id: "en", label: "EN", name: "English" },
  { id: "hi", label: "हिं", name: "हिंदी" },
]

// Must match STAFF | IsPatientReadOnly in backend/notifications/views.py:
// these messages go to patients, so other roles may not read them.
const NOTIFICATION_ROLES = new Set(["Admin", "Hospital Manager", "Receptionist", "Doctor", "Nurse"])

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

/* ---------------- Notifications (real API) ---------------- */
/** @param {{ hospitalId?: string|number, canRead?: boolean }} props */
export function NotificationsMenu({ hospitalId, canRead = true }) {
  const { t } = useLanguage()
  const { open, setOpen, ref } = usePopover()
  const [items, setItems] = useState([])
  const [status, setStatus] = useState("idle") // idle | loading | ready | error

  const load = useCallback(async () => {
    if (!hospitalId || !canRead) return
    setStatus("loading")
    try {
      const data = await api.notifications.list(hospitalId)
      setItems(toList(data))
      setStatus("ready")
    } catch {
      setStatus("error")
    }
  }, [hospitalId, canRead])

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
            {!canRead && <p className="px-4 py-8 text-center text-[13px] text-ink-500">No notifications for your role.</p>}
            {canRead && !hospitalId && <p className="px-4 py-8 text-center text-[13px] text-ink-500">Select a hospital to see notifications.</p>}
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

function GuestSignIn() {
  return (
    <div className="flex items-center gap-1.5">
      <Link
        to="/patient-login"
        className="hidden h-9 items-center rounded-lg border border-line-strong bg-white px-3 text-[13px] font-medium text-ink-800 hover:bg-ink-50 sm:inline-flex"
      >
        Patient sign in
      </Link>
      <Link
        to="/staff-login"
        className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-brand-600 px-3 text-[13px] font-medium text-white hover:bg-brand-700"
      >
        <LogIn size={15} aria-hidden="true" /> Staff sign in
      </Link>
    </div>
  )
}

/** Roles from the server that this staff user may switch between. */
function useSwitchableRoles() {
  const { activeRoleName, roles } = useRole()
  const { isStaff, user } = useAuth()
  if (!isStaff) return []
  const backendRoles = user?.user?.roles || user?.roles || []
  return (roles || []).filter((role) => {
    if (!backendRoles.length) return role.name === activeRoleName
    return backendRoles.some(
      (item) => String(item).toLowerCase() === role.name.toLowerCase() || (item === "Reception" && role.name === "Receptionist"),
    )
  })
}

const menuItem = "flex w-full items-center gap-2 px-4 py-1.5 text-left text-[13px] text-ink-700 hover:bg-ink-50"

/* ---------------- Language switch (English / हिंदी) ---------------- */
function LanguageToggle() {
  const { language, setLanguage } = useLanguage()
  return (
    <div className="flex rounded-lg bg-ink-100 p-0.5" role="radiogroup" aria-label="Interface language">
      {LANGUAGES.map((lang) => (
        <button
          key={lang.id}
          type="button"
          role="radio"
          aria-checked={language === lang.id}
          aria-label={lang.name}
          title={lang.name}
          onClick={() => setLanguage(lang.id)}
          className={`rounded-md px-2.5 py-1 text-xs font-semibold ${
            language === lang.id ? "bg-white text-brand-700 shadow-sm" : "text-ink-600 hover:text-ink-900"
          }`}
        >
          {lang.label}
        </button>
      ))}
    </div>
  )
}

/* ---------------- Profile menu (role, settings, sign out) ---------------- */
export function UserMenu() {
  const navigate = useNavigate()
  const { open, setOpen, ref } = usePopover()
  const { activeRoleName, switchRole } = useRole()
  const { isStaff, user, logout, isLoggedIn, patient } = useAuth()
  const { language, t } = useLanguage()
  const switchableRoles = useSwitchableRoles()

  if (!isLoggedIn) return <GuestSignIn />

  const displayName = isStaff
    ? user?.username || user?.user?.username || activeRoleName || "User"
    : patient?.name || user?.username || "Patient"
  const roleLabel = isStaff ? activeRoleName || "Staff" : language === "hi" ? "मरीज़" : "Patient"

  const close = (action) => () => {
    setOpen(false)
    action()
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Profile menu for ${displayName}`}
        className="flex h-10 items-center gap-2.5 rounded-lg pl-1 pr-2 hover:bg-ink-100"
      >
        <Avatar name={displayName} size="sm" />
        <span className="hidden text-left leading-tight md:block">
          <span className="block max-w-[8rem] truncate text-[13px] font-semibold text-ink-900">{displayName}</span>
          <span className="block max-w-[8rem] truncate text-[11.5px] text-ink-500">{roleLabel}</span>
        </span>
        <ChevronDown size={15} className="hidden text-ink-400 md:block" aria-hidden="true" />
      </button>

      {open && (
        <div className={`${popoverPanel} w-64`} role="menu">
          <div className="flex items-center gap-3 border-b border-line px-4 py-3">
            <Avatar name={displayName} />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink-900">{displayName}</p>
              <p className="truncate text-xs text-ink-500">{isStaff ? `Acting as ${roleLabel}` : roleLabel}</p>
            </div>
          </div>

          {switchableRoles.length > 1 && (
            <div className="border-b border-line py-1.5">
              <p className="px-4 pb-1 pt-1 text-[11px] font-semibold uppercase tracking-wide text-ink-400">Switch role</p>
              {switchableRoles.map((role) => (
                <button
                  key={role.id}
                  type="button"
                  role="menuitemradio"
                  aria-checked={role.name === activeRoleName}
                  onClick={close(() => switchRole(role.name))}
                  className={menuItem}
                >
                  <UserCog size={15} className="text-ink-400" aria-hidden="true" />
                  <span className="flex-1">{role.name}</span>
                  {role.name === activeRoleName && <Check size={15} className="text-brand-600" aria-hidden="true" />}
                </button>
              ))}
            </div>
          )}

          <div className="py-1.5">
            {isStaff && (
              <button type="button" role="menuitem" onClick={close(() => navigate("/settings"))} className={menuItem}>
                <Settings size={15} className="text-ink-400" aria-hidden="true" />
                {t("Settings")}
              </button>
            )}
            <button
              type="button"
              role="menuitem"
              onClick={close(() => {
                logout()
                navigate("/")
              })}
              className="flex w-full items-center gap-2 px-4 py-1.5 text-left text-[13px] text-red-700 hover:bg-red-50"
            >
              <LogOut size={15} aria-hidden="true" />
              {t("Logout")}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Language switch, bell, then profile avatar, at the right end of a header.
 * @param {{ hospitalId?: string|number }} props
 */
export function HeaderActions({ hospitalId }) {
  const { isLoggedIn, isStaff } = useAuth()
  const { activeRoleName } = useRole()
  const canRead = !isStaff || NOTIFICATION_ROLES.has(activeRoleName)
  return (
    <div className="flex items-center gap-1 sm:gap-2">
      <LanguageToggle />
      {isLoggedIn && <NotificationsMenu hospitalId={hospitalId} canRead={canRead} />}
      {isLoggedIn && <div className="mx-1 hidden h-6 w-px bg-line sm:block" aria-hidden="true" />}
      <UserMenu />
    </div>
  )
}
