import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import api from "../services/api.js"
import {
  LOGIN_ROLES,
  getSelectedLoginRole,
  saveSelectedLoginRole,
} from "../utils/roleRouting.js"
import { BrandMark } from "../components/Sidebar.jsx"
import { Alert } from "../components/ui"

const inputClass = "hms-input w-full"

function Register() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const initialRole = useMemo(() => {
    const fromQuery = searchParams.get("role")
    if (LOGIN_ROLES.includes(fromQuery)) return saveSelectedLoginRole(fromQuery)
    return getSelectedLoginRole()
  }, [searchParams])

  const [role, setRole] = useState(initialRole)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loading, setLoading] = useState(false)
  const [pendingEmail, setPendingEmail] = useState("")
  const [otp, setOtp] = useState("")
  const [otpMessage, setOtpMessage] = useState("")
  const [verified, setVerified] = useState(false)
  const [form, setForm] = useState({
    full_name: "",
    phone: "",
    email: "",
    password: "",
    confirm_password: "",
    date_of_birth: "",
    gender: "Other",
    address: "",
    license_number: "",
    specialization: "",
    experience: "",
    nursing_registration: "",
    department: "",
    employee_id: "",
    invite_code: "",
  })

  useEffect(() => {
    saveSelectedLoginRole(role)
  }, [role])

  const handleVerifyEmail = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const data = await api.auth.verifyEmailOtp(pendingEmail, otp)
      setVerified(true)
      setSuccess(data.message || "Email verified. You can now sign in.")
    } catch (err) {
      setError(err.message || "Invalid OTP.")
    } finally {
      setLoading(false)
    }
  }

  const handleResendEmail = async () => {
    setError("")
    setLoading(true)
    try {
      const data = await api.auth.requestEmailOtp(pendingEmail)
      setOtpMessage(data.message || "Verification email requested.")
    } catch (err) {
      setError(err.message || "Unable to send verification email. Please check email configuration.")
    } finally {
      setLoading(false)
    }
  }

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setSuccess("")

    if (form.password !== form.confirm_password) {
      setError("Password and confirm password do not match.")
      return
    }

    setLoading(true)
    try {
      const payload = {
        role,
        full_name: form.full_name,
        phone: form.phone,
        email: form.email,
        password: form.password,
        confirm_password: form.confirm_password,
      }

      if (role === "Patient") {
        payload.date_of_birth = form.date_of_birth
        payload.gender = form.gender
        payload.address = form.address
      }
      if (role === "Doctor") {
        payload.license_number = form.license_number
        payload.specialization = form.specialization
        payload.experience = form.experience
      }
      if (role === "Nurse") {
        payload.nursing_registration = form.nursing_registration
        payload.license_number = form.nursing_registration
        payload.department = form.department
      }
      if (role === "Compounder" || role === "Receptionist") {
        payload.employee_id = form.employee_id
        payload.department = form.department
      }
      if (role === "Admin") {
        payload.invite_code = form.invite_code
      }

      const data = await api.auth.register(payload)

      if (role === "Patient" && data.patient) {
        setPendingEmail(data.user?.email || form.email)
        setOtpMessage(data.verification?.message || data.message || "Account created.")
        setSuccess(data.message || "Patient account created.")
        return
      }

      setSuccess(data.message || "Account created.")
      setTimeout(() => {
        navigate(`/patient-login?role=${encodeURIComponent(role)}`)
      }, 1200)
    } catch (err) {
      setError(err.message || "Registration failed.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-[28rem]">
        <div className="mb-8">
          <BrandMark inverted={false} />
          <h1 className="mt-6 text-2xl font-semibold tracking-tight text-ink-900">Create an account</h1>
          <p className="mt-1 text-sm text-ink-500">Patients can sign in once their email is verified. Staff accounts wait for an administrator&apos;s approval.</p>
        </div>

        <div className="hms-surface-dark rounded-2xl border border-line p-6 shadow-xl shadow-ink-900/5 sm:p-8">
          <div className="mb-6">
            <p id="register-role-label" className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-ink-500">
              Account type
            </p>
            <div className="grid grid-cols-3 gap-1.5" role="radiogroup" aria-labelledby="register-role-label">
              {LOGIN_ROLES.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setRole(item)}
                  role="radio"
                  aria-checked={role === item}
                  className={`h-9 rounded-lg border px-2 text-xs font-semibold transition-colors ${role === item ? "border-brand-600 bg-brand-600 text-white" : "border-line bg-white text-ink-700 hover:border-brand-300"}`}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          {role === "Admin" && (
            <Alert tone="warning" className="mb-4">
              Admin accounts cannot be created from the role selector alone.
              An invitation code from an existing administrator is required.
            </Alert>
          )}

          {["Doctor", "Nurse", "Compounder", "Receptionist"].includes(role) && (
            <Alert tone="info" className="mb-4">
              {role} registrations stay pending until a hospital administrator
              activates the staff profile. Selecting {role} here does not grant
              {` ${role} `} access by itself.
            </Alert>
          )}

          {error && (
            <Alert tone="danger" className="mb-4">{error}</Alert>
          )}
          {success && (
            <Alert tone="success" className="mb-4">{success}</Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="reg-field-1" className="hms-label">Full Name</label>
              <input
                id="reg-field-1"
                className={inputClass}
                value={form.full_name}
                onChange={(e) => setField("full_name", e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="reg-field-phone" className="hms-label">Mobile Number</label>
              <div className="flex">
                <span className="flex items-center rounded-l-lg border border-r-0 border-line-strong bg-ink-50 px-3 text-sm text-ink-600">
                  +91
                </span>
                <input
                  id="reg-field-phone"
                  type="tel"
                  inputMode="numeric"
                  className="hms-input w-full rounded-l-none"
                  value={form.phone}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, "")
                    if (val.length <= 10) setField("phone", val)
                  }}
                  placeholder="Enter 10-digit number"
                  required
                />
              </div>
            </div>
            <div>
              <label htmlFor="reg-field-2" className="hms-label">Email</label>
              <input
                id="reg-field-2"
                type="email"
                className={inputClass}
                value={form.email}
                onChange={(e) => setField("email", e.target.value)}
                required={role === "Patient"}
              />
            </div>

            {role === "Patient" && (
              <>
                <div>
                  <label htmlFor="reg-field-3" className="hms-label">Date of Birth</label>
                  <input
                    id="reg-field-3"
                    type="date"
                    className={inputClass}
                    value={form.date_of_birth}
                    onChange={(e) => setField("date_of_birth", e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="reg-field-4" className="hms-label">Gender</label>
                  <select
                    id="reg-field-4"
                    className={inputClass}
                    value={form.gender}
                    onChange={(e) => setField("gender", e.target.value)}
                  >
                    <option>Male</option>
                    <option>Female</option>
                    <option>Other</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="reg-field-5" className="hms-label">Address</label>
                  <input
                    id="reg-field-5"
                    className={inputClass}
                    value={form.address}
                    onChange={(e) => setField("address", e.target.value)}
                  />
                </div>
              </>
            )}

            {role === "Doctor" && (
              <>
                <div>
                  <label htmlFor="reg-field-6" className="hms-label">Medical Registration / License Number</label>
                  <input
                    id="reg-field-6"
                    className={inputClass}
                    value={form.license_number}
                    onChange={(e) => setField("license_number", e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="reg-field-7" className="hms-label">Specialization</label>
                  <input
                    id="reg-field-7"
                    className={inputClass}
                    value={form.specialization}
                    onChange={(e) => setField("specialization", e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="reg-field-8" className="hms-label">Experience</label>
                  <input
                    id="reg-field-8"
                    className={inputClass}
                    value={form.experience}
                    onChange={(e) => setField("experience", e.target.value)}
                    placeholder="e.g. 8 years"
                  />
                </div>
              </>
            )}

            {role === "Nurse" && (
              <>
                <div>
                  <label htmlFor="reg-field-9" className="hms-label">Nursing Registration / ID</label>
                  <input
                    id="reg-field-9"
                    className={inputClass}
                    value={form.nursing_registration}
                    onChange={(e) => setField("nursing_registration", e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="reg-field-10" className="hms-label">Department / Ward</label>
                  <input
                    id="reg-field-10"
                    className={inputClass}
                    value={form.department}
                    onChange={(e) => setField("department", e.target.value)}
                  />
                </div>
              </>
            )}

            {(role === "Compounder" || role === "Receptionist") && (
              <>
                <div>
                  <label htmlFor="reg-field-11" className="hms-label">Employee / Staff ID</label>
                  <input
                    id="reg-field-11"
                    className={inputClass}
                    value={form.employee_id}
                    onChange={(e) => setField("employee_id", e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="reg-field-12" className="hms-label">Department</label>
                  <input
                    id="reg-field-12"
                    className={inputClass}
                    value={form.department}
                    onChange={(e) => setField("department", e.target.value)}
                  />
                </div>
              </>
            )}

            {role === "Admin" && (
              <div>
                <label htmlFor="reg-field-13" className="hms-label">Admin Invitation Code</label>
                <input
                  id="reg-field-13"
                  className={inputClass}
                  value={form.invite_code}
                  onChange={(e) => setField("invite_code", e.target.value)}
                  placeholder="Required — issued by an existing admin"
                />
              </div>
            )}

            <div>
              <label htmlFor="reg-field-14" className="hms-label">Password</label>
              <input
                id="reg-field-14"
                type="password"
                className={inputClass}
                value={form.password}
                onChange={(e) => setField("password", e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            <div>
              <label htmlFor="reg-field-15" className="hms-label">Confirm Password</label>
              <input
                id="reg-field-15"
                type="password"
                className={inputClass}
                value={form.confirm_password}
                onChange={(e) => setField("confirm_password", e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              disabled={loading || Boolean(pendingEmail)}
              className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>

          {pendingEmail && (
            <form onSubmit={handleVerifyEmail} className="mt-6 space-y-4 border-t border-line pt-6">
              <div>
                <h2 className="text-sm font-semibold text-ink-900">Verify email</h2>
                <p className="text-xs text-gray-500 mt-1">
                  {otpMessage || `Enter the code sent for ${pendingEmail}.`}
                </p>
              </div>
              <div>
                <label htmlFor="reg-field-16" className="hms-label">Email OTP</label>
                <input
                  id="reg-field-16"
                  className={inputClass}
                  inputMode="numeric"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="Enter the 6-digit code"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loading || verified}
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {verified ? "Email verified" : "Verify OTP"}
              </button>
              <div className="flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={handleResendEmail}
                  disabled={loading || verified}
                  className="rounded text-[13px] font-medium text-brand-700 hover:underline disabled:opacity-50"
                >
                  Resend email OTP
                </button>
                {verified && (
                  <Link
                    to={`/patient-login?role=Patient&email=${encodeURIComponent(pendingEmail)}`}
                    className="rounded text-[13px] font-medium text-brand-700 hover:underline disabled:opacity-50"
                  >
                    Sign in
                  </Link>
                )}
              </div>
            </form>
          )}

          <div className="mt-6 text-center text-[13px] text-ink-500">
            <p>Already have an account?</p>
            <Link
              to={`/patient-login?role=${encodeURIComponent(role)}`}
              className="mt-1 inline-block font-medium text-brand-700 hover:underline"
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Register
