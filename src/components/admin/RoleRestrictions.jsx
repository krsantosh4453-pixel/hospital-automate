import { useState } from "react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Select } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

/**
 * One module's setting for one role at this hospital: built-in access,
 * view only, or no access. Only takes access away; the server enforces it.
 */
export default function RoleRestrictionSelect({ hospitalId, roleName, module, rule, onSaved }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const value = rule?.access || "full"

  const change = async (event) => {
    const next = event.target.value
    setSaving(true)
    try {
      if (next === "full") await api.roleRestrictions.remove(rule.id, hospitalId)
      else if (rule) await api.roleRestrictions.update(rule.id, { access: next }, hospitalId)
      else await api.roleRestrictions.create({ role: roleName, module, access: next }, hospitalId)
      toast.success(t("Saved for {role}: {module}.", { role: roleName, module }))
      onSaved()
    } catch (err) {
      toast.error(err.message || "Could not save the restriction.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Select value={value} onChange={change} disabled={saving} aria-label={t("Access to {module}", { module })} className="w-36">
      <option value="full">{t("Built-in")}</option>
      <option value="view">{t("View only")}</option>
      <option value="none">{t("No access")}</option>
    </Select>
  )
}
