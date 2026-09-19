import Navbar from "../components/Navbar"
import Sidebar from "../components/Sidebar"
import { Outlet } from "react-router-dom"
import { useSidebar } from "../assets/context/SidebarContext.jsx"

function Layout() {
  const { isSidebarOpen, toggleSidebar } = useSidebar()

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">

      {/* Fixed Top Header */}
      <Navbar />

      {/* Body Area */}
      <div className="flex pt-16 flex-1 relative">

        {/* Sidebar */}
        <Sidebar />

        {/* Floating Open Sidebar Pill (when sidebar is closed) */}
        {!isSidebarOpen && (
          <button
            type="button"
            onClick={toggleSidebar}
            className="fixed left-3 top-20 z-20 hidden md:flex items-center gap-2 px-3 py-1.5 bg-slate-900 text-white rounded-full text-xs font-medium shadow-md hover:bg-slate-800 transition cursor-pointer border border-slate-700"
            title="Open sidebar"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="3" />
              <line x1="9" y1="3" x2="9" y2="21" strokeWidth="2.5" />
            </svg>
            <span>Open sidebar</span>
          </button>
        )}

        {/* Main Content Area - Expands to full desktop size when sidebar is collapsed */}
        <main
          className={`flex-1 transition-all duration-300 ease-in-out p-4 sm:p-6 lg:p-8 min-h-[calc(100vh-4rem)] ${
            isSidebarOpen ? "lg:ml-64" : "ml-0"
          } w-full overflow-x-hidden`}
        >
          <div className="w-full max-w-[1680px] mx-auto">
            <Outlet />
          </div>
        </main>

      </div>

    </div>
  )
}

export default Layout