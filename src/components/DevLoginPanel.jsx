import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { FlaskConical } from "lucide-react"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import api from "../services/api.js"
import { Alert, Button, Field, Input, Select } from "./ui"

/*
 * Temporary development sign-in shown on the staff and patient login pages.
 * One shared mobile number or email and one password open the demo account
 * of any role. The server shows it only when DEBUG and DEV_LOGIN_ENABLED are
 * on (backend/users/dev_login.py); otherwise this renders nothing.
 */
/**
 * @param {{ role?: string, onRoleChange?: (role: string) => void, defaultRole?: string, afterPatientLogin?: string }} props
 * Pass role/onRoleChange to follow the page's own role picker ("I am a").
 */
function DevLoginPanel({ role: chosenRole, onRoleChange, defaultRole = "Admin", afterPatientLogin = "/patient" }) {
  const navigate = useNavigate()
  const { adoptExternalSession } = useAuth()
  const { switchRole } = useRole()
  const [roles, setRoles] = useState([])
  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [ownRole, setOwnRole] = useState(defaultRole)
  const role = chosenRole ?? ownRole
  const setRole = onRoleChange ?? setOwnRole
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    api.auth.devLoginStatus().then((data) => {
      if (active && data?.enabled) setRoles(data.roles || [])
    })
    return () => {
      active = false
    }
  }, [])

  if (roles.length === 0) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const data = await api.auth.devLogin(identifier.trim(), password, role)
      await adoptExternalSession(data)
      switchRole(role)
      navigate(data.account_type === "staff" ? "/" : afterPatientLogin)
    } catch (err) {
      setError(err.message || "Sign-in failed.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="mb-5 rounded-2xl border border-amber-300 bg-amber-50/95 p-5 shadow-sm" aria-labelledby="dev-login-title">
      <p id="dev-login-title" className="flex items-center gap-2 text-sm font-semibold text-amber-900">
        <FlaskConical size={16} aria-hidden="true" /> Development sign-in (temporary)
      </p>
      <p className="mt-1 text-xs text-amber-800">
        Shared mobile number or email and password for every role. Replaced by OTP sign-in later.
      </p>
      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="Mobile number or email" required>
          <Input value={identifier} onChange={(e) => setIdentifier(e.target.value)} autoComplete="username" disabled={loading} />
        </Field>
        <Field label="Password" required>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" disabled={loading} />
        </Field>
        <Field label="Sign in as" required>
          <Select value={role} onChange={(e) => setRole(e.target.value)} disabled={loading}>
            {roles.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </Select>
        </Field>
        <Button type="submit" loading={loading} className="w-full justify-center">
          Sign in as {role}
        </Button>
      </form>
    </section>
  )
}

export default DevLoginPanel
