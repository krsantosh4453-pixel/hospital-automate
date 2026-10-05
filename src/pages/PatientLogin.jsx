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

function PatientLogin() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
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
      alert("No credential received from Google.")
      return
    }

    try {
      setGoogleLoading(true)
      setGoogleStatus("Verifying with backend...")

      // Try local Django server first, then fallback to relative path
      let res
      try {
        res = await fetch("http://127.0.0.1:8000/api/auth/google/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ credential: response.credential }),
        })
      } catch (networkErr) {
        // Retry with localhost or relative url
        res = await fetch("/api/auth/google/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ credential: response.credential }),
        })
      }

      const data = await res.json()

      if (!res.ok || data.status !== "success" || !data.access) {
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
        navigate(data.account_type === "staff" ? "/" : "/patient")
      }, 500)
    } catch (error) {
      console.error("Google login error:", error)
      alert(`Google Login Error: ${error.message || "Could not connect to server."}`)
    } finally {
      setGoogleLoading(false)
      setGoogleStatus("")
    }
  }

  // Trigger Google Login popup
  const handleGoogleLogin = () => {
    if (!window.google?.accounts?.id) {
      alert("Google Services are loading. Please try again in 2 seconds.")
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
      navigate("/patient")
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
      navigate("/patient")
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
      navigate("/patient")
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
            Hospital Portal Login
          </p>
        </div>

        <div className="mb-6">
          <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider text-center mb-3">
            Select Role
          </p>
          <div className="grid grid-cols-3 gap-2">
            {LOGIN_ROLES.map((role) => (
              <button
                key={role}
                type="button"
                onClick={() => setSelectedRole(role)}
                className={`py-2 px-2 text-[11px] font-semibold rounded-xl border transition cursor-pointer ${
                  selectedRole === role
                    ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                    : "bg-white text-gray-700 border-gray-200 hover:border-blue-300"
                }`}
              >
                {role}
              </button>
            ))}
          </div>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8">

          {/* Mode Switcher Tabs */}
          <div className="flex bg-gray-100 rounded-xl p-1 mb-6">
            <button
              type="button"
              onClick={() => {
                setLoginMode("mobile")
                setStep("mobile")
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition cursor-pointer ${
                loginMode === "mobile"
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              📱 Mobile OTP
            </button>
            <button
              type="button"
              onClick={() => {
                setLoginMode("token")
                setTokenError("")
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition cursor-pointer ${
                loginMode === "token"
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              🎫 Token / ID
            </button>
            <button
              type="button"
              onClick={() => {
                setLoginMode("email")
                setEmailError("")
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition cursor-pointer ${
                loginMode === "email"
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              ✉️ Email
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
                    <h2 className="text-lg font-bold text-gray-800">
                      Login with Mobile
                    </h2>
                    <p className="text-gray-500 text-xs mt-0.5">
                      We'll send a 6-digit verification code
                    </p>
                  </div>

                  {otpError && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                      {otpError}
                    </div>
                  )}
                  {otpNotice && (
                    <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
                      {otpNotice}
                    </div>
                  )}

                  <form onSubmit={handleSendOTP} className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1.5">
                        Mobile Number
                      </label>
                      <div className="flex">
                        <span className="flex items-center px-3.5 border border-r-0 border-gray-300 rounded-l-xl bg-gray-50 text-gray-600 text-sm">
                          +91
                        </span>
                        <input
                          type="tel"
                          value={mobile}
                          onChange={(e) => {
                            const val = e.target.value.replace(/\D/g, "")
                            if (val.length <= 10) setMobile(val)
                          }}
                          placeholder="Enter 10-digit number"
                          className="w-full border border-gray-300 rounded-r-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                          required
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm disabled:opacity-50"
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
                      className="w-full mt-3 border border-blue-600 text-blue-600 py-2.5 rounded-xl font-semibold text-sm hover:bg-blue-50 transition cursor-pointer"
                    >
                      Verify using Email
                    </button>
                  )}
                </>
              ) : (
                <>
                  <div className="mb-5">
                    <h2 className="text-lg font-bold text-gray-800">
                      Verify OTP
                    </h2>
                    <p className="text-gray-500 text-xs mt-0.5">
                      {otpNotice || (
                        <>
                          Enter 6-digit OTP sent to <span className="font-semibold text-gray-800">+91 {mobile}</span>
                        </>
                      )}
                    </p>
                  </div>

                  {otpError && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                      {otpError}
                    </div>
                  )}

                  <form onSubmit={handleVerifyOTP} className="space-y-4">
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
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm disabled:opacity-50"
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
                      className="text-blue-600 hover:text-blue-700 cursor-pointer"
                    >
                      ← Change Mobile
                    </button>
                    <button
                      type="button"
                      onClick={handleSendOTP}
                      className="text-gray-500 hover:text-gray-700 cursor-pointer"
                    >
                      Resend OTP
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setLoginMode("email")
                      setEmailStep("otp")
                    }}
                    className="w-full mt-3 border border-blue-600 text-blue-600 py-2.5 rounded-xl font-semibold text-sm hover:bg-blue-50 transition cursor-pointer"
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
                <h2 className="text-lg font-bold text-gray-800">
                  {emailStep === "otp" ? "Verify using Email" : "Login with Email"}
                </h2>
                <p className="text-gray-500 text-xs mt-0.5">
                  {emailStep === "otp"
                    ? "We will send a verification code to your registered email."
                    : "Use the email and password from your patient account."}
                </p>
              </div>
              {emailError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {emailError}
                </div>
              )}
              {emailNotice && (
                <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
                  {emailNotice}
                </div>
              )}
              {emailStep === "credentials" ? (
                <form onSubmit={handleEmailLogin} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1.5">Email</label>
                    <input
                      type="email"
                      value={emailAddress}
                      onChange={(e) => setEmailAddress(e.target.value)}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1.5">Password</label>
                    <input
                      type="password"
                      value={emailPassword}
                      onChange={(e) => setEmailPassword(e.target.value)}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                      autoComplete="current-password"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm"
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => setEmailStep("otp")}
                    className="w-full text-xs text-blue-600 hover:text-blue-700 cursor-pointer"
                  >
                    Email not verified? Send email OTP
                  </button>
                </form>
              ) : (
                <form onSubmit={handleVerifyEmailOtp} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1.5">Email</label>
                    <input
                      type="email"
                      value={emailAddress}
                      onChange={(e) => setEmailAddress(e.target.value)}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleSendEmailOtp}
                    disabled={otpLoading}
                    className="w-full border border-blue-600 text-blue-600 py-2.5 rounded-xl font-semibold text-sm hover:bg-blue-50 transition cursor-pointer disabled:opacity-50"
                  >
                    {otpLoading ? "Sending..." : "Send Email OTP"}
                  </button>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1.5">OTP</label>
                    <input
                      inputMode="numeric"
                      value={emailOtp}
                      onChange={(e) => setEmailOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={otpLoading}
                    className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm disabled:opacity-50"
                  >
                    Verify OTP
                  </button>
                  <button
                    type="button"
                    onClick={() => setEmailStep("credentials")}
                    className="text-xs text-blue-600 hover:text-blue-700 cursor-pointer"
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
                <h2 className="text-lg font-bold text-gray-800">
                  Login with Token / ID
                </h2>
                <p className="text-gray-500 text-xs mt-0.5">
                  Enter your token number or hospital patient ID
                </p>
              </div>

              <form onSubmit={handleTokenLogin} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    Token Number / Patient ID
                  </label>
                  <input
                    type="text"
                    value={tokenInput}
                    onChange={(e) => {
                      setTokenInput(e.target.value)
                      if (tokenError) setTokenError("")
                    }}
                    placeholder="e.g. T-001 or PAT-001 or 1"
                    className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500 font-medium"
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
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    Password
                  </label>
                  <input
                    type="password"
                    value={tokenPassword}
                    onChange={(e) => setTokenPassword(e.target.value)}
                    placeholder="Account password"
                    className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                    autoComplete="current-password"
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm"
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
            <div className="flex-1 border-t border-gray-200" />
            <span className="px-3 text-xs text-gray-400 uppercase tracking-wider font-semibold">
              OR
            </span>
            <div className="flex-1 border-t border-gray-200" />
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
              className="w-full border border-gray-300 bg-white text-gray-700 py-2.5 px-4 rounded-xl font-semibold text-sm hover:bg-gray-50 transition flex items-center justify-center gap-3 disabled:opacity-50 cursor-pointer shadow-xs"
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
              <p className="text-center text-xs text-blue-600 font-medium animate-pulse">
                {googleStatus}
              </p>
            )}
          </div>

          {/* Footer note */}
          <p className="text-center text-[11px] text-gray-400 mt-6 leading-relaxed">
            By continuing, you agree to our Terms of Service & Privacy Policy.
          </p>

          {selectedRole !== "Patient" && (
            <div className="mt-6 pt-6 border-t border-gray-100">
              <h3 className="text-sm font-bold text-gray-800 mb-1">
                Staff username / password
              </h3>
              <p className="text-[11px] text-gray-500 mb-4">
                Approved {selectedRole} accounts sign in here. OTP, Token/ID, and
                Google still identify a patient session and never grant {selectedRole} access by themselves.
              </p>
              {staffError && (
                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {staffError}
                </div>
              )}
              <form onSubmit={handleStaffPasswordLogin} className="space-y-3">
                <input
                  type="text"
                  value={staffUsername}
                  onChange={(e) => setStaffUsername(e.target.value)}
                  placeholder="Username or email"
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                  autoComplete="username"
                  required
                />
                <input
                  type="password"
                  value={staffPassword}
                  onChange={(e) => setStaffPassword(e.target.value)}
                  placeholder="Password"
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="submit"
                  disabled={staffLoading}
                  className="w-full bg-slate-800 text-white py-2.5 rounded-xl font-semibold text-sm hover:bg-slate-900 transition cursor-pointer disabled:opacity-50"
                >
                  {staffLoading ? "Signing in..." : `Sign in as ${selectedRole}`}
                </button>
              </form>
            </div>
          )}

          <div className="mt-6 pt-6 border-t border-gray-100 text-center">
            <p className="text-xs text-gray-500">New to the Hospital Management System?</p>
            <Link
              to={`/register?role=${encodeURIComponent(selectedRole)}`}
              className="inline-block mt-3 w-full bg-white border border-blue-600 text-blue-600 py-3 rounded-xl font-semibold text-sm hover:bg-blue-50 transition"
            >
              Create Account
            </Link>
            <p className="text-xs text-gray-500 mt-5">Already have an account?</p>
            <p className="text-sm font-semibold text-gray-800 mt-1">Login</p>
          </div>

        </div>

      </div>
    </div>
  )
}

export default PatientLogin