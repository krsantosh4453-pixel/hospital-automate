import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../assets/context/AuthContext.jsx"
import { usePatient } from "../assets/context/PatientContext.jsx"

function PatientLogin() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const { savePatient, saveToken, patients } = usePatient()

  // Login modes: "mobile", "token"
  const [loginMode, setLoginMode] = useState("mobile")

  // Mobile & OTP states
  const [step, setStep] = useState("mobile")
  const [mobile, setMobile] = useState("")
  const [otp, setOtp] = useState("")

  // Token number states
  const [tokenInput, setTokenInput] = useState("")
  const [tokenError, setTokenError] = useState("")

  // Google login states
  const [googleLoading, setGoogleLoading] = useState(false)
  const [googleStatus, setGoogleStatus] = useState("")
  const googleBtnRef = useRef(null)

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

      if (!res.ok || data.status !== "success") {
        throw new Error(data.error || "Google verification failed.")
      }

      // Success! Format patient data
      const patientData = {
        id: data.patient?.id || data.user?.id || `PAT-${Date.now()}`,
        name: data.patient?.name || data.user?.name || "Google Patient",
        email: data.user?.email || "",
        picture: data.user?.picture || "",
        phone: data.patient?.phone || "",
        authProvider: "google",
      }

      // Save in Auth Context and Patient Context
      login(patientData)
      savePatient(patientData)

      setGoogleStatus("Login successful! Redirecting...")
      setTimeout(() => {
        navigate("/hospital-selection")
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

  // Demo Google Login (for testing without external OAuth popup restrictions)
  const handleDemoGoogleLogin = async () => {
    setGoogleLoading(true)
    setGoogleStatus("Authenticating Google Account...")

    // Dummy valid JWT format: header.payload.signature
    const header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    const payload = btoa(
      JSON.stringify({
        sub: "google_patient_1001",
        email: "patient.google@gmail.com",
        name: "Google Verified Patient",
        picture: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100",
      })
    )
    const dummyToken = `${header}.${payload}.signature`

    try {
      const res = await fetch("http://127.0.0.1:8000/api/auth/google/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: dummyToken }),
      })

      const data = await res.json()

      const patientData = {
        id: data.patient?.id || 101,
        name: data.patient?.name || "Google Verified Patient",
        email: data.user?.email || "patient.google@gmail.com",
        picture: data.user?.picture || "",
        phone: data.patient?.phone || "9876543210",
        authProvider: "google",
      }

      login(patientData)
      savePatient(patientData)

      setGoogleStatus("Welcome! Redirecting...")
      setTimeout(() => {
        navigate("/hospital-selection")
      }, 500)
    } catch (err) {
      console.error("Demo login error:", err)
      // Local fallback
      const fallbackPatient = {
        id: `PAT-${Date.now()}`,
        name: "Google Patient",
        email: "patient.google@gmail.com",
        authProvider: "google",
      }
      login(fallbackPatient)
      savePatient(fallbackPatient)
      navigate("/hospital-selection")
    } finally {
      setGoogleLoading(false)
      setGoogleStatus("")
    }
  }

  // Send Mobile OTP
  const handleSendOTP = (e) => {
    e.preventDefault()

    if (mobile.length !== 10) {
      alert("Please enter a valid 10-digit mobile number.")
      return
    }

    setStep("otp")
  }

  // Verify Mobile OTP
  const handleVerifyOTP = (e) => {
    e.preventDefault()

    if (otp.length !== 6) {
      alert("Please enter a valid 6-digit OTP.")
      return
    }

    const patientData = {
      id: `PAT-${Date.now()}`,
      name: `Patient (${mobile})`,
      phone: mobile,
      mobile: mobile,
      authProvider: "mobile",
    }

    login(patientData)
    savePatient(patientData)
    navigate("/hospital-selection")
  }

  // Token Number Login
  const handleTokenLogin = (e) => {
    e.preventDefault()
    setTokenError("")

    const cleanToken = tokenInput.trim()
    if (!cleanToken) {
      setTokenError("Please enter a token or patient ID.")
      return
    }

    // Try finding existing patient by ID
    const foundPatient = patients?.find(
      (p) =>
        String(p.id).toLowerCase() === cleanToken.toLowerCase() ||
        String(p.phone) === cleanToken
    )

    const patientData = foundPatient || {
      id: cleanToken.startsWith("T-") ? cleanToken : `T-${cleanToken}`,
      name: `Patient (${cleanToken})`,
      tokenNumber: cleanToken,
      authProvider: "token",
    }

    saveToken(cleanToken)
    login(patientData)
    savePatient(patientData)
    navigate("/hospital-selection")
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
            Patient Portal Login
          </p>
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
                      className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm"
                    >
                      Send OTP
                    </button>
                  </form>
                </>
              ) : (
                <>
                  <div className="mb-5">
                    <h2 className="text-lg font-bold text-gray-800">
                      Verify OTP
                    </h2>
                    <p className="text-gray-500 text-xs mt-0.5">
                      Enter 6-digit OTP sent to <span className="font-semibold text-gray-800">+91 {mobile}</span>
                    </p>
                  </div>

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
                      className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm"
                    >
                      Verify & Continue
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
                      onClick={() => alert("Demo OTP: 123456")}
                      className="text-gray-500 hover:text-gray-700 cursor-pointer"
                    >
                      Resend OTP
                    </button>
                  </div>
                </>
              )}
            </>
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
                    Tip: Existing patients can enter their ID or token number to resume their session.
                  </p>
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

            {/* Quick Demo Google Sign-In (instant 1-click test with Django API) */}
            <button
              type="button"
              onClick={handleDemoGoogleLogin}
              disabled={googleLoading}
              className="w-full text-center text-xs text-blue-600 hover:text-blue-700 py-1 cursor-pointer font-medium"
              title="Test Google login API directly with Django backend"
            >
              🚀 1-Click Instant Google Test Login
            </button>

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

        </div>

      </div>
    </div>
  )
}

export default PatientLogin