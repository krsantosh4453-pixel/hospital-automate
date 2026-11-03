import { useCallback, useEffect, useState } from "react"
import { UserPlus, UsersRound } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, Card, CardHeader, Field, Input, SkeletonRows, useConfirm } from "../ui"

const EMPTY_FORM = { name: "", relationship: "", phone: "" }

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : ""
}

/**
 * The patient's list of family members / caregivers with view-only access.
 * They sign in from the login page ("Family" tab) with their own mobile OTP.
 */
export default function FamilyAccessCard() {
  const [confirm, confirmDialog] = useConfirm()
  const [grants, setGrants] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  const load = useCallback(async () => {
    try {
      setGrants(await api.auth.listFamilyAccess())
    } catch (err) {
      setError(err.message || "Could not load family access.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleGrant = async (e) => {
    e.preventDefault()
    setError("")
    setNotice("")
    if (!/^\d{10}$/.test(form.phone)) {
      setError("Enter the family member's 10-digit mobile number.")
      return
    }
    setSaving(true)
    try {
      const grant = await api.auth.grantFamilyAccess(form)
      setGrants((prev) => [grant, ...prev])
      setForm(EMPTY_FORM)
      setNotice(`${grant.name} can now sign in with +91 ${grant.phone} and view your records.`)
    } catch (err) {
      setError(err.message || "Could not give access.")
    } finally {
      setSaving(false)
    }
  }

  const handleRevoke = async (grant) => {
    const ok = await confirm({
      title: "Remove family access?",
      message: `${grant.name} will lose access to your records immediately.`,
      confirmLabel: "Remove access",
      destructive: true,
    })
    if (!ok) return
    setError("")
    try {
      await api.auth.revokeFamilyAccess(grant.id)
      setGrants((prev) => prev.filter((g) => g.id !== grant.id))
      setNotice(`${grant.name} no longer has access.`)
    } catch (err) {
      setError(err.message || "Could not remove access.")
    }
  }

  return (
    <Card>
      {confirmDialog}
      <CardHeader
        icon={UsersRound}
        title="Family access"
        description="Let a family member or caregiver view your appointments, prescriptions, lab reports and bills. They sign in with an OTP on their own mobile and cannot change anything."
      />

      <div className="space-y-4 p-5">
        {error && <Alert tone="danger" onDismiss={() => setError("")}>{error}</Alert>}
        {notice && !error && <Alert tone="success" onDismiss={() => setNotice("")}>{notice}</Alert>}

        <form onSubmit={handleGrant} className="grid gap-4 md:grid-cols-[1fr_1fr_1fr_auto] md:items-end">
          <Field label="Name" required>
            <Input
              value={form.name}
              maxLength={100}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Ravi Kumar"
              required
            />
          </Field>
          <Field label="Relationship" required>
            <Input
              value={form.relationship}
              maxLength={50}
              onChange={(e) => setForm({ ...form, relationship: e.target.value })}
              placeholder="e.g. Son"
              required
            />
          </Field>
          <Field label="Their mobile number" required>
            <Input
              type="tel"
              inputMode="numeric"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value.replace(/\D/g, "").slice(0, 10) })}
              placeholder="10-digit number"
              required
            />
          </Field>
          <Button type="submit" icon={UserPlus} loading={saving}>Give access</Button>
        </form>
      </div>

      <div className="border-t border-line">
        {loading ? (
          <SkeletonRows rows={2} />
        ) : grants.length === 0 ? (
          <p className="p-5 text-sm text-ink-500">No family member has access to your records.</p>
        ) : (
          <ul className="divide-y divide-line">
            {grants.map((grant) => (
              <li key={grant.id} className="flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-medium text-ink-900">
                    {grant.name} <span className="font-normal text-ink-500">· {grant.relationship}</span>
                  </p>
                  <p className="mt-0.5 text-[13px] text-ink-500">
                    +91 {grant.phone} · added {formatDate(grant.created_at)}
                    {grant.last_used_at ? ` · last signed in ${formatDate(grant.last_used_at)}` : " · has not signed in yet"}
                  </p>
                </div>
                <Button variant="danger-ghost" size="sm" onClick={() => handleRevoke(grant)}>Remove access</Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}
