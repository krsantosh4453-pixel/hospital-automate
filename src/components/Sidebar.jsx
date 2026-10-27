import { useEffect } from "react"
import { Link, NavLink, useLocation } from "react-router-dom"
import { LogIn, PanelLeftClose, PanelLeftOpen, X } from "lucide-react"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { useSidebar } from "../assets/context/SidebarContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { guestStaffNav, visibleStaffNav } from "../config/navigation.js"

export function BrandMark({ compact = false, inverted = true }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${inverted ? "bg-brand-400/15 ring-1 ring-brand-300/30" : "bg-brand-600"}`}
        aria-hidden="true"
      >
        {/* HMS mark: a cross formed by two rounded bars with a pulse notch */}
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none">
          <rect x="9.25" y="3" width="5.5" height="18" rx="2.2" fill={inverted ? "#7ec4ca" : "#ffffff"} />
          <rect x="3" y="9.25" width="18" height="5.5" rx="2.2" fill={inverted ? "#d6eeef" : "#d6eeef"} />
          <path d="M6.5 12h3l1.2-2.2 2 4.4 1.3-2.2h3.5" stroke={inverted ? "#0b272d" : "#186d79"} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      {!compact && (
        <span className="min-w-0 leading-tight">
          <span className={`block text-[15px] font-semibold tracking-tight ${inverted ? "text-white" : "text-ink-900"}`}>HMS</span>
          <span className={`block text-[11px] ${inverted ? "text-brand-200/70" : "text-ink-500"}`}>Hospital Management</span>
        </span>
      )}
    </div>
  )
}

function NavItems({ groups, collapsed, t, onNavigate }) {
  return (
    <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 py-3 scrollbar-thin [scrollbar-color:rgb(255_255_255/0.15)_transparent]">
      {groups.map((group, gi) => (
        <div key={group.id} className={gi > 0 ? "mt-4" : ""}>
          {collapsed ? (
            gi > 0 && <div className="mx-3 mb-3 border-t border-white/10" aria-hidden="true" />
          ) : (
            group.id !== "overview" && (
              <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-brand-200/50">
                {t(group.label)}
              </p>
            )
          )}
          <ul className="space-y-0.5">
            {group.items.map((item) => {
              const Icon = item.icon
              return (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.end}
                    onClick={onNavigate}
                    title={collapsed ? t(item.label) : undefined}
                    className={({ isActive }) =>
                      `group relative flex items-center gap-3 rounded-lg py-2 text-[13.5px] font-medium transition-colors ${
                        collapsed ? "justify-center px-0" : "px-3"
                      } ${
                        isActive
                          ? "bg-white/[0.09] text-white"
                          : "text-ink-300 hover:bg-white/[0.05] hover:text-white"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-brand-300" aria-hidden="true" />
                        )}
                        <Icon
                          size={18}
                          strokeWidth={isActive ? 2.1 : 1.8}
                          className={isActive ? "text-brand-200" : "text-ink-400 group-hover:text-ink-200"}
                          aria-hidden="true"
                        />
                        {collapsed ? <span className="sr-only">{t(item.label)}</span> : <span className="truncate">{t(item.label)}</span>}
                      </>
                    )}
                  </NavLink>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </nav>
  )
}

function GuestFooter({ collapsed }) {
  return (
    <div className={`border-t border-white/10 ${collapsed ? "flex justify-center py-3" : "px-4 py-3"}`}>
      <Link
        to="/staff-login"
        title={collapsed ? "Sign in" : undefined}
        className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-medium text-ink-200 hover:bg-white/[0.05] hover:text-white"
      >
        <LogIn size={15} aria-hidden="true" />
        {collapsed ? <span className="sr-only">Sign in</span> : <span>Not signed in · Sign in</span>}
      </Link>
    </div>
  )
}

