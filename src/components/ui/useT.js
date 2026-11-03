import { useLanguage } from "../../assets/context/LanguageContext.jsx"

/**
 * Translator for interface text in shared components (A17): strings go through
 * the language dictionary, anything else (elements, numbers) passes through.
 * Unknown strings stay in English.
 * Sentences with names or numbers use {placeholders}: tr("Signed in as {name}", { name }).
 * @returns {(value: unknown, vars?: Record<string, unknown>) => unknown}
 */
export function useT() {
  const { t } = useLanguage()
  return (value, vars) => (typeof value === "string" ? t(value, vars) : value)
}
