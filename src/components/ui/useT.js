import { useLanguage } from "../../assets/context/LanguageContext.jsx"

/**
 * Translator for interface text in shared components (A17): strings go through
 * the language dictionary, anything else (elements, numbers) passes through.
 * Unknown strings stay in English.
 * @returns {(value: unknown) => unknown}
 */
export function useT() {
  const { t } = useLanguage()
  return (value) => (typeof value === "string" ? t(value) : value)
}
