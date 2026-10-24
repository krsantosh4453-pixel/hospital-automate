import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../assets/context/AuthContext.jsx"
import api from "../services/api.js"

function StaffLogin() {
  const navigate = useNavigate()
  const { staffLoginStartOtp, staffOtpVerify, staffOtpResend, applyDevelopmentAccess, devBypassAvailable } = useAuth()

  const [step, setStep] = useState("credentials")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [otp, setOtp] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [challenge, setChallenge] = useState(null)
  const [notice, setNotice] = useState("")
  const [resetCode, setResetCode] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [staffRole, setStaffRole] = useState("")
  const [maskedPhone, setMaskedPhone] = useState("")

  const handleCredentialsSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      const data = await staffLoginStartOtp(username, password)
      if (data.otp_required) {
        setChallenge(data.challenge)
        setStaffRole(data.staff_role)
        setMaskedPhone(data.message.match(/\((.*?)\)/)?.[1] || "******")
        setStep("otp")
        setError("")
      } else {
        setError(data.message || "Failed to start OTP verification.")
      }
    } catch (err) {
      setError(err.message || "Login failed. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const handleOtpSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      await staffOtpVerify(challenge, otp)
      navigate("/")
    } catch (err) {
      setError(err.message || "Invalid or expired OTP.")
    } finally {
      setLoading(false)
    }
  }

  const handleResendOtp = async () => {
    setError("")
    setLoading(true)

    try {
      await staffOtpResend(challenge)
      setOtp("")
    } catch (err) {
      setError(err.message || "Failed to resend OTP.")
    } finally {
      setLoading(false)
    }
  }

  const handleDevelopmentAccess = () => {
    applyDevelopmentAccess()
    navigate("/")
  }

  const handleResetRequest = async (e) => {
    e.preventDefault()
    setError("")
    setNotice("")
    setLoading(true)
    try {
      const data = await api.auth.requestPasswordReset(username)
      setNotice(data.message)
      setStep("reset-confirm")
    } catch (err) {
      setError(err.message || "Could not start password reset.")
    } finally {
      setLoading(false)
    }
  }

  const handleResetConfirm = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const data = await api.auth.confirmPasswordReset(username, resetCode, newPassword)
      setNotice(data.message)
      setPassword("")
      setResetCode("")
      setNewPassword("")
      setStep("credentials")
    } catch (err) {
      setError(err.message || "Could not reset password.")
    } finally {
      setLoading(false)
    }
  }

  const goBackToCredentials = () => {
    setStep("credentials")
    setOtp("")
    setError("")
    setChallenge(null)
    setStaffRole("")
    setMaskedPhone("")
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg text-white text-3xl font-bold">
            🏥
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mt-4">
            Hospital Management System
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Staff Portal Login
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8">
          <div className="mb-6">
            <h2 className="text-lg font-bold text-gray-800">
              {step === "credentials"
                ? "Sign in to your account"
                : step === "otp"
                  ? "Verify your identity"
                  : "Reset your password"}
            </h2>
            <p className="text-gray-500 text-xs mt-0.5">
              {step === "credentials"
                ? "Enter your credentials to access the hospital system"
                : step === "otp"
                  ? `Enter the 6-digit code sent to your mobile number (${maskedPhone})`
                  : "A code is sent to the mobile number registered on your staff account"}
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
              {error}
            </div>
          )}

          {notice && !error && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm" role="status">
              {notice}
            </div>
          )}

          {step === "reset-request" || step === "reset-confirm" ? (
            <form onSubmit={step === "reset-request" ? handleResetRequest : handleResetConfirm} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5" htmlFor="reset-username">
                  Username or Email
                </label>
                <input
                  id="reset-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                  required
                  autoComplete="username"
                  disabled={loading || step === "reset-confirm"}
                />
              </div>
              {step === "reset-confirm" && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1.5" htmlFor="reset-code">
                      Code from SMS
                    </label>
                    <input
                      id="reset-code"
                      type="text"
                      inputMode="numeric"
                      maxLength={8}
                      value={resetCode}
                      onChange={(e) => setResetCode(e.target.value.replace(/\D/g, ""))}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                      required
                      disabled={loading}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1.5" htmlFor="reset-password">
                      New Password
                    </label>
                    <input
                      id="reset-password"
                      type="password"
                      minLength={8}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                      required
                      autoComplete="new-password"
                      disabled={loading}
                    />
                  </div>
                </>
              )}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm disabled:opacity-50"
              >
                {loading ? "Please wait..." : step === "reset-request" ? "Send Reset Code" : "Set New Password"}
              </button>
              <button
                type="button"
                onClick={goBackToCredentials}
                className="text-blue-600 hover:text-blue-700 cursor-pointer text-xs"
                disabled={loading}
              >
                ← Back to sign in
              </button>
            </form>
          ) : step === "credentials" ? (
            <form onSubmit={handleCredentialsSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">
                  Username or Email
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter username or email"
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                  required
                  autoComplete="username"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                  required
                  autoComplete="current-password"
                  disabled={loading}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Sending OTP..." : "Send OTP"}
              </button>
              <button
                type="button"
                onClick={() => { setError(""); setNotice(""); setStep("reset-request") }}
                className="text-blue-600 hover:text-blue-700 cursor-pointer text-xs"
                disabled={loading}
              >
                Forgot password?
              </button>
            </form>
          ) : (
            <form onSubmit={handleOtpSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">
                  6-Digit OTP Code
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, "")
                    if (val.length <= 6) setOtp(val)
                  }}
                  placeholder="• • • • • •"
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-center text-xl tracking-[0.5em] font-bold outline-none focus:ring-2 focus:ring-blue-500"
                  required
                  disabled={loading}
                  autoFocus
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm disabled:opacity-50"
              >
                {loading ? "Verifying..." : "Verify & Continue"}
              </button>

              <div className="flex items-center justify-between mt-4 text-xs">
                <button
                  type="button"
                  onClick={goBackToCredentials}
                  className="text-blue-600 hover:text-blue-700 cursor-pointer"
                  disabled={loading}
                >
                  ← Back to credentials
                </button>
                <button
                  type="button"
                  onClick={handleResendOtp}
                  className="text-gray-500 hover:text-gray-700 cursor-pointer disabled:text-gray-300"
                  disabled={loading}
                >
                  Resend OTP
                </button>
              </div>
            </form>
          )}

          {devBypassAvailable && (
          <div className="mt-6 border-t border-gray-200 pt-5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-2">
              Temporary Development Access
            </p>
            <button
              type="button"
              onClick={handleDevelopmentAccess}
              className="w-full bg-amber-500 hover:bg-amber-600 text-white py-3 rounded-xl font-semibold text-sm transition cursor-pointer shadow-sm"
            >
              Development Access – OTP temporarily bypassed
            </button>
            <p className="text-[11px] text-gray-500 mt-2">
              This bypass is intended for local development only and can be removed later by setting
              <span className="font-semibold text-gray-700"> VITE_DEV_AUTH_BYPASS=false</span>.
            </p>
          </div>
          )}

          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">
              Patient?{" "}
              <a href="/patient-login" className="text-blue-600 hover:text-blue-700 font-medium">
                Create Patient Account / Sign In
              </a>
            </p>
            <p className="text-[11px] text-gray-400 mt-1">
              Patients can create accounts via Mobile OTP, Google, or Token.
            </p>
          </div>

          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">New to the Hospital Management System?</p>
            <a
              href="/register?role=Doctor"
              className="inline-block mt-2 text-sm font-semibold text-blue-600 hover:text-blue-700"
            >
              Create Account
            </a>
            <p className="text-[11px] text-gray-400 mt-1">
              Staff registrations stay pending until an administrator approves them.
            </p>
          </div>

          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">
              Don&apos;t have a staff account?{" "}
              <span className="text-blue-600 hover:text-blue-700 font-medium cursor-pointer">
                Contact Hospital Admin
              </span>
            </p>
            <p className="text-[11px] text-gray-400 mt-1">
              Staff accounts are created by hospital administrators.
            </p>
          </div>

          {devBypassAvailable && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 text-center">
              Demo credentials (local seed data only):
              <br />
              <span className="font-mono text-gray-700">doctor_a / testpass123</span> (Doctor - Hospital A)
              <br />
              <span className="font-mono text-gray-700">nurse_b / testpass123</span> (Nurse - Hospital B)
            </p>
          </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default StaffLogin