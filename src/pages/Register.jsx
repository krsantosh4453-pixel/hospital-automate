import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import api from "../services/api.js"
import {
  LOGIN_ROLES,
  getSelectedLoginRole,
  saveSelectedLoginRole,
} from "../utils/roleRouting.js"
import { BrandMark } from "../components/Sidebar.jsx"
import { Alert, Button } from "../components/ui"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { AuthLink, useAuthNavigate, useInSignInDialog } from "../components/auth/SignInDialog.jsx"

const inputClass = "hms-input w-full"

// Staff (Doctor, Nurse, Compounder, Receptionist) join a hospital only by its
// invitation; the backend refuses them here.
const REGISTER_ROLES = LOGIN_ROLES.filter((item) => item === "Patient" || item === "Admin")
const MOBILE_DIGITS = 10

/** The sign-in route for `role`, keeping the booking hand-off (?next=book) PatientLogin understands. */
function signInPath(role, next, email = "") {
  const params = new URLSearchParams({ role })
  if (email) params.set("email", email)
  if (next === "book") params.set("next", "book")
  return `/patient-login?${params}`
}

function Register() {
  const { t } = useLanguage()
  // Opened from the sign-in dialog, the form stays in that dialog over the page.
  const inDialog = useInSignInDialog()
  const authNavigate = useAuthNavigate()
  const [searchParams] = useSearchParams()
  const next = searchParams.get("next")

  const initialRole = useMemo(() => {
    const fromQuery = searchParams.get("role")
    if (REGISTER_ROLES.includes(fromQuery)) return saveSelectedLoginRole(fromQuery)
    const remembered = getSelectedLoginRole()
    return REGISTER_ROLES.includes(remembered) ? remembered : "Patient"
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
    invite_code: "",
    hospital: "",
  })
  // Prompt 3: hospitals a patient may choose (GET /api/auth/patient/hospitals/).
  // The server decides which are open; the choice gives the patient a UHID there.
  const [hospitals, setHospitals] = useState({ state: "loading", data: [] })
  const [hospitalsReload, setHospitalsReload] = useState(0)
  const [registeredAt, setRegisteredAt] = useState(null)

  useEffect(() => {
    saveSelectedLoginRole(role)
  }, [role])

  useEffect(() => {
    let cancelled = false
    setHospitals({ state: "loading", data: [] })
    api.auth
      .selfRegistrationHospitals()
      .then((data) => !cancelled && setHospitals({ state: "loaded", data: Array.isArray(data) ? data : data?.results || [] }))
      .catch(() => !cancelled && setHospitals({ state: "failed", data: [] }))
    return () => {
      cancelled = true
    }
  }, [hospitalsReload])

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
    // An old error must not look like the answer to the next submit, which the
    // browser itself may block (e.g. a date of birth after `max`).
    setError("")
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setSuccess("")

    if (form.password !== form.confirm_password) {
      setError("Password and confirm password do not match.")
      return
    }
    if (form.phone.length !== MOBILE_DIGITS) {
      setError("Enter a valid 10-digit mobile number.")
      return
    }
    if (role === "Patient") {
      if (hospitals.state === "loading") {
        setError("Hospitals are still loading. Please wait a moment.")
        return
      }
      if (hospitals.state === "failed") {
        setError("Hospitals could not be loaded. Try again before creating the account.")
        return
      }
      // Required whenever any hospital accepts online registration.
      if (hospitals.data.length > 0 && !form.hospital) {
        setError("Choose the hospital where you want to be registered.")
        return
      }
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
        if (form.hospital) payload.hospital = form.hospital
      }
      if (role === "Admin") {
        payload.invite_code = form.invite_code
      }

      const data = await api.auth.register(payload)

      if (role === "Patient" && data.patient) {
        setRegisteredAt(data.patient.hospitals?.[0] || null)
        setPendingEmail(data.user?.email || form.email)
        setOtpMessage(data.verification?.message || data.message || "Account created.")
        setSuccess(data.message || "Patient account created.")
        return
      }

      setSuccess(data.message || "Account created.")
      setTimeout(() => {
        authNavigate(signInPath(role, next))
      }, 1200)
    } catch (err) {
      setError(err.message || "Registration failed.")
    } finally {
      setLoading(false)
    }
  }

  return (
    // Inside the sign-in dialog the dialog supplies the frame and title (as on PatientLogin).
    <div className={inDialog ? "" : "min-h-screen flex items-center justify-center px-4 py-8"}>
      <div className={inDialog ? "" : "w-full max-w-[28rem]"}>
        {inDialog ? (
          <p className="mb-5 text-sm text-ink-500">{t("Patients can sign in once their email is verified. Doctors, nurses and other staff join by an invitation from their hospital.")}</p>
        ) : (
          <div className="mb-8">
            <BrandMark inverted={false} />
            <h1 className="mt-6 text-2xl font-semibold tracking-tight text-ink-900">{t("Create an account")}</h1>
            <p className="mt-1 text-sm text-ink-500">{t("Patients can sign in once their email is verified. Doctors, nurses and other staff join by an invitation from their hospital.")}</p>
          </div>
        )}

        <div className={inDialog ? "" : "hms-surface-dark rounded-2xl border border-line p-6 shadow-xl shadow-ink-900/5 sm:p-8"}>
          <div className="mb-6">
            <p id="register-role-label" className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-ink-500">
              {t("Account type")}
            </p>
            <div className="grid grid-cols-2 gap-1.5" role="radiogroup" aria-labelledby="register-role-label">
              {REGISTER_ROLES.map((item) => (
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
              {t("Admin accounts cannot be created from the role selector alone. An invitation code from an existing administrator is required.")}
            </Alert>
          )}

          {role === "Patient" && (
            <Alert tone="info" className="mb-4">
              {t("Hospital staff do not sign up here. Your hospital's administrator sends you an invitation link to set your password.")}
            </Alert>
          )}

          {error && (
            <Alert tone="danger" className="mb-4">{error}</Alert>
          )}
          {success && (
            <Alert tone="success" className="mb-4">
              {success}
              {registeredAt && (
                <span className="mt-1 block">
                  {t("Registered at {hospital}. Your patient ID (UHID) there is", { hospital: registeredAt.name })}{" "}
                  <strong className="tabular-nums">{registeredAt.uhid}</strong>.
                </span>
              )}
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="reg-field-1" className="hms-label">{t("Full Name")}</label>
              <input
                id="reg-field-1"
                className={inputClass}
                value={form.full_name}
                onChange={(e) => setField("full_name", e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="reg-field-phone" className="hms-label">{t("Mobile Number")}</label>
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
                  placeholder={t("Enter 10-digit number")}
                  required
                />
              </div>
            </div>
            <div>
              <label htmlFor="reg-field-2" className="hms-label">{t("Email")}</label>
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
                  <label htmlFor="reg-field-3" className="hms-label">{t("Date of Birth")}</label>
                  <input
                    id="reg-field-3"
                    type="date"
                    required
                    max={new Date().toISOString().slice(0, 10)}
                    className={inputClass}
                    value={form.date_of_birth}
                    onChange={(e) => setField("date_of_birth", e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="reg-field-4" className="hms-label">{t("Gender")}</label>
                  <select
                    id="reg-field-4"
                    className={inputClass}
                    value={form.gender}
                    onChange={(e) => setField("gender", e.target.value)}
                  >
                    <option value="Male">{t("Male")}</option>
                    <option value="Female">{t("Female")}</option>
                    <option value="Other">{t("Other")}</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="reg-field-5" className="hms-label">{t("Address")}</label>
                  <input
                    id="reg-field-5"
                    className={inputClass}
                    value={form.address}
                    onChange={(e) => setField("address", e.target.value)}
                  />
                </div>
                <HospitalChoice
                  hospitals={hospitals}
                  value={form.hospital}
                  onChange={(value) => setField("hospital", value)}
                  onRetry={() => setHospitalsReload((n) => n + 1)}
                />
              </>
            )}

            {role === "Admin" && (
              <div>
                <label htmlFor="reg-field-13" className="hms-label">{t("Admin Invitation Code")}</label>
                <input
                  id="reg-field-13"
                  className={inputClass}
                  value={form.invite_code}
                  onChange={(e) => setField("invite_code", e.target.value)}
                  placeholder={t("Required — issued by an existing admin")}
                />
              </div>
            )}

            <div>
              <label htmlFor="reg-field-14" className="hms-label">{t("Password")}</label>
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
              <label htmlFor="reg-field-15" className="hms-label">{t("Confirm Password")}</label>
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
              {loading ? t("Creating account...") : t("Create Account")}
            </button>
          </form>

          {pendingEmail && (
            <form onSubmit={handleVerifyEmail} className="mt-6 space-y-4 border-t border-line pt-6">
              <div>
                <h2 className="text-sm font-semibold text-ink-900">{t("Verify email")}</h2>
                <p className="text-xs text-gray-500 mt-1">
                  {otpMessage || t("Enter the code sent for {pendingEmail}.", { pendingEmail })}
                </p>
              </div>
              <div>
                <label htmlFor="reg-field-16" className="hms-label">{t("Email OTP")}</label>
                <input
                  id="reg-field-16"
                  className={inputClass}
                  inputMode="numeric"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder={t("Enter the 6-digit code")}
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loading || verified}
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {verified ? t("Email verified") : t("Verify OTP")}
              </button>
              <div className="flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={handleResendEmail}
                  disabled={loading || verified}
                  className="rounded text-[13px] font-medium text-brand-700 hover:underline disabled:opacity-50"
                >
                  {t("Resend email OTP")}
                </button>
                {verified && (
                  <AuthLink
                    to={signInPath("Patient", next, pendingEmail)}
                    className="rounded text-[13px] font-medium text-brand-700 hover:underline disabled:opacity-50"
                  >
                    {t("Sign in")}
                  </AuthLink>
                )}
              </div>
            </form>
          )}

          <div className="mt-6 text-center text-[13px] text-ink-500">
            <p>{t("Already have an account?")}</p>
            <AuthLink
              to={signInPath(role, next)}
              className="mt-1 inline-block font-medium text-brand-700 hover:underline"
            >
              {t("Sign in")}
            </AuthLink>
          </div>
        </div>
      </div>
    </div>
  )
}

/** The hospital to register at, from the server's list of open hospitals. */
function HospitalChoice({ hospitals, value, onChange, onRetry }) {
  const { t } = useLanguage()
  if (hospitals.state === "loading") {
    return <p className="text-sm text-ink-500">{t("Loading hospitals…")}</p>
  }
  if (hospitals.state === "failed") {
    return (
      <Alert tone="danger">
        {t("Hospitals could not be loaded.")}{" "}
        <Button size="sm" variant="secondary" onClick={onRetry}>{t("Try again")}</Button>
      </Alert>
    )
  }
  if (hospitals.data.length === 0) {
    return <Alert tone="info">{t("No hospital accepts online registration at the moment. You can still create your account; the hospital's reception will register you there.")}</Alert>
  }
  return (
    <div>
      <label htmlFor="reg-field-hospital" className="hms-label">{t("Hospital")}</label>
      <select
        id="reg-field-hospital"
        className={inputClass}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
      >
        <option value="">{t("Select hospital")}</option>
        {hospitals.data.map((h) => (
          <option key={h.id} value={h.id}>{h.city ? `${h.name} (${h.city})` : h.name}</option>
        ))}
      </select>
      <p className="mt-1 text-xs text-ink-500">{t("You get a patient ID (UHID) at this hospital and can book appointments there.")}</p>
    </div>
  )
}

export default Register
