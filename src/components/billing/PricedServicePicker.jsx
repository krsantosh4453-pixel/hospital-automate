import { useEffect, useState } from "react"
import api from "../../services/api.js"
import { Button, Field, Input, Select } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { pickablePrices, pricedAmount } from "../../utils/billingLines.js"

// B-4: add services to a bill from the hospital price list, so the price and
// GST come from the list. Consultations, laboratory tests and bed days are
// not offered: they are charged automatically (B-1).

const rowsOf = (data) => (Array.isArray(data) ? data : data?.results || [])

export default function PricedServicePicker({ hospitalId, lines, onChange }) {
  const { t } = useLanguage()
  const [prices, setPrices] = useState(null)
  const [error, setError] = useState("")
  const [choice, setChoice] = useState("")
  const [quantity, setQuantity] = useState("1")

  useEffect(() => {
    if (!hospitalId) return undefined
    let cancelled = false
    api.billing.priceList
      .list(hospitalId, { current: true })
      .then((data) => !cancelled && setPrices(pickablePrices(rowsOf(data))))
      .catch((err) => !cancelled && setError(err.message || "Could not load the price list."))
    return () => {
      cancelled = true
    }
  }, [hospitalId])

  const add = () => {
    const price = (prices || []).find((p) => String(p.id) === choice)
    const qty = Number.parseInt(quantity, 10)
    if (!price || !(qty >= 1)) return
    onChange([...lines, { id: price.id, name: price.name, unit_price: price.unit_price, tax_rate: price.tax_rate,
      quantity: qty }])
    setChoice("")
    setQuantity("1")
  }

  const remove = (index) => onChange(lines.filter((_, i) => i !== index))

  return (
    <div className="space-y-2" data-testid="priced-services">
      <p className="text-sm font-medium text-ink-700">{t("Services from the price list")}</p>
      {error && <p className="text-sm text-red-700" role="alert">{error}</p>}
      {lines.length > 0 && (
        <ul className="divide-y divide-line rounded-lg border border-line text-sm">
          {lines.map((line, index) => (
            <li key={`${line.id}-${index}`} className="flex items-center justify-between gap-2 px-3 py-2">
              <span>
                {line.name} × {line.quantity} · ₹{pricedAmount(line).toFixed(2)}
                {Number(line.tax_rate) > 0 && <span className="text-ink-500"> ({t("incl. GST")} {line.tax_rate}%)</span>}
              </span>
              <Button type="button" size="sm" variant="ghost" onClick={() => remove(index)}>{t("Remove")}</Button>
            </li>
          ))}
        </ul>
      )}
      {prices === null && !error ? (
        <p className="text-sm text-ink-500">{t("Loading…")}</p>
      ) : prices?.length === 0 && !error ? (
        <p className="text-sm text-ink-500">{t("No other services are on the price list yet.")}</p>
      ) : error ? null : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_6rem_auto] sm:items-end">
          <Field label="Service">
            <Select value={choice} onChange={(e) => setChoice(e.target.value)} aria-label={t("Service from the price list")}>
              <option value="">{t("Choose…")}</option>
              {prices.map((p) => (
                <option key={p.id} value={p.id}>{p.name} · ₹{p.unit_price}</option>
              ))}
            </Select>
          </Field>
          <Field label="Qty">
            <Input type="number" min="1" step="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </Field>
          <Button type="button" variant="secondary" onClick={add} disabled={!choice}>{t("Add service")}</Button>
        </div>
      )}
    </div>
  )
}
