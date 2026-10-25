import { useId, useRef } from "react"

/**
 * Underline tabs with arrow-key navigation (WAI-ARIA tabs pattern).
 * tabs: [{ id, label, icon?, count? }]
 */
export function Tabs({ tabs, value, onChange, className = "", label = "Sections" }) {
  const baseId = useId()
  const refs = useRef({})

  const onKeyDown = (e, index) => {
    let next = null
    if (e.key === "ArrowRight") next = (index + 1) % tabs.length
    if (e.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length
    if (e.key === "Home") next = 0
    if (e.key === "End") next = tabs.length - 1
    if (next !== null) {
      e.preventDefault()
      const tab = tabs[next]
      onChange(tab.id)
      refs.current[tab.id]?.focus()
    }
  }

  return (
    <div className={`-mx-1 overflow-x-auto scrollbar-thin ${className}`}>
      <div role="tablist" aria-label={label} className="flex min-w-max gap-1 border-b border-line px-1">
        {tabs.map((tab, index) => {
          const active = tab.id === value
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              ref={(el) => {
                refs.current[tab.id] = el
              }}
              type="button"
              role="tab"
              id={`${baseId}-${tab.id}`}
              aria-selected={active}
              aria-disabled={tab.disabled || undefined}
              disabled={tab.disabled}
              tabIndex={active ? 0 : -1}
              onClick={() => onChange(tab.id)}
              onKeyDown={(e) => onKeyDown(e, index)}
              className={`relative -mb-px inline-flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:text-ink-300 disabled:hover:border-transparent ${
                active
                  ? "border-brand-600 text-brand-700"
                  : "border-transparent text-ink-500 hover:border-ink-300 hover:text-ink-800"
              }`}
            >
              {Icon && <Icon size={16} aria-hidden="true" />}
              {tab.label}
              {tab.count !== undefined && tab.count !== null && (
                <span
                  className={`rounded-full px-1.5 py-px text-[11px] font-semibold tabular-nums ${
                    active ? "bg-brand-100 text-brand-700" : "bg-ink-100 text-ink-600"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/** Compact pill switch for filters with few options. */
export function SegmentedControl({ options, value, onChange, className = "", label }) {
  return (
    <div role="radiogroup" aria-label={label} className={`inline-flex rounded-lg bg-ink-100 p-0.5 ${className}`}>
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={`rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors ${
              active ? "bg-white text-ink-900 shadow-sm" : "text-ink-600 hover:text-ink-900"
            }`}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

export default Tabs
