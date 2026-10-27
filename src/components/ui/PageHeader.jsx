import { Link } from "react-router-dom"
import { ChevronRight } from "lucide-react"

/**
 * Page title block used at the top of every staff and patient page.
 * breadcrumbs: [{ label, to? }] — the last item is the current page.
 */
function PageHeader({ title, description, breadcrumbs, actions, meta, className = "" }) {
  return (
    <header className={`mb-6 ${className}`}>
      {breadcrumbs?.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-2">
          <ol className="flex flex-wrap items-center gap-1 text-[13px] text-ink-500">
            {breadcrumbs.map((crumb, i) => {
              const last = i === breadcrumbs.length - 1
              return (
                <li key={`${crumb.label}-${i}`} className="flex items-center gap-1">
                  {crumb.to && !last ? (
                    <Link to={crumb.to} className="rounded hover:text-brand-700 hover:underline">
                      {crumb.label}
                    </Link>
                  ) : (
                    <span aria-current={last ? "page" : undefined} className={last ? "text-ink-700" : ""}>
                      {crumb.label}
                    </span>
                  )}
                  {!last && <ChevronRight size={14} className="text-ink-300" aria-hidden="true" />}
                </li>
              )
            })}
          </ol>
        </nav>
      )}
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h1 className="text-[22px] font-semibold leading-8 tracking-[-0.01em] text-ink-900 sm:text-2xl">
            {title}
          </h1>
          {description && <p className="mt-1 max-w-3xl text-sm leading-6 text-ink-500">{description}</p>}
          {meta && <div className="mt-2 flex flex-wrap items-center gap-2">{meta}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </header>
  )
}

export default PageHeader
