import { useState } from "react"
import { Check, Copy, Send } from "lucide-react"
import api from "../../services/api.js"
import { STAFF_ROLES } from "../../config/staffRoles.js"
import { Alert, Button, Field, Input, Select } from "../ui"

const EMPTY = { name: "", phone: "", email: "", role: "Doctor", department: "" }

/** The invitation link for someone who still has to set a password, with a copy button. */
export function InviteLink({ result }) {
  const [copied, setCopied] = useState(false)
  if (!result?.invite_url) return null
  // The page the admin is on is the web app the person should open.
  const url = result.invite_path ? `${window.location.origin}${result.invite_path}` : result.invite_url

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  return (
    <Alert tone="success" title={`Invitation for ${result.name}`}>
      <p>
        Username <strong>{result.username}</strong>.{" "}
        {result.emailed ? "The link was emailed to them. " : "Email is not set up, so send them this link yourself. "}
        It works once and expires in a few days.
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <code className="min-w-0 flex-1 break-all rounded-md bg-white/70 px-2 py-1 text-xs">{url}</code>
        <Button size="sm" variant="secondary" icon={copied ? Check : Copy} onClick={copy}>
          {copied ? "Copied" : "Copy link"}
        </Button>
      </div>
    </Alert>
  )
}

/**
 * Invite one person to the selected hospital with a role (and department).
 * The backend creates the account; the person sets a password from the link.
 */
export default function InviteStaffForm({ departments = [], onInvited }) {
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [result, setResult] = useState(null)

  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError("")
    setResult(null)
    if (form.phone.length !== 10) {
      setError("Enter a 10-digit mobile number. The sign-in code is sent to it.")
      return
    }
    setSaving(true)
    try {
      const data = await api.users.invite({
        ...form,
        department: form.department ? Number(form.department) : null,
      })
      setResult(data)
      setForm({ ...EMPTY, role: form.role })
      onInvited?.(data)
    } catch (err) {
      setError(err.message || "The invitation was not sent.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {error && <Alert tone="danger">{error}</Alert>}
      {result && !result.invited && (
        <Alert tone="success">
          {result.name} already has a staff account and was added to this hospital as {result.membership?.role}. They
          sign in with their existing password.
        </Alert>
      )}
      <InviteLink result={result} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Full name" required>
          <Input value={form.name} onChange={set("name")} autoComplete="off" />
        </Field>
        <Field label="Mobile number" required hint="Receives the sign-in code">
          <Input
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value.replace(/\D/g, "").slice(0, 10) })}
            inputMode="numeric"
            autoComplete="off"
          />
        </Field>
        <Field label="Email" hint="The invitation is emailed here when email is set up">
          <Input type="email" value={form.email} onChange={set("email")} autoComplete="off" />
        </Field>
        <Field label="Role" required>
          <Select value={form.role} onChange={set("role")}>
            {STAFF_ROLES.map((role) => (
              <option key={role}>{role}</option>
            ))}
          </Select>
        </Field>
        {departments.length > 0 && (
          <Field label="Department" hint="Leave empty to work across all departments">
            <Select value={form.department} onChange={set("department")}>
              <option value="">All departments</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
      </div>
      <Button type="submit" icon={Send} loading={saving} disabled={!form.name.trim()}>
        Send invitation
      </Button>
    </form>
  )
}
