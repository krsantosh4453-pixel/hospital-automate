import { useEffect } from "react"
import { Outlet, useLocation } from "react-router-dom"
import Navbar from "../components/Navbar"
import Sidebar from "../components/Sidebar"
import { useSidebar } from "../assets/context/SidebarContext.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { findNavItem } from "../config/navigation.js"

function Layout() {
  const { isSidebarOpen } = useSidebar()
  const { t } = useLanguage()
  const location = useLocation()

  // Keep the browser tab title in step with the current module.
  useEffect(() => {
    const match = findNavItem(location.pathname)
    document.title = match ? `${t(match.item.label)} · HMS` : "HMS — Hospital Management"
  }, [location.pathname, t])

  return (
    <div className="min-h-screen bg-canvas">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-[80] focus:rounded-lg focus:bg-brand-700 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white"
      >
        Skip to main content
      </a>

      <Sidebar />

      <div className={`flex min-h-screen flex-col transition-[padding] duration-200 ${isSidebarOpen ? "lg:pl-64" : "lg:pl-[72px]"}`}>
        <Navbar />
        <main id="main-content" tabIndex={-1} className="flex-1 px-4 py-5 outline-none sm:px-6 sm:py-6 lg:px-8">
          <div className="mx-auto w-full max-w-[1600px] min-w-0">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout
