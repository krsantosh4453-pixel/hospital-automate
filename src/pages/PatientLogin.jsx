import { useEffect, useState, useRef } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { useAuth } from "../assets/context/AuthContext.jsx"
import api from "../services/api.js"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import {
  LOGIN_ROLES,
  getSelectedLoginRole,
  saveSelectedLoginRole,
} from "../utils/roleRouting.js"
import { MailIcon, SmartphoneIcon, TicketIcon } from "lucide-react"
import { useToast } from "../components/Toast.jsx"
import { BrandMark } from "../components/Sidebar.jsx"
import { Alert } from "../components/ui"
import DevLoginPanel from "../components/DevLoginPanel.jsx"

function PatientLogin() {
  const toast = useToast()

  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  // From the public "Book appointment" button: open the booking form after sign-in.
  const afterPatientLogin = searchParams.get("next") === "book" ? "/patient/appointments?book=1" : "/patient"
  const { patientLogin, staffLogin, adoptExternalSession } = useAuth()
  const { savePatient } = usePatient()
  const { switchRole } = useRole()

  const [selectedRole, setSelectedRole] = useState(() => {
    const fromQuery = searchParams.get("role")
    if (LOGIN_ROLES.includes(fromQuery)) return saveSelectedLoginRole(fromQuery)
    return getSelectedLoginRole()
  })

  // Login modes: "mobile", "token", "email"
  const [loginMode, setLoginMode] = useState(searchParams.get("email") ? "email" : "mobile")

  // Mobile & OTP states
  const [step, setStep] = useState("mobile")
  const [mobile, setMobile] = useState("")
  const [otp, setOtp] = useState("")

  // Token number states
  const [tokenInput, setTokenInput] = useState("")
  const [tokenPassword, setTokenPassword] = useState("")
  const [tokenError, setTokenError] = useState("")
  const [otpError, setOtpError] = useState("")
  const [otpNotice, setOtpNotice] = useState("")
  const [showEmailFallback, setShowEmailFallback] = useState(false)
  const [otpLoading, setOtpLoading] = useState(false)
  const [emailAddress, setEmailAddress] = useState(searchParams.get("email") || "")
  const [emailPassword, setEmailPassword] = useState("")
  const [emailError, setEmailError] = useState("")
  const [emailNotice, setEmailNotice] = useState("")
  const [emailOtp, setEmailOtp] = useState("")
  const [emailStep, setEmailStep] = useState("credentials")

  // Google login states
  const [googleLoading, setGoogleLoading] = useState(false)
  const [googleStatus, setGoogleStatus] = useState("")
  const googleBtnRef = useRef(null)

  const [staffUsername, setStaffUsername] = useState("")
  const [staffPassword, setStaffPassword] = useState("")
  const [staffError, setStaffError] = useState("")
  const [staffLoading, setStaffLoading] = useState(false)

  useEffect(() => {
    saveSelectedLoginRole(selectedRole)
  }, [selectedRole])

  const GOOGLE_CLIENT_ID =
    import.meta.env.VITE_GOOGLE_CLIENT_ID ||
    "1199500530711-s1ti1g061cno8d3tk2759hqrgitdect.apps.googleusercontent.com"

  // Google Identity Services load
  useEffect(() => {
    let script = document.getElementById("google-gsi-script")

    if (!script) {
      script = document.createElement("script")
      script.id = "google-gsi-script"
      script.src = "https://accounts.google.com/gsi/client"
      script.async = true
      script.defer = true
      document.body.appendChild(script)
    }

    const initGsi = () => {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleResponse,
          auto_select: false,
        })

        // Also render standard Google button if element exists
        if (googleBtnRef.current) {
          window.google.accounts.id.renderButton(googleBtnRef.current, {
            theme: "outline",
            size: "large",
            width: 320,
            text: "continue_with",
            shape: "pill",
          })
        }
      }
    }

    if (window.google?.accounts?.id) {
      initGsi()
    } else {
      script.onload = initGsi
    }
  }, [])

  // Handle Google OAuth Response
  const handleGoogleResponse = async (response) => {
    if (!response || !response.credential) {
      toast.warning("No credential received from Google.")
      return
    }

    try {
      setGoogleLoading(true)
      setGoogleStatus("Verifying with backend...")

      // Through the shared client so the session arrives as httpOnly cookies.
      const data = await api.auth.googleLogin(response.credential)

      if (data.status !== "success" || !(data.access || data.session === "cookie")) {
        throw new Error(data.error || "Google verification failed.")
      }

      await adoptExternalSession(data)
      if (data.account_type === "staff") {
        navigate("/")
        return
      }

      if (data.patient) savePatient(data.patient)
      switchRole(data.account_type === "staff" ? data.user?.staff_role : "Patient")

      setGoogleStatus("Login successful! Redirecting...")
      setTimeout(() => {
        navigate(data.account_type === "staff" ? "/" : afterPatientLogin)
      }, 500)
    } catch (error) {
      console.error("Google login error:", error)
      toast.error(`Google Login Error: ${error.message || "Could not connect to server."}`)
    } finally {
      setGoogleLoading(false)
      setGoogleStatus("")
    }
  }

  // Trigger Google Login popup
  const handleGoogleLogin = () => {
    if (!window.google?.accounts?.id) {
      toast.warning("Google Services are loading. Please try again in 2 seconds.")
      return
    }

    try {
      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed()) {
          // If prompt blocked by third-party cookies or origin policy
          console.warn("Google prompt not displayed:", notification.getNotDisplayedReason())
        }
      })
    } catch (err) {
      console.error("Prompt error:", err)
    }
  }

  const handleSendOTP = async (e) => {
    e?.preventDefault()
    setOtpError("")

    if (mobile.length !== 10) {
      setOtpError("Please enter a valid 10-digit mobile number.")
      return
    }

    setOtpLoading(true)
    try {
      const data = await api.auth.requestPatientOtp(mobile)
      if (data.delivery === "sms") {
        setOtpNotice("")
        setShowEmailFallback(false)
        setStep("otp")
      } else {
        setOtpNotice(data.message || "Unable to send SMS OTP. SMS service is not configured.")
        setShowEmailFallback(true)
        if (data.delivery === "console" || data.delivery === "cache") {
          setStep("otp")
        }
      }
    } catch (error) {
      setOtpError(error.message || "Unable to send SMS OTP. SMS service is not configured.")
      setShowEmailFallback(true)
    } finally {
      setOtpLoading(false)
    }
  }

  const handleVerifyOTP = async (e) => {
    e.preventDefault()
    setOtpError("")
    setOtpLoading(true)
    try {
      const data = await api.auth.verifyPatientOtp(mobile, otp)
      patientLogin(data)
      if (data.patient) savePatient(data.patient)
      switchRole("Patient")
      navigate(afterPatientLogin)
    } catch (error) {
      setOtpError(error.message || "Invalid or expired verification code.")
    } finally {
      setOtpLoading(false)
    }
  }

  const handleTokenLogin = async (e) => {
    e.preventDefault()
    setTokenError("")

    const cleanToken = tokenInput.trim()
    if (!cleanToken || !tokenPassword) {
      setTokenError("Enter your patient ID and password.")
      return
    }

    try {
      const data = await api.auth.patientTokenLogin(cleanToken, tokenPassword)
      patientLogin(data)
      if (data.patient) savePatient(data.patient)
      switchRole("Patient")
      navigate(afterPatientLogin)
    } catch (error) {
      setTokenError(error.message || "Invalid patient credentials.")
    }
  }

  const handleEmailLogin = async (e) => {
    e.preventDefault()
    setEmailError("")
    try {
      const data = await api.auth.patientEmailLogin(emailAddress.trim(), emailPassword)
      patientLogin(data)
      if (data.patient) savePatient(data.patient)
      switchRole("Patient")
      navigate(afterPatientLogin)
    } catch (error) {
      const message = error.message || "Invalid email or password."
      setEmailError(message)
      if (message.toLowerCase().includes("not verified")) {
        setEmailStep("otp")
      }
    }
  }

  const handleSendEmailOtp = async (e) => {
    e?.preventDefault()
    setEmailError("")
    setEmailNotice("")
    if (!emailAddress.trim()) {
      setEmailError("A valid email address is required.")
      return
    }
    setOtpLoading(true)
    try {
      const data = await api.auth.requestEmailOtp(emailAddress.trim())
      setEmailNotice(data.message || "Verification email requested.")
      setEmailStep("otp")
    } catch (error) {
      setEmailError(error.message || "Unable to send verification email. Please check email configuration.")
    } finally {
      setOtpLoading(false)
    }
  }

  const handleVerifyEmailOtp = async (e) => {
    e.preventDefault()
    setEmailError("")
    setOtpLoading(true)
    try {
      const data = await api.auth.verifyEmailOtp(emailAddress.trim(), emailOtp)
      setEmailNotice(data.message || "Email verified. Sign in with your email and password.")
      setEmailStep("credentials")
      setEmailOtp("")
    } catch (error) {
      setEmailError(error.message || "Invalid OTP.")
    } finally {
      setOtpLoading(false)
    }
  }

  const handleStaffPasswordLogin = async (e) => {
    e.preventDefault()
    setStaffError("")
    setStaffLoading(true)
    try {
      await staffLogin(staffUsername, staffPassword)
      navigate("/")
    } catch (err) {
      setStaffError(err.message || "Staff login failed.")
    } finally {
      setStaffLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-[26rem]">

        <div className="mb-8">
          <BrandMark inverted={false} />
          <h1 className="mt-6 text-2xl font-semibold tracking-tight text-ink-900">Sign in</h1>
          <p className="mt-1 text-sm text-ink-500">Patients see their own appointments, prescriptions, reports and bills.</p>
        </div>

        <div className="mb-6">
          <p id="login-role-label" className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-ink-500">
            I am a
          </p>
          <div className="grid grid-cols-3 gap-1.5" role="radiogroup" aria-labelledby="login-role-label">
            {LOGIN_ROLES.map((role) => (
              <button
                key={role}
                type="button"
                onClick={() => setSelectedRole(role)}
                role="radio"
                aria-checked={selectedRole === role}
                className={`h-9 rounded-lg border px-2 text-xs font-semibold transition-colors ${selectedRole === role ? "border-brand-600 bg-brand-600 text-white" : "border-line bg-white text-ink-700 hover:border-brand-300"}`}
              >
                {role}
              </button>
            ))}
          </div>
        </div>

        <DevLoginPanel role={selectedRole} onRoleChange={setSelectedRole} afterPatientLogin={afterPatientLogin} />

        {/* Main Card */}
        <div className="rounded-2xl border border-line bg-white/95 p-6 shadow-xl shadow-ink-900/5 backdrop-blur-sm sm:p-8">

          {/* Mode Switcher Tabs */}
          <div className="mb-6 flex rounded-lg bg-ink-100 p-0.5" role="tablist" aria-label="Sign-in method">
            <button
              type="button"
              onClick={() => {
                setLoginMode("mobile")
                setStep("mobile")
              }}
              role="tab"
              aria-selected={loginMode === "mobile"}
              className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-md py-2 text-xs font-semibold transition-colors ${loginMode === "mobile" ? "bg-white text-brand-700 shadow-sm" : "text-ink-600 hover:text-ink-900"}`}
            >
              <SmartphoneIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> Mobile OTP
            </button>
            <button
              type="button"
              onClick={() => {
                setLoginMode("token")
                setTokenError("")
              }}
              role="tab"
              aria-selected={loginMode === "token"}
              className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-md py-2 text-xs font-semibold transition-colors ${loginMode === "token" ? "bg-white text-brand-700 shadow-sm" : "text-ink-600 hover:text-ink-900"}`}
            >
              <TicketIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> Token / ID
            </button>
            <button
              type="button"
              onClick={() => {
                setLoginMode("email")
                setEmailError("")
              }}
              role="tab"
              aria-selected={loginMode === "email"}
              className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-md py-2 text-xs font-semibold transition-colors ${loginMode === "email" ? "bg-white text-brand-700 shadow-sm" : "text-ink-600 hover:text-ink-900"}`}
            >
              <MailIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> Email
            </button>
          </div>

          {/* ==================================================== */}
          {/* TAB 1: MOBILE NUMBER & OTP */}
          {/* ==================================================== */}
          {loginMode === "mobile" && (
            <>
              {step === "mobile" ? (
                <>
                  <div className="mb-5">
                    <h2 className="text-lg font-semibold text-ink-900">
                      Login with Mobile
                    </h2>
                    <p className="mt-0.5 text-[13px] text-ink-500">
                      We&apos;ll send a 6-digit verification code
                    </p>
                  </div>

                  {otpError && (
                    <Alert tone="danger" className="mb-4">{otpError}</Alert>
                  )}
                  {otpNotice && (
                    <Alert tone="warning" className="mb-4">{otpNotice}</Alert>
                  )}

                  <form onSubmit={handleSendOTP} className="space-y-4">
                    <div>
                      <label htmlFor="pl-field-1" className="hms-label">Mobile Number</label>
                      <div className="flex">
                        <span className="flex items-center rounded-l-lg border border-r-0 border-line-strong bg-ink-50 px-3 text-sm text-ink-600">
                          +91
                        </span>
                        <input
                          id="pl-field-1"
                          type="tel"
                          value={mobile}
                          onChange={(e) => {
                            const val = e.target.value.replace(/\D/g, "")
                            if (val.length <= 10) setMobile(val)
                          }}
                          placeholder="Enter 10-digit number"
                          className="hms-input w-full rounded-l-none"
                          required
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={otpLoading}
                    >
                      {otpLoading ? "Sending..." : "Send OTP"}
                    </button>
                  </form>
                  {showEmailFallback && (
                    <button
                      type="button"
                      onClick={() => {
                        setLoginMode("email")
                        setEmailStep("otp")
                      }}
                      className="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-line-strong bg-white text-sm font-semibold text-ink-800 hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Verify using Email
                    </button>
                  )}
                </>
              ) : (
                <>
                  <div className="mb-5">
                    <h2 className="text-lg font-semibold text-ink-900">
                      Verify OTP
                    </h2>
                    <p className="mt-0.5 text-[13px] text-ink-500">
                      {otpNotice || (
                        <>
                          Enter 6-digit OTP sent to <span className="font-semibold text-gray-800">+91 {mobile}</span>
                        </>
                      )}
                    </p>
                  </div>

                  {otpError && (
                    <Alert tone="danger" className="mb-4">{otpError}</Alert>
                  )}

                  <form onSubmit={handleVerifyOTP} className="space-y-4">
                    <div>
                      <label htmlFor="pl-field-2" className="hms-label">6-Digit OTP Code</label>
                      <input
                        id="pl-field-2"
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        value={otp}
                        onChange={(e) => {
                          const val = e.target.value.replace(/\D/g, "")
                          if (val.length <= 6) setOtp(val)
                        }}
                        placeholder="• • • • • •"
                        className="hms-input w-full text-center text-xl tracking-[0.5em] font-bold"
                        required
                      />
                    </div>

                    <button
                      type="submit"
                      className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={otpLoading}
                    >
                      {otpLoading ? "Verifying..." : "Verify & Continue"}
                    </button>
                  </form>

                  <div className="flex items-center justify-between mt-4 text-xs">
                    <button
                      type="button"
                      onClick={() => {
                        setStep("mobile")
                        setOtp("")
                      }}
                      className="rounded text-[13px] font-medium text-brand-700 hover:underline"
                    >
                      Change number
                    </button>
                    <button
                      type="button"
                      onClick={handleSendOTP}
                      className="rounded text-[13px] font-medium text-ink-600 hover:text-ink-900"
                    >
                      Resend code
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setLoginMode("email")
                      setEmailStep("otp")
                    }}
                    className="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-line-strong bg-white text-sm font-semibold text-ink-800 hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Verify using Email
                  </button>
                </>
              )}
            </>
          )}

          {loginMode === "email" && (
            <div>
              <div className="mb-5">
                <h2 className="text-lg font-semibold text-ink-900">
                  {emailStep === "otp" ? "Verify using Email" : "Login with Email"}
                </h2>
                <p className="mt-0.5 text-[13px] text-ink-500">
                  {emailStep === "otp"
                    ? "We will send a verification code to your registered email."
                    : "Use the email and password from your patient account."}
                </p>
              </div>
              {emailError && (
                <Alert tone="danger" className="mb-4">{emailError}</Alert>
              )}
              {emailNotice && (
                <Alert tone="warning" className="mb-4">{emailNotice}</Alert>
              )}
              {emailStep === "credentials" ? (
                <form onSubmit={handleEmailLogin} className="space-y-4">
                  <div>
                    <label htmlFor="pl-field-3" className="hms-label">Email</label>
                    <input
                      id="pl-field-3"
                      type="email"
                      value={emailAddress}
                      onChange={(e) => setEmailAddress(e.target.value)}
                      className="hms-input w-full"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="pl-field-4" className="hms-label">Password</label>
                    <input
                      id="pl-field-4"
                      type="password"
                      value={emailPassword}
                      onChange={(e) => setEmailPassword(e.target.value)}
                      className="hms-input w-full"
                      autoComplete="current-password"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => setEmailStep("otp")}
                    className="rounded text-[13px] font-medium text-brand-700 hover:underline"
                  >
                    Email not verified? Send email OTP
                  </button>
                </form>
              ) : (
                <form onSubmit={handleVerifyEmailOtp} className="space-y-4">
                  <div>
                    <label htmlFor="pl-field-5" className="hms-label">Email</label>
                    <input
                      id="pl-field-5"
                      type="email"
                      value={emailAddress}
                      onChange={(e) => setEmailAddress(e.target.value)}
                      className="hms-input w-full"
                      required
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleSendEmailOtp}
                    disabled={otpLoading}
                    className="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-line-strong bg-white text-sm font-semibold text-ink-800 hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {otpLoading ? "Sending..." : "Send Email OTP"}
                  </button>
                  <div>
                    <label htmlFor="pl-field-6" className="hms-label">OTP</label>
                    <input
                      id="pl-field-6"
                      inputMode="numeric"
                      value={emailOtp}
                      onChange={(e) => setEmailOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                      className="hms-input w-full"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={otpLoading}
                    className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Verify OTP
                  </button>
                  <button
                    type="button"
                    onClick={() => setEmailStep("credentials")}
                    className="rounded text-[13px] font-medium text-brand-700 hover:underline"
                  >
                    Back to email login
                  </button>
                </form>
              )}
            </div>
          )}

          {/* ==================================================== */}
          {/* TAB 2: TOKEN NUMBER / PATIENT ID */}
          {/* ==================================================== */}
          {loginMode === "token" && (
            <div>
              <div className="mb-5">
                <h2 className="text-lg font-semibold text-ink-900">
                  Login with Token / ID
                </h2>
                <p className="mt-0.5 text-[13px] text-ink-500">
                  Enter your token number or hospital patient ID
                </p>
              </div>

              <form onSubmit={handleTokenLogin} className="space-y-4">
                <div>
                  <label htmlFor="pl-field-7" className="hms-label">Token Number / Patient ID</label>
                  <input
                    id="pl-field-7"
                    type="text"
                    value={tokenInput}
                    onChange={(e) => {
                      setTokenInput(e.target.value)
                      if (tokenError) setTokenError("")
                    }}
                    placeholder="e.g. T-001 or PAT-001 or 1"
                    className="hms-input w-full font-medium"
                    required
                  />
                  {tokenError && (
                    <p className="text-xs text-red-500 mt-1">{tokenError}</p>
                  )}
                  <p className="text-[11px] text-gray-400 mt-1.5">
                    Use the patient ID from registration together with your account password.
                  </p>
                </div>

                <div>
                  <label htmlFor="pl-field-8" className="hms-label">Password</label>
                  <input
                    id="pl-field-8"
                    type="password"
                    value={tokenPassword}
                    onChange={(e) => setTokenPassword(e.target.value)}
                    placeholder="Account password"
                    className="hms-input w-full"
                    autoComplete="current-password"
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Lookup & Login
                </button>
              </form>
            </div>
          )}

          {/* ==================================================== */}
          {/* DIVIDER: OR CONTINUE WITH GOOGLE */}
          {/* ==================================================== */}
          <div className="flex items-center my-6">
            <div className="flex-1 border-t border-line" />
            <span className="px-3 text-xs font-medium text-ink-400">
              OR
            </span>
            <div className="flex-1 border-t border-line" />
          </div>

          {/* ==================================================== */}
          {/* GOOGLE ACCOUNT LOGIN */}
          {/* ==================================================== */}
          <div className="space-y-3">
            {/* Primary Google Login Button */}
            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={googleLoading}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-line-strong bg-white text-sm font-semibold text-ink-800 hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-50 h-11"
            >
              {/* Google 4-color SVG Icon */}
              <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M21.35 12.23c0-.79-.07-1.55-.23-2.27H12v4.3h5.24a4.48 4.48 0 0 1-1.94 2.94v2.45h3.14c1.84-1.69 2.91-4.18 2.91-7.42z"
                />
                <path
                  fill="#34A853"
                  d="M12 21.6c2.63 0 4.84-.87 6.45-2.35l-3.14-2.45c-.87.58-1.98.92-3.31.92-2.54 0-4.69-1.72-5.46-4.03H3.3v2.53A9.75 9.75 0 0 0 12 21.6z"
                />
                <path
                  fill="#FBBC05"
                  d="M6.54 13.69A5.86 5.86 0 0 1 6.23 12c0-.59.1-1.16.31-1.69V7.78H3.3A9.75 9.75 0 0 0 2.25 12c0 1.57.38 3.05 1.05 4.22l3.24-2.53z"
                />
                <path
                  fill="#EA4335"
                  d="M12 6.28c1.43 0 2.71.49 3.72 1.45l2.79-2.79C16.83 3.37 14.63 2.4 12 2.4a9.75 9.75 0 0 0-8.7 5.38l3.24 2.53C7.31 8 9.46 6.28 12 6.28z"
                />
              </svg>
              <span>
                {googleLoading ? "Connecting to Google..." : "Continue with Google"}
              </span>
            </button>

            {/* Google GSI Auto-render container */}
            <div ref={googleBtnRef} className="flex justify-center" />

            {googleStatus && (
              <p className="text-center text-xs font-medium text-brand-700" role="status">
                {googleStatus}
              </p>
            )}
          </div>

          {selectedRole !== "Patient" && (
            <div className="mt-6 border-t border-line pt-6">
              <h3 className="mb-1 text-sm font-semibold text-ink-900">
                Staff username / password
              </h3>
              <p className="text-[11px] text-gray-500 mb-4">
                Approved {selectedRole} accounts sign in here. OTP, Token/ID, and
                Google still identify a patient session and never grant {selectedRole} access by themselves.
              </p>
              {staffError && (
                <Alert tone="danger" className="mb-4">{staffError}</Alert>
              )}
              <form onSubmit={handleStaffPasswordLogin} className="space-y-3">
                <input
                  type="text"
                  value={staffUsername}
                  onChange={(e) => setStaffUsername(e.target.value)}
                  placeholder="Username or email"
                  aria-label="Staff username or email"
                  className="hms-input w-full"
                  autoComplete="username"
                  required
                />
                <input
                  type="password"
                  value={staffPassword}
                  onChange={(e) => setStaffPassword(e.target.value)}
                  placeholder="Password"
                  aria-label="Staff password"
                  className="hms-input w-full"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="submit"
                  disabled={staffLoading}
                  className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {staffLoading ? "Signing in..." : `Sign in as ${selectedRole}`}
                </button>
              </form>
            </div>
          )}

          <div className="mt-6 border-t border-line pt-6 text-center">
            <p className="text-xs text-gray-500">New to the Hospital Management System?</p>
            <Link
              to={`/register?role=${encodeURIComponent(selectedRole)}`}
              className="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-line-strong bg-white text-sm font-semibold text-ink-800 hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Create Account
            </Link>
          </div>

        </div>

      </div>
    </div>
  )
}

export default PatientLogin