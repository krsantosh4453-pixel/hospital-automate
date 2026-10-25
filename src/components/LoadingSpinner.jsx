export function LoadingSpinner({ size = "md", className = "" }) {
  const sizeClasses = {
    sm: "w-5 h-5 border-2",
    md: "w-8 h-8 border-[3px]",
    lg: "w-10 h-10 border-[3px]",
    xl: "w-12 h-12 border-4",
  }

  return (
    <div className={`${sizeClasses[size]} border-brand-200 border-t-brand-600 rounded-full animate-spin ${className}`} role="status" aria-label="Loading">
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function LoadingOverlay({ message = "Loading...", className = "" }) {
  return (
    <div className={`fixed inset-0 bg-white/85 flex flex-col items-center justify-center z-50 ${className}`} role="status" aria-live="polite">
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
  const baseClass = "skeleton"
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
    <div className="bg-white rounded-2xl border border-line p-5 space-y-3">
      <Skeleton variant="title" />
      <Skeleton variant="text" />
      <Skeleton variant="text" className="w-1/2" />
    </div>
  )
}

export function SkeletonTable({ rows = 5, columns = 4 }) {
  return (
    <div className="bg-white rounded-2xl border border-line overflow-hidden">
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