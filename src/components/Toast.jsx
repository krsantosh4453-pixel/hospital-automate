import { createContext, useContext, useState, useCallback } from "react"
import { CircleAlert, TriangleAlert, CircleCheck, Info, X } from "lucide-react"

const ToastContext = createContext(null)

const TOAST_TYPES = {
  success: { icon: CircleCheck, accent: "text-green-600", bar: "bg-green-500" },
  error: { icon: CircleAlert, accent: "text-red-600", bar: "bg-red-500" },
  warning: { icon: TriangleAlert, accent: "text-amber-600", bar: "bg-amber-500" },
  info: { icon: Info, accent: "text-brand-600", bar: "bg-brand-500" },
}

function ToastList({ toasts, hideToast }) {
  return (
    <div
      className="pointer-events-none fixed inset-x-4 bottom-4 z-[70] flex flex-col items-end gap-2 sm:inset-x-auto sm:right-4"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
    >
      {toasts.map((toast) => {
        const s = TOAST_TYPES[toast.type] || TOAST_TYPES.info
        const Icon = s.icon
        return (
          <div
            key={toast.id}
            className="pointer-events-auto relative flex w-full max-w-sm items-start gap-3 overflow-hidden rounded-xl border border-line bg-white py-3 pl-4 pr-3 shadow-lg animate-slide-in"
            role={toast.type === "error" ? "alert" : "status"}
          >
            <span className={`absolute inset-y-0 left-0 w-1 ${s.bar}`} aria-hidden="true" />
            <Icon size={18} className={`mt-0.5 shrink-0 ${s.accent}`} aria-hidden="true" />
            <p className="flex-1 text-sm font-medium leading-6 text-ink-800">{toast.message}</p>
            <button
              type="button"
              onClick={() => hideToast(toast.id)}
              className="rounded-md p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-700"
              aria-label="Dismiss notification"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        )
      })}
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const showToast = useCallback((message, type = "info", duration = 5000) => {
    const id = Date.now() + Math.random()
    const toast = { id, message, type, duration }
    setToasts(prev => [...prev, toast])

    if (duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id))
      }, duration)
    }

    return id
  }, [])

  const hideToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const success = useCallback((message, duration) => showToast(message, "success", duration), [showToast])
  const error = useCallback((message, duration) => showToast(message, "error", duration), [showToast])
  const warning = useCallback((message, duration) => showToast(message, "warning", duration), [showToast])
  const info = useCallback((message, duration) => showToast(message, "info", duration), [showToast])

  return (
    <ToastContext.Provider value={{ toasts, showToast, hideToast, success, error, warning, info }}>
      {children}
      <ToastList toasts={toasts} hideToast={hideToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error("useToast must be used within ToastProvider")
  }
  return context
}

export function ToastContainer() {
  const { toasts, hideToast } = useToast()
  return <ToastList toasts={toasts} hideToast={hideToast} />
}
