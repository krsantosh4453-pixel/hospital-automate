import { createContext, useContext } from "react"
import { findNavItem } from "../config/navigation.js"

// True while the staff shell is drawing the breadcrumb bar, so PageHeader
// leaves out its own trail instead of showing a second one.
export const ShellBreadcrumbsContext = createContext(false)

export const useShellBreadcrumbs = () => useContext(ShellBreadcrumbsContext)

/** The route the shell bar covers: a navigation page other than Home. */
export function shellBreadcrumbsFor(pathname) {
  return pathname === "/" ? null : findNavItem(pathname)
}
