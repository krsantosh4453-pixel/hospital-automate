import { CircleAlert, TriangleAlert, CircleCheck, Info, Inbox, Lock, X } from "lucide-react"

const ALERT_TONES = {
  info: { icon: Info, cls: "border-brand-200 bg-brand-50 text-brand-900", iconCls: "text-brand-600" },
  success: { icon: CircleCheck, cls: "border-green-200 bg-green-50 text-green-800", iconCls: "text-green-600" },
  warning: { icon: TriangleAlert, cls: "border-amber-200 bg-amber-50 text-amber-800", iconCls: "text-amber-600" },
  danger: { icon: CircleAlert, cls: "border-red-200 bg-red-50 text-red-800", iconCls: "text-red-600" },
}

/** Inline message for page-level info, warnings and errors. */
export function Alert({ tone = "info", title, children, onDismiss, action, className = "" }) {
  const t = ALERT_TONES[tone] || ALERT_TONES.info
  const Icon = t.icon
  return (
    <div
      role={tone === "danger" || tone === "warning" ? "alert" : "status"}
      className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${t.cls} ${className}`}
    >
      <Icon size={18} className={`mt-0.5 shrink-0 ${t.iconCls}`} aria-hidden="true" />
      <div className="min-w-0 flex-1 leading-6">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? "opacity-90" : ""}>{children}</div>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="-mr-1 rounded-md p-1 opacity-60 hover:bg-black/5 hover:opacity-100"
          aria-label="Dismiss"
        >
          <X size={16} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}

/** Shown when a list or section has no records. Never shows invented data. */
export function EmptyState({ icon: Icon = Inbox, title, description, action, compact = false, className = "" }) {
  return (
    <div className={`flex flex-col items-center justify-center text-center ${compact ? "px-4 py-8" : "px-6 py-14"} ${className}`}>
      <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-ink-100 text-ink-500">
        <Icon size={22} aria-hidden="true" />
      </span>
      <p className="mt-3 text-sm font-semibold text-ink-800">{title}</p>
      {description && <p className="mt-1 max-w-sm text-[13px] leading-5 text-ink-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ title = "Something went wrong", message, onRetry, className = "" }) {
  return (
    <EmptyState
      icon={CircleAlert}
      title={title}
      description={message}
      className={className}
      action={
        onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex h-9 items-center rounded-lg border border-line-strong bg-white px-3.5 text-sm font-medium text-ink-800 hover:bg-ink-50"
          >
            Try again
          </button>
        )
      }
    />
  )
}

export function PermissionDenied({ message = "Your role does not have access to this page in the selected hospital." }) {
  return <EmptyState icon={Lock} title="You don't have access" description={message} />
}

export function SkeletonRows({ rows = 5, className = "" }) {
  return (
    <div className={`space-y-3 p-5 ${className}`} role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4">
          <div className="skeleton h-9 w-9 rounded-full" />
          <div className="flex-1 space-y-2">
            <div className="skeleton h-3.5" style={{ width: `${60 - (i % 3) * 12}%` }} />
            <div className="skeleton h-3" style={{ width: `${35 - (i % 2) * 10}%` }} />
          </div>
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  )
}
