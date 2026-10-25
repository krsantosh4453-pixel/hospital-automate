import { Search, X } from "lucide-react"

/** Key figure with label. `value` of null/undefined renders "—", never a made-up number. */
export function StatTile({ label, value, icon: Icon, tone = "brand", hint, onClick, className = "" }) {
  const toneCls = {
    brand: "bg-brand-50 text-brand-700",
    accent: "bg-accent-50 text-accent-700",
    success: "bg-green-50 text-green-700",
    warning: "bg-amber-50 text-amber-700",
    danger: "bg-red-50 text-red-700",
    neutral: "bg-ink-100 text-ink-600",
  }[tone]
  const Tag = onClick ? "button" : "div"
  const shown = value === null || value === undefined || value === "" ? "—" : value
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={`flex w-full items-start gap-3.5 rounded-2xl border border-line bg-surface p-4 text-left ${onClick ? "transition-colors hover:border-brand-300 hover:bg-brand-50/30" : ""} ${className}`}
    >
      {Icon && (
        <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${toneCls}`}>
          <Icon size={20} aria-hidden="true" />
        </span>
      )}
      <span className="min-w-0">
        <span className="block text-[13px] font-medium text-ink-500">{label}</span>
        <span className="mt-0.5 block text-2xl font-semibold leading-8 tracking-tight text-ink-900 tabular-nums">
          {shown}
        </span>
        {hint && <span className="mt-0.5 block text-xs text-ink-500">{hint}</span>}
      </span>
    </Tag>
  )
}

/** Search box with a clear button. */
export function SearchInput({ value, onChange, placeholder = "Search…", className = "", label = "Search", ...rest }) {
  return (
    <div className={`relative ${className}`}>
      <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" aria-hidden="true" />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={label}
        className="hms-input w-full pl-9 pr-8 [&::-webkit-search-cancel-button]:hidden"
        {...rest}
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-700"
          aria-label="Clear search"
        >
          <X size={14} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}

/** Toolbar above a table: search/filters on the left, actions on the right. */
export function Toolbar({ children, actions, className = "" }) {
  return (
    <div className={`flex flex-col gap-3 border-b border-line px-4 py-3 sm:flex-row sm:items-center sm:justify-between ${className}`}>
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{children}</div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

/** Scroll container for wide tables; the table keeps its density on small screens. */
export function TableWrap({ children, className = "", maxHeight }) {
  return (
    <div className={`overflow-x-auto scrollbar-thin ${className}`} style={maxHeight ? { maxHeight, overflowY: "auto" } : undefined}>
      {children}
    </div>
  )
}

/** Avatar with initials, used for patients and staff. */
export function Avatar({ name, size = "md", tone = "brand" }) {
  const initials = String(name || "?")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p.charAt(0).toUpperCase())
    .join("")
  const sizes = { sm: "h-7 w-7 text-[11px]", md: "h-9 w-9 text-xs", lg: "h-12 w-12 text-sm" }
  const tones = {
    brand: "bg-brand-100 text-brand-800",
    accent: "bg-accent-100 text-accent-800",
    neutral: "bg-ink-100 text-ink-700",
  }
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-semibold ${sizes[size]} ${tones[tone] || tones.brand}`}
      aria-hidden="true"
    >
      {initials || "?"}
    </span>
  )
}

/** Label/value list for detail panels. */
export function DescriptionList({ items, columns = 2, className = "" }) {
  return (
    <dl className={`grid grid-cols-1 gap-x-6 gap-y-4 ${columns === 3 ? "sm:grid-cols-3" : columns === 1 ? "" : "sm:grid-cols-2"} ${className}`}>
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-xs font-medium text-ink-500">{item.label}</dt>
          <dd className="mt-0.5 break-words text-sm text-ink-900">
            {item.value === null || item.value === undefined || item.value === "" ? (
              <span className="text-ink-400">Not recorded</span>
            ) : (
              item.value
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}
