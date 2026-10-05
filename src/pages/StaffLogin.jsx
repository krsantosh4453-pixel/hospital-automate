import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../assets/context/AuthContext.jsx"

function StaffLogin() {
  const navigate = useNavigate()
  const { staffLogin } = useAuth()

  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      await staffLogin(username, password)
      navigate("/")
    } catch (err) {
      setError(err.message || "Login failed. Please try again.")
    } finally {
      setLoading(false)
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
            Staff Portal Login
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8">
          <div className="mb-6">
            <h2 className="text-lg font-bold text-gray-800">
              Sign in to your account
            </h2>
            <p className="text-gray-500 text-xs mt-0.5">
              Enter your credentials to access the hospital system
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
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
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition cursor-pointer shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

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
            <p className="text-xs text-gray-500">
              Don't have a staff account?{" "}
              <span className="text-blue-600 hover:text-blue-700 font-medium cursor-pointer">
                Contact Hospital Admin
              </span>
            </p>
            <p className="text-[11px] text-gray-400 mt-1">
              Staff accounts are created by hospital administrators.
            </p>
          </div>

          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 text-center">
              Demo credentials:
              <br />
              <span className="font-mono text-gray-700">doctor_a / testpass123</span> (Doctor - Hospital A)
              <br />
              <span className="font-mono text-gray-700">nurse_b / testpass123</span> (Nurse - Hospital B)
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default StaffLogin