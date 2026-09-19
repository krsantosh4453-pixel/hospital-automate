import { createContext, useContext, useState, useEffect } from "react"

const SidebarContext = createContext(null)

export function SidebarProvider({ children }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    const saved = localStorage.getItem("sidebarOpen")
    return saved !== null ? saved === "true" : true
  })

  useEffect(() => {
    localStorage.setItem("sidebarOpen", String(isSidebarOpen))
  }, [isSidebarOpen])

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev)
  const openSidebar = () => setIsSidebarOpen(true)
  const closeSidebar = () => setIsSidebarOpen(false)

  return (
    <SidebarContext.Provider
      value={{
        isSidebarOpen,
        toggleSidebar,
        openSidebar,
        closeSidebar,
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
