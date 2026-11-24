import { useCallback, useEffect, useState } from "react"
import { Tag } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, Card, CardHeader, Field, Input, Select, TableWrap, useConfirm } from "../ui"
import { useToast } from "../Toast.jsx"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"
import { CATEGORY_LABELS } from "../../utils/billingLines.js"

// B-4: the hospital price list. Billing staff read it; an Admin or Hospital
// Manager adds a price or retires one. A price is never edited: a new price
// for the same service closes the old one on the server (billing/price_list.py).

const rowsOf = (data) => (Array.isArray(data) ? data : data?.results || [])
const EMPTY = { category: "consultation", code: "", name: "", applies_to: "", unit_price: "", tax_rate: "0" }
const APPLIES_HINT = {
  consultation: "Visit type, e.g. OPD; empty for every visit",
  laboratory: "Test name exactly as ordered, e.g. Lipid Profile",
  imaging: "Modality and body part, e.g. X-ray Chest PA; or the modality alone, e.g. X-ray",
  bed: "Bed type, e.g. ICU; empty for every bed",
}

export default function PriceList({ hospitalId, canManage }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()
  const [rows, setRows] = useState([])
  const [error, setError] = useState("")
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState("")

  const load = useCallback(async () => {
    if (!hospitalId) return
    try {
      setRows(rowsOf(await api.billing.priceList.list(hospitalId, { current: true })))
      setError("")
    } catch (err) {
      setError(err.message || "Could not load the price list.")
    }
  }, [hospitalId])

  useEffect(() => {
    load()
  }, [load])

  const set = (name) => (event) => setForm((prev) => ({ ...prev, [name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    if (!form.code.trim() || !form.name.trim() || !(Number(form.unit_price) > 0)) {
      setFormError(t("Give a code, a name and a price above ₹0."))
      return
    }
    setSaving(true)
    setFormError("")
    try {
      await api.billing.priceList.create({
        hospital: hospitalId, category: form.category, code: form.code.trim(), name: form.name.trim(),
        applies_to: form.applies_to.trim(), unit_price: form.unit_price, tax_rate: form.tax_rate || "0",
      })
      toast.success(t("Price added."))
      setForm(EMPTY)
      await load()
    } catch (err) {
      setFormError(err.message || "Could not add the price.")
    } finally {
      setSaving(false)
    }
  }

  const retire = async (row) => {
    const ok = await confirm({
      title: t("Stop charging {name}?", { name: row.name }),
      message: t("Its last day is today. Bills already made keep this price."),
      confirmLabel: "Retire price",
      destructive: true,
    })
    if (!ok) return
    try {
      await api.billing.priceList.retire(row.id)
      toast.success(t("Price retired."))
      await load()
    } catch (err) {
      toast.error(err.message || "Could not retire the price.")
    }
  }

  return (
    <Card className="mb-6">
      <CardHeader
        icon={Tag}
        title={t("Price list")}
        description="Prices in force today. Consultations, laboratory tests and bed days are charged from here automatically."
        actions={<Button size="sm" variant="secondary" onClick={() => setOpen((v) => !v)}>{open ? t("Hide") : t("Show")}</Button>}
      />
      {error && <Alert tone="danger" className="m-4">{error}</Alert>}
      {open && (
        <div className="space-y-4 px-5 pb-5">
          {rows.length === 0 ? (
            <p className="text-sm text-ink-500">{t("No prices yet. Until a service has a price, its work is recorded as unbilled.")}</p>
          ) : (
            <TableWrap>
              <table className="hms-table">
                <thead>
                  <tr>
                    <th scope="col">{t("Service")}</th>
                    <th scope="col">{t("Category")}</th>
                    <th scope="col">{t("For")}</th>
                    <th scope="col" className="text-right">{t("Price")}</th>
                    <th scope="col" className="text-right">{t("GST")}</th>
                    <th scope="col">{t("From")}</th>
                    {canManage && <th scope="col"><span className="sr-only">{t("Actions")}</span></th>}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id}>
                      <td className="font-medium text-ink-900">{row.name} <span className="text-ink-500">({row.code})</span></td>
                      <td>{t(CATEGORY_LABELS[row.category] || row.category)}</td>
                      <td>{row.doctor_name || row.applies_to || <span className="text-ink-400">{t("All")}</span>}</td>
                      <td className="text-right tabular-nums">₹{row.unit_price}</td>
                      <td className="text-right tabular-nums">{row.tax_rate}%</td>
                      <td className="tabular-nums">{row.effective_from}</td>
                      {canManage && (
                        <td className="text-right">
                          <Button size="sm" variant="danger-ghost" onClick={() => retire(row)}>{t("Retire")}</Button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}

          {canManage && (
            <form onSubmit={submit} className="grid grid-cols-1 gap-3 border-t border-line pt-4 sm:grid-cols-3">
              <p className="sm:col-span-3 text-sm font-semibold text-ink-900">{t("Add a price")}</p>
              <Field label="Category" required>
                <Select value={form.category} onChange={set("category")}>
                  {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{t(label)}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Code" required><Input value={form.code} onChange={set("code")} placeholder="CON-OPD" maxLength={40} /></Field>
              <Field label="Name" required><Input value={form.name} onChange={set("name")} placeholder={t("OPD consultation")} maxLength={150} /></Field>
              <Field label="Applies to" hint={APPLIES_HINT[form.category] || "Optional"}>
                <Input value={form.applies_to} onChange={set("applies_to")} maxLength={150} />
              </Field>
              <Field label="Price (₹)" required>
                <Input type="number" min="0.01" step="0.01" inputMode="decimal" value={form.unit_price} onChange={set("unit_price")} />
              </Field>
              <Field label="GST %">
                <Input type="number" min="0" max="100" step="0.01" value={form.tax_rate} onChange={set("tax_rate")} />
              </Field>
              {formError && <Alert tone="danger" className="sm:col-span-3">{formError}</Alert>}
              <div className="sm:col-span-3 flex justify-end">
                <Button type="submit" loading={saving}>{t("Add price")}</Button>
              </div>
            </form>
          )}
        </div>
      )}
      {confirmDialog}
    </Card>
  )
}
