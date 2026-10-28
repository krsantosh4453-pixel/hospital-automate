import { Link, useLocation } from "react-router-dom"
import { ChevronRight } from "lucide-react"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { ShellBreadcrumbsContext, shellBreadcrumbsFor } from "./shellBreadcrumbsContext.js"

export function ShellBreadcrumbsProvider({ children }) {
  const { pathname } = useLocation()
  return (
    <ShellBreadcrumbsContext.Provider value={Boolean(shellBreadcrumbsFor(pathname))}>
      {children}
    </ShellBreadcrumbsContext.Provider>
  )
}

// Home › section › page for the current staff route (requirement A18).
// Section names are not pages, so only Home links; Home itself shows none.
// Routes outside the navigation keep the trail their PageHeader passes.
export default function Breadcrumbs() {
  const { pathname } = useLocation()
  const { t } = useLanguage()
  const match = shellBreadcrumbsFor(pathname)

  if (!match) return null

  const crumbs = [t(match.group.label), t(match.item.label)]

  return (
    <nav aria-label="Breadcrumb" className="mb-4">
      <ol className="flex flex-wrap items-center gap-1 text-sm text-ink-500">
        <li>
          <Link to="/" className="rounded hover:text-ink-900 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
            {t("Home")}
          </Link>
        </li>
        {crumbs.map((label, index) => {
          const isCurrent = index === crumbs.length - 1
          return (
            <li key={index} className="flex items-center gap-1">
              <ChevronRight aria-hidden="true" className="h-3.5 w-3.5 text-ink-400" />
              <span aria-current={isCurrent ? "page" : undefined} className={isCurrent ? "font-medium text-ink-800" : undefined}>
                {label}
              </span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
