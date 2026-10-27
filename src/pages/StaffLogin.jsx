import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../assets/context/AuthContext.jsx"
import api from "../services/api.js"
import { Link } from "react-router-dom"
import { ArrowLeft, KeyRound, LockKeyhole, ShieldCheck, UserRound } from "lucide-react"
import { BrandMark } from "../components/Sidebar.jsx"
import DevLoginPanel from "../components/DevLoginPanel.jsx"
import { Alert, Button, Field, Input } from "../components/ui"

function StaffLogin() {
  const navigate = useNavigate()
  const { staffLogin, staffLoginStartOtp, staffOtpVerify, staffOtpResend, applyDevelopmentAccess, devBypassAvailable } = useAuth()

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
      let data
      try {
        data = await staffLoginStartOtp(username, password)
      } catch (otpError) {
        // SMS OTP cannot be used (switched off, not set up, or no mobile
        // number): sign in with the password. The server refuses this when
        // its policy requires OTP.
        if (otpError.body?.otp_unavailable) {
          await staffLogin(username, password)
          navigate("/")
          return
        }
        throw otpError
      }
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

  const titles = {
    credentials: ["Sign in", "Use your hospital staff account."],
    otp: ["Enter the code", `We sent a 6-digit code to your mobile (${maskedPhone}).`],
    "reset-request": ["Reset your password", "A code is sent to the mobile number registered on your staff account."],
    "reset-confirm": ["Reset your password", "Enter the code from the SMS and choose a new password."],
  }
  const [title, subtitle] = titles[step] || titles.credentials

  return (
    <div className="flex min-h-screen">
      {/* Brand panel (large screens) */}
      <aside className="relative hidden w-[44%] max-w-xl flex-col justify-between bg-brand-950 px-12 py-10 text-white lg:flex">
        <BrandMark />
        <div>
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Calm, connected care
            <br />
            across every ward.
          </h1>
          <ul className="mt-8 space-y-4 text-[15px] text-brand-100/90">
            <li className="flex gap-3">
              <ShieldCheck size={20} className="mt-0.5 shrink-0 text-brand-300" aria-hidden="true" />
              Every hospital&apos;s records stay separate; you only see the hospitals you belong to.
            </li>
            <li className="flex gap-3">
              <LockKeyhole size={20} className="mt-0.5 shrink-0 text-brand-300" aria-hidden="true" />
              Sign-in is confirmed with a one-time code sent to your registered mobile.
            </li>
            <li className="flex gap-3">
              <UserRound size={20} className="mt-0.5 shrink-0 text-brand-300" aria-hidden="true" />
              Every change to a patient record is attributed and kept in the audit trail.
            </li>
          </ul>
        </div>
        <p className="text-xs text-brand-200/60">For authorised hospital staff only.</p>
      </aside>

      {/* Form */}
      <main className="flex flex-1 items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-[26rem]">
          <div className="mb-8 lg:hidden">
            <BrandMark inverted={false} />
          </div>

          <DevLoginPanel />

          <div className="hms-surface-dark rounded-2xl border border-line p-6 shadow-xl shadow-ink-900/5 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-brand-700">Staff portal</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-ink-900">{title}</h2>
            <p className="mt-1 text-sm text-ink-500">{subtitle}</p>

            <div className="mt-6 space-y-4">
              {error && <Alert tone="danger">{error}</Alert>}
              {notice && !error && <Alert tone="success">{notice}</Alert>}

              {step === "reset-request" || step === "reset-confirm" ? (
                <form onSubmit={step === "reset-request" ? handleResetRequest : handleResetConfirm} className="space-y-4">
                  <Field label="Username or email" required>
                    <Input
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      autoComplete="username"
                      disabled={loading || step === "reset-confirm"}
                    />
                  </Field>
                  {step === "reset-confirm" && (
                    <>
                      <Field label="Code from SMS" required>
                        <Input
                          inputMode="numeric"
                          maxLength={8}
                          value={resetCode}
                          onChange={(e) => setResetCode(e.target.value.replace(/\D/g, ""))}
                          disabled={loading}
                          autoComplete="one-time-code"
                        />
                      </Field>
                      <Field label="New password" required hint="At least 8 characters.">
                        <Input
                          type="password"
                          minLength={8}
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          autoComplete="new-password"
                          disabled={loading}
                        />
                      </Field>
                    </>
                  )}
                  <Button type="submit" size="lg" loading={loading} className="w-full justify-center">
                    {step === "reset-request" ? "Send reset code" : "Set new password"}
                  </Button>
                  <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={goBackToCredentials} disabled={loading}>
                    Back to sign in
                  </Button>
                </form>
              ) : step === "credentials" ? (
                <form onSubmit={handleCredentialsSubmit} className="space-y-4">
                  <Field label="Username or email" required>
                    <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" disabled={loading} autoFocus />
                  </Field>
                  <Field label="Password" required>
                    <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" disabled={loading} />
                  </Field>
                  <Button type="submit" size="lg" loading={loading} className="w-full justify-center">
                    Continue
                  </Button>
                  <button
                    type="button"
                    onClick={() => {
                      setError("")
                      setNotice("")
                      setStep("reset-request")
                    }}
                    className="inline-flex items-center gap-1.5 rounded text-[13px] font-medium text-brand-700 hover:underline"
                    disabled={loading}
                  >
                    <KeyRound size={14} aria-hidden="true" /> Forgot password?
                  </button>
                </form>
              ) : (
                <form onSubmit={handleOtpSubmit} className="space-y-4">
                  <Field label="6-digit code" required>
                    <Input
                      inputMode="numeric"
                      maxLength={6}
                      value={otp}
                      onChange={(e) => {
                        const val = e.target.value.replace(/\D/g, "")
                        if (val.length <= 6) setOtp(val)
                      }}
                      className="h-12 text-center text-xl font-semibold tracking-[0.5em]"
                      disabled={loading}
                      autoFocus
                      autoComplete="one-time-code"
                    />
                  </Field>
                  <Button type="submit" size="lg" loading={loading} className="w-full justify-center">
                    Verify and continue
                  </Button>
                  <div className="flex items-center justify-between">
                    <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={goBackToCredentials} disabled={loading}>
                      Back
                    </Button>
                    <Button variant="ghost" size="sm" onClick={handleResendOtp} disabled={loading}>
                      Resend code
                    </Button>
                  </div>
                </form>
              )}
            </div>

            {devBypassAvailable && (
              <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">Local development only</p>
                <Button variant="secondary" size="sm" onClick={handleDevelopmentAccess} className="mt-2 w-full justify-center">
                  Development access (OTP bypassed)
                </Button>
                <p className="mt-2 text-xs text-amber-800">
                  Disable with <code className="font-mono">VITE_DEV_AUTH_BYPASS=false</code>. Seed accounts:{" "}
                  <span className="font-mono">doctor_a</span>, <span className="font-mono">nurse_b</span> (password in the seed data).
                </p>
              </div>
            )}
          </div>

          <div className="mt-6 space-y-2 text-center text-[13px] text-ink-500">
            <p>
              New staff member? Ask your hospital&apos;s administrator for an invitation — it has the link to set your password.
            </p>
            <p>
              Patient?{" "}
              <Link to="/patient-login" className="font-medium text-brand-700 hover:underline">Sign in to the patient portal</Link>
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

export default StaffLogin
