import { useEffect, useState } from "react"
import { Plus } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Alert, Button, EmptyState, Field, Input, Modal, Select, StatusBadge, TableWrap, Textarea } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

// One hospital-service list (OT, ambulance, mortuary, CSSD, ...): the rows,
// a form to add one and the status actions the server allows. The server
// enforces roles, order of steps and tenancy; this panel only hides buttons
// a role cannot use and shows the server's message when it refuses.

const list = (data) => (Array.isArray(data) ? data : data?.results || [])
const toInput = (value, type) => (type === "checkbox" ? Boolean(value) : value ?? "")
const formatValue = (value) => {
  if (value === true) return "Yes"
  if (value === false) return "No"
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) return new Date(value).toLocaleString("en-IN")
  return value ?? ""
}

function OptionsField({ field, hospitalId, value, onChange, a11y }) {
  const { t } = useLanguage()
  const [options, setOptions] = useState([])
  const [query, setQuery] = useState("")

  useEffect(() => {
    let cancelled = false
    const { source } = field
    const load = source.kind === "patients"
      ? (query.trim().length >= 2 ? api.patients.list(hospitalId, 1, query.trim()) : Promise.resolve([]))
      : source.kind === "departments" ? api.departments.list(hospitalId)
        : source.kind === "doctors" ? api.doctors.list(hospitalId)
          : api.services.list(source.resource, hospitalId)
    load.then((data) => !cancelled && setOptions(list(data).filter(source.filter || (() => true))))
      .catch(() => !cancelled && setOptions([]))
    return () => {
      cancelled = true
    }
  }, [field, hospitalId, query])

  return (
    <div className="space-y-1.5">
      {field.source.kind === "patients" && (
        <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("Search by name or phone")} aria-label={t("Search patients")} />
      )}
      <Select value={value ?? ""} onChange={onChange} {...a11y}>
        <option value="">{t("Choose…")}</option>
        {options.map((option) => <option key={option.id} value={option.id}>{field.source.label(option)}</option>)}
      </Select>
    </div>
  )
}

// ``a11y`` (id, aria-describedby, aria-invalid from <Field>) goes to the real control so its label works.
function FieldInput({ field, hospitalId, value, onChange, ...a11y }) {
  const { t } = useLanguage()
  const set = (event) => onChange(field.type === "checkbox" ? event.target.checked : event.target.value)
  if (field.source) return <OptionsField field={field} hospitalId={hospitalId} value={value} onChange={set} a11y={a11y} />
  if (field.options) {
    return (
      <Select value={value ?? ""} onChange={set} {...a11y}>
        <option value="">{t("Choose…")}</option>
        {field.options.map((option) => <option key={option} value={option}>{t(option)}</option>)}
      </Select>
    )
  }
  if (field.type === "textarea") return <Textarea rows={3} value={value ?? ""} onChange={set} placeholder={field.placeholder ? t(field.placeholder) : undefined} {...a11y} />
  if (field.type === "checkbox") return <input type="checkbox" checked={Boolean(value)} onChange={set} {...a11y} />
  return <Input type={field.type || "text"} value={toInput(value, field.type)} onChange={set} placeholder={field.placeholder ? t(field.placeholder) : undefined} {...a11y} />
}

function FormDialog({ open, title, fields, hospitalId, saving, error, onClose, onSubmit }) {
  const { t } = useLanguage()
  const [values, setValues] = useState({})
  useEffect(() => {
    if (open) setValues(Object.fromEntries(fields.map((f) => [f.name, f.type === "checkbox" ? false : ""])))
  }, [open, fields])
  const submit = (event) => {
    event.preventDefault()
    const body = Object.fromEntries(Object.entries(values).filter(([, v]) => v !== "").map(([k, v]) => {
      const field = fields.find((f) => f.name === k)
      return [k, field?.type === "datetime-local" ? new Date(v).toISOString() : field?.type === "number" || field?.source ? Number(v) : v]
    }))
    onSubmit(body)
  }
  return (
    <Modal open={open} onClose={onClose} title={t(title)} size="md"
      footer={<><Button variant="secondary" onClick={onClose}>{t("Cancel")}</Button><Button type="submit" form="service-form" loading={saving}>{t("Save")}</Button></>}>
      <form id="service-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        {fields.map((field) => (
          <Field key={field.name} label={field.label} required={field.required} hint={field.hint} className={field.wide || field.type === "textarea" ? "sm:col-span-2" : ""}>
            <FieldInput field={field} hospitalId={hospitalId} value={values[field.name]} onChange={(v) => setValues((prev) => ({ ...prev, [field.name]: v }))} />
          </Field>
        ))}
        {error && <Alert tone="danger" className="sm:col-span-2">{error}</Alert>}
      </form>
    </Modal>
  )
}

