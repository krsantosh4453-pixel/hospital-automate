import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { BrandMark } from "../components/Sidebar.jsx"
import api from "../services/api.js"
import { Alert, Button, Field, Input } from "../components/ui"

/**
 * Opened from a staff invitation link: shows who it is for and lets the
 * person set their password. They then sign in on the staff login page.
 */
function StaffInvite() {
  const { uid, token } = useParams()
  const [invite, setInvite] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    let cancelled = false
    api.staffInvite
      .get(uid, token)
      .then((data) => !cancelled && setInvite(data))
      .catch((err) => !cancelled && setError(err.message || "This invitation link is not valid."))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [uid, token])

  const submit = async (e) => {
    e.preventDefault()
    setError("")
    if (password !== confirm) {
      setError("The two passwords do not match.")
      return
    }
    setSaving(true)
    try {
      await api.staffInvite.accept(uid, token, { password, confirm_password: confirm })
      setDone(true)
    } catch (err) {
      setError(err.message || "The password was not set.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-[26rem]">
        <div className="mb-8">
          <BrandMark inverted={false} />
        </div>
        <div className="hms-surface-dark rounded-2xl border border-line p-6 shadow-xl shadow-ink-900/5 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-brand-700">Staff invitation</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink-900">
            {invite ? `Welcome, ${invite.name}` : "Set your password"}
          </h1>

          <div className="mt-6 space-y-4">
            {loading && <p className="text-sm text-ink-500" role="status">Checking the link…</p>}
            {error && <Alert tone="danger">{error}</Alert>}

            {done ? (
              <>
                <Alert tone="success">
                  Your password is set. Sign in with username <strong>{invite.username}</strong>.
                </Alert>
                <Link
                  to="/staff-login"
                  className="inline-flex h-10 w-full items-center justify-center rounded-lg bg-brand-600 text-sm font-medium text-white hover:bg-brand-700"
                >
                  Go to staff sign-in
                </Link>
              </>
            ) : (
              invite && (
                <form onSubmit={submit} className="space-y-4">
                  <ul className="space-y-1 text-sm text-ink-700">
                    {invite.hospitals.map((h) => (
                      <li key={h.name}>
                        {h.role} at <strong>{h.name}</strong>
                      </li>
                    ))}
                  </ul>
                  <Field label="Username">
                    <Input value={invite.username} readOnly autoComplete="username" />
                  </Field>
                  <Field label="New password" required hint="At least 8 characters, not only numbers">
                    <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
                  </Field>
                  <Field label="Confirm password" required>
                    <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
                  </Field>
                  <Button type="submit" className="w-full justify-center" loading={saving} disabled={!password || !confirm}>
                    Set password
                  </Button>
                </form>
              )
            )}
          </div>
        </div>
      </div>
    </main>
  )
}

export default StaffInvite
