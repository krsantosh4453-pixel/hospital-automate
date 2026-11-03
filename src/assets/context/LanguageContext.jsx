import { createContext, useContext } from "react"

// The Language context and its hook. LanguageProvider (./LanguageProvider.jsx) supplies
// the value; they live in separate files so React Fast Refresh can hot-reload it.

/** "Signed in as {name}" + { name: "Admin" } → "Signed in as Admin"; unknown names stay as written. */
export function fillPlaceholders(template, vars) {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (match, key) => (key in vars ? String(vars[key]) : match))
}

export const LanguageContext = createContext({
  language: "en",
  setLanguage: () => {},
  t: (text, vars) => fillPlaceholders(text, vars),
})

export function useLanguage() {
  return useContext(LanguageContext)
}
