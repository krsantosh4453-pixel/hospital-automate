export function LoadingSpinner({ size = "md", className = "" }) {
  const sizeClasses = {
    sm: "w-6 h-6 border-3",
    md: "w-10 h-10 border-4",
    lg: "w-14 h-14 border-4",
    xl: "w-16 h-16 border-4",
  }

  return (
    <div className={`${sizeClasses[size]} border-blue-600 border-t-transparent rounded-full animate-spin ${className}`} role="status" aria-label="Loading">
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function LoadingOverlay({ message = "Loading...", className = "" }) {
  return (
    <div className={`fixed inset-0 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center z-50 ${className}`} role="status" aria-live="polite">
      <LoadingSpinner size="lg" />
      <p className="mt-4 text-gray-600 font-medium">{message}</p>
    </div>
  )
}

export function PageLoading({ message = "Loading..." }) {
  return (
    <div className="min-h-[400px] flex items-center justify-center">
      <div className="text-center">
        <LoadingSpinner size="xl" className="mx-auto" />
        <p className="mt-4 text-gray-500">{message}</p>
      </div>
    </div>
  )
}

export function ButtonLoading({ children, loading, className = "" }) {
  return (
    <button
      type="button"
      disabled={loading}
      className={`inline-flex items-center justify-center gap-2 ${className} ${loading ? "opacity-75 cursor-wait" : ""}`}
    >
      {loading && <LoadingSpinner size="sm" />}
      {children}
    </button>
  )
}

export function Skeleton({ className = "", variant = "text" }) {
  const baseClass = "animate-pulse bg-gray-200 rounded"
  const variants = {
    text: "h-4 w-full",
    title: "h-6 w-3/4",
    card: "h-32 w-full",
    avatar: "h-12 w-12 rounded-full",
    button: "h-10 w-24 rounded-lg",
    tableRow: "h-12 w-full",
  }

  return <div className={`${baseClass} ${variants[variant]} ${className}`} />
}

export function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 space-y-3">
      <Skeleton variant="title" />
      <Skeleton variant="text" />
      <Skeleton variant="text" className="w-1/2" />
    </div>
  )
}

export function SkeletonTable({ rows = 5, columns = 4 }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="p-5 border-b border-gray-100 bg-gray-50">
        <div className="grid grid-cols-12 gap-4">
          {[...Array(columns)].map((_, i) => (
            <Skeleton variant="text" key={i} className="col-span-3" />
          ))}
        </div>
      </div>
      <div className="divide-y divide-gray-100">
        {[...Array(rows)].map((_, row) => (
          <div key={row} className="p-5">
            <div className="grid grid-cols-12 gap-4">
              {[...Array(columns)].map((_, i) => (
                <Skeleton variant="text" key={i} className="col-span-3" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}