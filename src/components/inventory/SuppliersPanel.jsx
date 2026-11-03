import { useState } from "react"
import { Pencil, Plus, Truck } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Button, EmptyState, Field, Input, Modal, StatusBadge, TableWrap, Textarea } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

const EMPTY_FORM = { name: "", contact_person: "", phone: "", email: "", address: "", is_active: true }

/**
 * Suppliers of one hospital: list, add, edit, and mark inactive.
 *
 * @param {{ hospital: { id: number, name: string }, suppliers: object[], canEdit: boolean, onChanged: () => void }} props
 */
export default function SuppliersPanel({ hospital, suppliers, canEdit, onChanged }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [editing, setEditing] = useState(null) // null = closed, {} = new, supplier = edit
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const open = (supplier) => {
    setEditing(supplier || {})
    setForm(supplier ? { ...EMPTY_FORM, ...supplier } : EMPTY_FORM)
  }
  const close = () => setEditing(null)
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const save = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) {
      toast.warning("Enter the supplier's name.")
      return
    }
    setSaving(true)
    try {
      const payload = {
        name: form.name.trim(),
        contact_person: (form.contact_person || "").trim(),
        phone: (form.phone || "").trim(),
        email: (form.email || "").trim(),
        address: (form.address || "").trim(),
        is_active: form.is_active,
        hospital: hospital.id,
      }
      if (editing.id) {
        await api.procurement.suppliers.update(editing.id, payload, hospital.id)
      } else {
        await api.procurement.suppliers.create(payload)
      }
      toast.success(editing.id ? "Supplier updated." : "Supplier added.")
      close()
      onChanged()
    } catch (err) {
      toast.error(err.message || "Could not save the supplier.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      {suppliers.length === 0 ? (
        <EmptyState
          icon={Truck}
          title={t("No suppliers yet")}
          description="Add the companies you buy from, then raise purchase orders to them."
          action={canEdit && <Button icon={Plus} onClick={() => open(null)}>{t("Add supplier")}</Button>}
        />
      ) : (
        <>
          {canEdit && (
            <div className="flex justify-end border-b border-line px-4 py-3">
              <Button size="sm" icon={Plus} onClick={() => open(null)}>{t("Add supplier")}</Button>
            </div>
          )}
          <TableWrap>
            <table className="hms-table">
              <caption className="sr-only">{t("Suppliers of")}{" "}{hospital.name}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("Supplier")}</th>
                  <th scope="col">{t("Contact")}</th>
                  <th scope="col">{t("Phone")}</th>
                  <th scope="col">{t("Email")}</th>
                  <th scope="col">{t("Status")}</th>
                  {canEdit && <th scope="col"><span className="sr-only">{t("Actions")}</span></th>}
                </tr>
              </thead>
              <tbody>
                {suppliers.map((supplier) => (
                  <tr key={supplier.id}>
                    <td className="font-medium text-ink-900">{supplier.name}</td>
                    <td className="text-ink-600">{supplier.contact_person || "—"}</td>
                    <td className="tabular-nums text-ink-600">{supplier.phone || "—"}</td>
                    <td className="text-ink-600">{supplier.email || "—"}</td>
                    <td><StatusBadge status={supplier.is_active ? "active" : "inactive"} label={supplier.is_active ? t("Active") : t("Inactive")} /></td>
                    {canEdit && (
                      <td>
                        <div className="flex justify-end">
                          <Button variant="ghost" size="icon-sm" icon={Pencil} onClick={() => open(supplier)} aria-label={`Edit ${supplier.name}`} title={t("Edit")} />
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </>
      )}

      <Modal
        open={editing !== null}
        onClose={close}
        title={editing?.id ? `Edit ${editing.name}` : t("Add supplier")}
        footer={
          <>
            <Button variant="secondary" onClick={close}>{t("Cancel")}</Button>
            <Button type="submit" form="supplier-form" loading={saving}>{editing?.id ? t("Save changes") : t("Add supplier")}</Button>
          </>
        }
      >
        <form id="supplier-form" onSubmit={save} className="space-y-4">
          <Field label="Supplier name" required>
            <Input name="name" value={form.name} onChange={change} />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Contact person">
              <Input name="contact_person" value={form.contact_person} onChange={change} />
            </Field>
            <Field label="Phone">
              <Input type="tel" name="phone" value={form.phone} onChange={change} />
            </Field>
            <Field label="Email" className="sm:col-span-2">
              <Input type="email" name="email" value={form.email} onChange={change} />
            </Field>
          </div>
          <Field label="Address">
            <Textarea name="address" rows={2} value={form.address} onChange={change} />
          </Field>
          {editing?.id && (
            <label className="flex items-center gap-2 text-sm text-ink-700">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
              {t("Active (inactive suppliers are not offered for new purchase orders)")}
            </label>
          )}
        </form>
      </Modal>
    </>
  )
}
