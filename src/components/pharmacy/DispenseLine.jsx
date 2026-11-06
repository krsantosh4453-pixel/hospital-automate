import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { remainingOf, substituteBatches, usableBatches } from "../../utils/dispenseBatches.js"

const batchLabel = (batch) => `${batch.batch || "No batch no."} · Exp ${batch.expiry || "—"} · ${batch.stock} in stock`

/**
 * One prescribed medicine at the pharmacy counter: how much is still owed,
 * how much to give now, from which batch, and (for a same-salt substitute)
 * why. ``choice`` is { batch, quantity, reason }.
 */
export default function DispenseLine({ medicine, stock, choice, onChange, done }) {
  const { t } = useLanguage()
  const owed = remainingOf(medicine)
  const batches = usableBatches(stock, medicine.name)
  const substitutes = substituteBatches(stock, medicine.name)
  const chosen = [...batches, ...substitutes].find((b) => String(b.id) === String(choice.batch))
  const isSubstitute = Boolean(chosen) && substitutes.includes(chosen)
  const set = (field) => (event) => onChange({ ...choice, [field]: event.target.value })
  const short = chosen && Number(chosen.stock) < Number(choice.quantity || 0)

  return (
    <div className="rounded-xl border border-gray-200 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <p className="font-semibold text-gray-800">{medicine.name}</p>
          {/* F8: as the prescription saved them; blank stays blank. */}
          <dl className="mt-1 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-0.5 text-sm">
            {[["Dose", medicine.dosage], ["Frequency", medicine.frequency], ["Duration", medicine.duration]].map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-gray-500">{t(label)}</dt>
                <dd className="text-gray-800">{value || "—"}</dd>
              </div>
            ))}
            <dt className="text-gray-500">{t("Instructions")}</dt>
            <dd className={medicine.instructions ? "font-medium text-gray-900" : "text-gray-400"}>
              {medicine.instructions || t("None written")}
            </dd>
          </dl>
        </div>
        <div className="text-sm">
          <p>{t("Required:")} <span className="font-bold">{medicine.quantity}</span></p>
          {Number(medicine.dispensed) > 0 && (
            <p className="text-ink-600">{t("Already given: {given} · Still to give: {owed}", { given: medicine.dispensed, owed })}</p>
          )}
          {chosen && <p className={short ? "text-red-600" : "text-green-600"}>{t("Stock:")} <span className="font-bold">{chosen.stock}</span></p>}
        </div>
      </div>

      {!done && owed > 0 && (
        <div className="mt-3 grid gap-3 md:grid-cols-[minmax(0,1fr)_8rem]">
          <div>
            <label htmlFor={`dispense-batch-${medicine.id}`} className="mb-1 block text-xs text-gray-500">
              {t("Stock batch for")} {medicine.name}
            </label>
            <select id={`dispense-batch-${medicine.id}`} value={choice.batch ?? ""} onChange={set("batch")} className="hms-input w-full">
              <option value="">{batches.length + substitutes.length > 0 ? t("Choose a batch") : t("Not in stock")}</option>
              {batches.map((batch) => <option key={batch.id} value={batch.id}>{batchLabel(batch)}</option>)}
              {substitutes.length > 0 && (
                <optgroup label={t("Same-salt substitutes (pharmacist only)")}>
                  {substitutes.map((batch) => <option key={batch.id} value={batch.id}>{batch.name} · {batchLabel(batch)}</option>)}
                </optgroup>
              )}
            </select>
          </div>
          <div>
            <label htmlFor={`dispense-qty-${medicine.id}`} className="mb-1 block text-xs text-gray-500">{t("Give now")}</label>
            <input id={`dispense-qty-${medicine.id}`} type="number" min="0" max={owed} value={choice.quantity ?? owed}
              onChange={set("quantity")} className="hms-input w-full" />
          </div>
          {isSubstitute && (
            <div className="md:col-span-2">
              <label htmlFor={`dispense-reason-${medicine.id}`} className="mb-1 block text-xs text-gray-500">
                {t("Why {given} instead of {prescribed}?", { given: chosen.name, prescribed: medicine.name })}
              </label>
              <input id={`dispense-reason-${medicine.id}`} value={choice.reason || ""} onChange={set("reason")}
                placeholder={t("e.g. Prescribed brand out of stock")} className="hms-input w-full" />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
