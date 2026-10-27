import { createContext, useContext, useState, useEffect, useCallback } from "react"

const SidebarContext = createContext(null)

/**
 * isSidebarOpen: desktop sidebar expanded (true) or collapsed to an icon rail
 * (false); remembered per browser. isMobileOpen: the off-canvas drawer on
 * screens narrower than lg; never remembered.
 */
export function SidebarProvider({ children }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    try {
      const saved = localStorage.getItem("sidebarOpen")
      return saved !== null ? saved === "true" : true
    } catch {
      return true
    }
  })
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem("sidebarOpen", String(isSidebarOpen))
    } catch {
      // storage unavailable (private mode); the preference just isn't kept
    }
  }, [isSidebarOpen])

  const toggleSidebar = useCallback(() => setIsSidebarOpen((prev) => !prev), [])
  const openSidebar = useCallback(() => setIsSidebarOpen(true), [])
  const closeSidebar = useCallback(() => setIsSidebarOpen(false), [])
  const openMobile = useCallback(() => setIsMobileOpen(true), [])
  const closeMobile = useCallback(() => setIsMobileOpen(false), [])

  return (
    <SidebarContext.Provider
      value={{
        isSidebarOpen,
        toggleSidebar,
        openSidebar,
        closeSidebar,
        isMobileOpen,
        openMobile,
        closeMobile,
      }}
    >
      {children}
    </SidebarContext.Provider>
  )
}

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (!context) {
    throw new Error("useSidebar must be used within SidebarProvider")
  }
  return context
}
