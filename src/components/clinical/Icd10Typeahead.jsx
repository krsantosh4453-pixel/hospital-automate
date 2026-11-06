import { useEffect, useId, useRef, useState } from "react"
import api from "../../services/api.js"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

const MIN_QUERY_LENGTH = 2
const DEBOUNCE_MS = 250

/**
 * Diagnosis text box that suggests ICD-10 codes as the clinician types.
 * Free text is still allowed; picking a suggestion calls `onSelect` with
 * `{ code, description }`. Extra props (id, aria-describedby, required) go
 * to the input, so it works inside <Field>.
 */
export default function Icd10Typeahead({ value, onChange, onSelect, className = "", ...inputProps }) {
  const { t } = useLanguage()
  const listId = useId()
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  // Typing opens the list; picking a suggestion must not reopen it.
  const searchOnChange = useRef(false)

  useEffect(() => {
    const query = (value || "").trim()
    if (!searchOnChange.current || query.length < MIN_QUERY_LENGTH) {
      setResults([])
      return undefined
    }
    let stale = false
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await api.terminology.icd10Search(query)
        if (stale) return
        setResults(data?.results || [])
        setFailed(false)
        setOpen(true)
        setActive(-1)
      } catch {
        if (!stale) setFailed(true)
      } finally {
        if (!stale) setLoading(false)
      }
    }, DEBOUNCE_MS)
    return () => {
      stale = true
      clearTimeout(timer)
    }
  }, [value])

  const pick = (row) => {
    searchOnChange.current = false
    setOpen(false)
    setResults([])
    onSelect(row)
  }

  const onKeyDown = (event) => {
    if (!open || results.length === 0) return
    if (event.key === "ArrowDown") {
      event.preventDefault()
      setActive((i) => (i + 1) % results.length)
    } else if (event.key === "ArrowUp") {
      event.preventDefault()
      setActive((i) => (i <= 0 ? results.length - 1 : i - 1))
    } else if (event.key === "Enter" && active >= 0) {
      event.preventDefault()
      pick(results[active])
    } else if (event.key === "Escape") {
      setOpen(false)
    }
  }

  const showList = open && results.length > 0
  return (
    <div className="relative">
      <input
        {...inputProps}
        type="text"
        role="combobox"
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={showList && active >= 0 ? `${listId}-${active}` : undefined}
        className={`hms-input w-full ${className}`}
        value={value}
        onChange={(event) => {
          searchOnChange.current = true
          onChange(event.target.value)
        }}
        onKeyDown={onKeyDown}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onFocus={() => results.length > 0 && setOpen(true)}
      />
      {loading && <span className="absolute right-3 top-2.5 text-xs text-ink-400" aria-hidden="true">…</span>}
      {failed && <p className="mt-1 text-xs text-ink-500">{t("ICD-10 suggestions are unavailable; you can still type the diagnosis.")}</p>}
      <ul
        id={listId}
        role="listbox"
        aria-label={t("ICD-10 suggestions")}
        className={`absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-lg border border-line bg-white py-1 shadow-lg ${showList ? "" : "hidden"}`}
      >
        {results.map((row, index) => (
          <li
            key={row.code}
            id={`${listId}-${index}`}
            role="option"
            aria-selected={index === active}
            onMouseDown={(event) => {
              event.preventDefault()
              pick(row)
            }}
            className={`cursor-pointer px-3 py-2 text-sm ${index === active ? "bg-brand-50 text-brand-800" : "text-ink-800 hover:bg-ink-50"}`}
          >
            <span className="mr-2 font-mono text-xs font-semibold text-ink-600">{row.code}</span>
            {row.description}
          </li>
        ))}
      </ul>
    </div>
  )
}