/**
 * config: { resource, createLabel, columns: [{ key, label, render? }], fields, actions:
 *   [{ verb, label, when(row), fields?, roles? }], createRoles }
 */
export default function ResourcePanel({ hospitalId, config, role }) {
  const { t } = useLanguage()
  const toast = useToast()
  const [rows, setRows] = useState([])
  const [loadError, setLoadError] = useState("")
  const [reloadToken, setReloadToken] = useState(0)
  const [dialog, setDialog] = useState(null) // { kind: "create" } | { kind: "action", action, row }
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const allowed = (roles) => !roles || roles.includes(role)

  useEffect(() => {
    let cancelled = false
    api.services.list(config.resource, hospitalId)
      .then((data) => !cancelled && (setRows(list(data)), setLoadError("")))
      .catch((err) => !cancelled && setLoadError(err.status === 403 ? t("Not available for your role.") : err.message))
    return () => {
      cancelled = true
    }
  }, [config.resource, hospitalId, reloadToken, t])

  const run = async (body) => {
    setSaving(true)
    setError("")
    try {
      if (dialog.kind === "create") await api.services.create(config.resource, body, hospitalId)
      else await api.services.act(config.resource, dialog.row.id, dialog.action.verb, body, hospitalId)
      toast.success(t("Saved."))
      setDialog(null)
      setReloadToken((n) => n + 1)
    } catch (err) {
      setError(err.message || "Could not save.")
    } finally {
      setSaving(false)
    }
  }

  const startAction = (action, row) => {
    setError("")
    if (action.fields?.length) setDialog({ kind: "action", action, row })
    else {
      setDialog({ kind: "action", action, row })
      setSaving(true)
      api.services.act(config.resource, row.id, action.verb, {}, hospitalId)
        .then(() => {
          toast.success(t("Saved."))
          setReloadToken((n) => n + 1)
        })
        .catch((err) => toast.error(err.message || "Could not save."))
        .finally(() => {
          setSaving(false)
          setDialog(null)
        })
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-3 px-5 py-4">
        <p className="text-sm text-ink-600">{t(config.description)}</p>
        {config.fields && allowed(config.createRoles) && (
          <Button size="sm" icon={Plus} onClick={() => { setError(""); setDialog({ kind: "create" }) }}>{t(config.createLabel)}</Button>
        )}
      </div>
      {loadError && <Alert tone="warning" className="mx-5 mb-4">{loadError}</Alert>}
      {rows.length === 0 ? (
        <EmptyState compact title={t("Nothing recorded yet")} />
      ) : (
        <TableWrap>
          <table className="hms-table">
            <thead>
              <tr>
                {config.columns.map((col) => <th key={col.key} scope="col">{t(col.label)}</th>)}
                <th scope="col"><span className="sr-only">{t("Actions")}</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  {config.columns.map((col) => (
                    <td key={col.key}>{col.key === "status" ? <StatusBadge status={row.status} /> : col.render ? col.render(row, t) : t(String(formatValue(row[col.key])))}</td>
                  ))}
                  <td>
                    <div className="flex justify-end gap-1.5">
                      {(config.actions || []).filter((a) => a.when(row) && allowed(a.roles)).map((action) => (
                        <Button key={action.verb} size="sm" variant="subtle" onClick={() => startAction(action, row)}>{t(action.label)}</Button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}
      <FormDialog
        open={dialog?.kind === "create" || Boolean(dialog?.action?.fields?.length)}
        title={dialog?.kind === "create" ? config.createLabel : dialog?.action?.label || ""}
        fields={dialog?.kind === "create" ? config.fields : dialog?.action?.fields || []}
        hospitalId={hospitalId}
        saving={saving}
        error={error}
        onClose={() => setDialog(null)}
        onSubmit={run}
      />
    </div>
  )
}
