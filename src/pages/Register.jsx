import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import api from "../services/api.js"
import {
  LOGIN_ROLES,
  getSelectedLoginRole,
  saveSelectedLoginRole,
} from "../utils/roleRouting.js"

const inputClass =
  "w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"

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
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg text-white text-3xl font-bold">
            🏥
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mt-4">
            Hospital Management System
          </h1>
          <p className="text-gray-500 text-sm mt-1">Create Account</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8">
          <div className="mb-6">
            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider text-center mb-3">
              Select Role
            </p>
            <div className="grid grid-cols-3 gap-2">
              {LOGIN_ROLES.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setRole(item)}
                  className={`py-2 px-2 text-[11px] font-semibold rounded-xl border transition cursor-pointer ${
                    role === item
                      ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                      : "bg-gray-50 text-gray-700 border-gray-200 hover:border-blue-300"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-gray-400 mt-3 text-center">
              {role} Registration
            </p>
          </div>

          {role === "Admin" && (
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs">
              Admin accounts cannot be created from the role selector alone.
              An invitation code from an existing administrator is required.
            </div>
          )}

          {["Doctor", "Nurse", "Compounder", "Receptionist"].includes(role) && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-xs">
              {role} registrations stay pending until a hospital administrator
              activates the staff profile. Selecting {role} here does not grant
              {` ${role} `} access by itself.
            </div>
          )}

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Full Name</label>
              <input
                className={inputClass}
                value={form.full_name}
                onChange={(e) => setField("full_name", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Mobile Number</label>
              <div className="flex">
                <span className="flex items-center px-3.5 border border-r-0 border-gray-300 rounded-l-xl bg-gray-50 text-gray-600 text-sm">
                  +91
                </span>
                <input
                  type="tel"
                  className="w-full border border-gray-300 rounded-r-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
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
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Email</label>
              <input
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
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Date of Birth</label>
                  <input
                    type="date"
                    className={inputClass}
                    value={form.date_of_birth}
                    onChange={(e) => setField("date_of_birth", e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Gender</label>
                  <select
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
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Address</label>
                  <input
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
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    Medical Registration / License Number
                  </label>
                  <input
                    className={inputClass}
                    value={form.license_number}
                    onChange={(e) => setField("license_number", e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Specialization</label>
                  <input
                    className={inputClass}
                    value={form.specialization}
                    onChange={(e) => setField("specialization", e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Experience</label>
                  <input
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
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    Nursing Registration / ID
                  </label>
                  <input
                    className={inputClass}
                    value={form.nursing_registration}
                    onChange={(e) => setField("nursing_registration", e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Department / Ward</label>
                  <input
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
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    Employee / Staff ID
                  </label>
                  <input
                    className={inputClass}
                    value={form.employee_id}
                    onChange={(e) => setField("employee_id", e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">Department</label>
                  <input
                    className={inputClass}
                    value={form.department}
                    onChange={(e) => setField("department", e.target.value)}
                  />
                </div>
              </>
            )}

            {role === "Admin" && (
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">
                  Admin Invitation Code
                </label>
                <input
                  className={inputClass}
                  value={form.invite_code}
                  onChange={(e) => setField("invite_code", e.target.value)}
                  placeholder="Required — issued by an existing admin"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Password</label>
              <input
                type="password"
                className={inputClass}
                value={form.password}
                onChange={(e) => setField("password", e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Confirm Password</label>
              <input
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
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm disabled:opacity-50"
            >
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>

          {pendingEmail && (
            <form onSubmit={handleVerifyEmail} className="mt-6 space-y-4 border-t border-gray-100 pt-6">
              <div>
                <h2 className="text-sm font-bold text-gray-800">Verify email</h2>
                <p className="text-xs text-gray-500 mt-1">
                  {otpMessage || `Enter the code sent for ${pendingEmail}.`}
                </p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Email OTP</label>
                <input
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
                className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm disabled:opacity-50"
              >
                {verified ? "Email verified" : "Verify OTP"}
              </button>
              <div className="flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={handleResendEmail}
                  disabled={loading || verified}
                  className="text-blue-600 hover:text-blue-700 cursor-pointer disabled:opacity-50"
                >
                  Resend email OTP
                </button>
                {verified && (
                  <Link
                    to={`/patient-login?role=Patient&email=${encodeURIComponent(pendingEmail)}`}
                    className="font-semibold text-blue-600 hover:text-blue-700"
                  >
                    Sign in
                  </Link>
                )}
              </div>
            </form>
          )}

          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">Already have an account?</p>
            <Link
              to={`/patient-login?role=${encodeURIComponent(role)}`}
              className="inline-block mt-2 text-sm font-semibold text-blue-600 hover:text-blue-700"
            >
              Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Register
