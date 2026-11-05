import { useLanguage } from "../assets/context/LanguageContext.jsx"

// One audit row's details, readable: an edit shows each field's old and new
// value, a removal its reason and the values the record had before.

const show = (value) => (value === null || value === undefined || value === "" ? "—" : String(value))

function parse(details) {
  if (!details) return null
  try {
    const parsed = JSON.parse(details)
    return parsed && typeof parsed === "object" ? parsed : { text: String(parsed) }
  } catch {
    return { text: details }
  }
}

export default function AuditDetails({ details }) {
  const { t } = useLanguage()
  const parsed = parse(details)
  if (!parsed) return <span className="text-ink-400">—</span>

  const { changes, reason, before, text, ...rest } = parsed
  const changed = changes && Object.entries(changes)
  const other = Object.keys(rest).length ? JSON.stringify(rest) : ""

  return (
    <div className="space-y-1 text-[13px] text-ink-600">
      {reason && <p><span className="font-medium text-ink-900">{t("Reason")}:</span> {reason}</p>}
      {changed?.length > 0 && (
        <ul className="space-y-0.5">
          {changed.map(([field, change]) => (
            <li key={field}>
              <span className="font-medium text-ink-900">{field}</span>: <s className="text-ink-400">{show(change?.from)}</s> → {show(change?.to)}
            </li>
          ))}
        </ul>
      )}
      {before && (
        <details>
          <summary className="cursor-pointer text-ink-700">{t("Values before")}</summary>
          <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3">
            {Object.entries(before).map(([field, value]) => (
              <div key={field} className="contents">
                <dt className="text-ink-500">{field}</dt>
                <dd className="break-words">{show(value)}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
      {(text || other) && <p className="max-w-xs truncate" title={text || other}>{text || other}</p>}
    </div>
  )
}