function RoleFooter({ collapsed, activeRoleName, activeRole, isGuest }) {
  if (isGuest) return <GuestFooter collapsed={collapsed} />
  if (collapsed) {
    return (
      <div className="flex justify-center border-t border-white/10 py-3" title={`Role: ${activeRoleName}`}>
        <span className="h-2 w-2 rounded-full bg-green-500" aria-hidden="true" />
        <span className="sr-only">Role: {activeRoleName}</span>
      </div>
    )
  }
  return (
    <div className="border-t border-white/10 px-4 py-3">
      <p className="flex items-center gap-2 text-xs font-medium text-ink-200">
        <span className="h-1.5 w-1.5 rounded-full bg-green-500" aria-hidden="true" />
        <span className="truncate">Signed in as {activeRoleName}</span>
      </p>
      {activeRole?.description && <p className="mt-0.5 truncate pl-3.5 text-[11px] text-ink-400">{activeRole.description}</p>}
    </div>
  )
}

function Sidebar() {
  const location = useLocation()
  const { isSidebarOpen, toggleSidebar, isMobileOpen, closeMobile } = useSidebar()
  const { canView, activeRole, activeRoleName } = useRole()
  const { isStaff } = useAuth()
  const { t } = useLanguage()
  // Visitors see the full menu; each page asks them to sign in.
  const groups = isStaff ? visibleStaffNav(canView) : guestStaffNav()
  const collapsed = !isSidebarOpen

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    closeMobile()
  }, [location.pathname, closeMobile])

  // Escape closes the mobile drawer.
  useEffect(() => {
    if (!isMobileOpen) return undefined
    const onKey = (e) => e.key === "Escape" && closeMobile()
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [isMobileOpen, closeMobile])

  return (
    <>
      {/* Desktop: full sidebar or icon rail */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 hidden flex-col bg-brand-950 transition-[width] duration-200 lg:flex ${
          collapsed ? "w-[72px]" : "w-64"
        }`}
      >
        <div className={`flex h-16 items-center border-b border-white/10 ${collapsed ? "justify-center px-2" : "justify-between px-4"}`}>
          <BrandMark compact={collapsed} />
          {!collapsed && (
            <button
              type="button"
              onClick={toggleSidebar}
              className="rounded-lg p-1.5 text-ink-400 hover:bg-white/10 hover:text-white"
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
            >
              <PanelLeftClose size={18} aria-hidden="true" />
            </button>
          )}
        </div>
        {collapsed && (
          <div className="flex justify-center pt-3">
            <button
              type="button"
              onClick={toggleSidebar}
              className="rounded-lg p-2 text-ink-400 hover:bg-white/10 hover:text-white"
              aria-label="Expand sidebar"
              title="Expand sidebar"
            >
              <PanelLeftOpen size={18} aria-hidden="true" />
            </button>
          </div>
        )}
        <NavItems groups={groups} collapsed={collapsed} t={t} />
        <RoleFooter collapsed={collapsed} activeRoleName={activeRoleName} activeRole={activeRole} isGuest={!isStaff} />
      </aside>

      {/* Mobile / tablet: off-canvas drawer */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-ink-950/50 animate-fade-in" onClick={closeMobile} aria-hidden="true" />
          <aside className="absolute inset-y-0 left-0 flex w-[min(18rem,85vw)] flex-col bg-brand-950 shadow-2xl animate-fade-in">
            <div className="flex h-16 items-center justify-between border-b border-white/10 px-4">
              <BrandMark />
              <button
                type="button"
                onClick={closeMobile}
                className="rounded-lg p-2 text-ink-300 hover:bg-white/10 hover:text-white"
                aria-label="Close navigation"
              >
                <X size={20} aria-hidden="true" />
              </button>
            </div>
            <NavItems groups={groups} collapsed={false} t={t} onNavigate={closeMobile} />
            <RoleFooter collapsed={false} activeRoleName={activeRoleName} activeRole={activeRole} isGuest={!isStaff} />
          </aside>
        </div>
      )}
    </>
  )
}

export default Sidebar
