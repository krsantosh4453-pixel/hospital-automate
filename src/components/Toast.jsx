import { createContext, useContext, useState, useCallback } from "react"

const ToastContext = createContext(null)

const TOAST_TYPES = {
  success: { icon: "✅", bg: "bg-green-50", border: "border-green-200", text: "text-green-700" },
  error: { icon: "❌", bg: "bg-red-50", border: "border-red-200", text: "text-red-700" },
  warning: { icon: "⚠️", bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-700" },
  info: { icon: "ℹ️", bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700" },
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
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none" role="region" aria-live="polite">
        {toasts.map((toast) => {
          const style = TOAST_TYPES[toast.type] || TOAST_TYPES.info
          return (
            <div
              key={toast.id}
              className={`${style.bg} ${style.border} ${style.text} border rounded-xl shadow-lg p-4 flex items-center gap-3 min-w-[280px] max-w-md pointer-events-auto animate-slide-in`}
              role="alert"
            >
              <span className="text-lg flex-shrink-0">{style.icon}</span>
              <p className="text-sm font-medium flex-1">{toast.message}</p>
              <button
                onClick={() => hideToast(toast.id)}
                className="text-current opacity-50 hover:opacity-100 transition flex-shrink-0"
                aria-label="Dismiss"
              >
                ✕
              </button>
            </div>
          )
        })}
      </div>
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
  const style = TOAST_TYPES

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none" role="region" aria-live="polite">
      {toasts.map((toast) => {
        const s = style[toast.type] || style.info
        return (
          <div
            key={toast.id}
            className={`${s.bg} ${s.border} ${s.text} border rounded-xl shadow-lg p-4 flex items-center gap-3 min-w-[280px] max-w-md pointer-events-auto animate-slide-in`}
            role="alert"
          >
            <span className="text-lg flex-shrink-0">{s.icon}</span>
            <p className="text-sm font-medium flex-1">{toast.message}</p>
            <button
              onClick={() => hideToast(toast.id)}
              className="text-current opacity-50 hover:opacity-100 transition flex-shrink-0"
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
        )
      })}
    </div>
  )
}