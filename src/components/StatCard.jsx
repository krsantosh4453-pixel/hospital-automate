/**
 * Legacy stat card API (title/value/icon/color/subtitle). `icon` may be a
 * lucide component or a node. Kept for existing callers; new code uses
 * StatTile from components/ui.
 */
function StatCard({ title, value, icon: Icon, color = "bg-brand-50 text-brand-700", subtitle }) {
  const shown = value === null || value === undefined || value === "" ? "—" : value
  const iconNode = typeof Icon === "function" || (Icon && Icon.$$typeof && Icon.render)
    ? <Icon size={20} aria-hidden="true" />
    : Icon

  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className="flex items-start gap-3.5">
        {iconNode && (
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${color}`}>
            {iconNode}
          </span>
        )}
        <div className="min-w-0">
          <p className="truncate text-[13px] font-medium text-ink-500">{title}</p>
          <p className="mt-0.5 text-2xl font-semibold leading-8 tracking-tight text-ink-900 tabular-nums">{shown}</p>
          {subtitle && <p className="mt-0.5 text-xs text-ink-500">{subtitle}</p>}
        </div>
      </div>
    </div>
  )
}

export default StatCard
