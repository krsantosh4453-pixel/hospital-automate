import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../assets/context/AuthContext.jsx"

function PatientLogin() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [step, setStep] = useState("mobile")
  const [mobile, setMobile] = useState("")
  const [otp, setOtp] = useState("")

  const handleSendOTP = (e) => {
    e.preventDefault()

    if (mobile.length !== 10) {
      alert("Please enter a valid 10-digit mobile number.")
      return
    }

    setStep("otp")
  }

  const handleVerifyOTP = (e) => {
    e.preventDefault()

    if (otp.length !== 6) {
      alert("Please enter a valid 6-digit OTP.")
      return
    }

    // Frontend demo patient data
    const patientData = {
      name: "New Patient",
      mobile: mobile,
    }

    // Save login in AuthContext
    login(patientData)

    // Continue to hospital selection
    navigate("/hospital-selection")
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">

      <div className="w-full max-w-md">

        {/* Header */}
        <div className="text-center mb-8">

          <div className="mx-auto w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg">

            <span className="text-white text-3xl font-bold">
              H
            </span>

          </div>

          <h1 className="text-2xl font-bold text-gray-800 mt-4">
            Hospital Management System
          </h1>

          <p className="text-gray-500 mt-2">
            Patient Portal
          </p>

        </div>


        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8">

          {step === "mobile" ? (

            <>
              <div className="mb-6">

                <h2 className="text-xl font-bold text-gray-800">
                  Login to Continue
                </h2>

                <p className="text-gray-500 text-sm mt-1">
                  Enter your mobile number to continue
                </p>

              </div>


              <form
                onSubmit={handleSendOTP}
                className="space-y-5"
              >

                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Mobile Number
                  </label>

                  <div className="flex">

                    <span className="flex items-center px-4 border border-r-0 border-gray-300 rounded-l-xl bg-gray-50 text-gray-600">
                      +91
                    </span>

                    <input
                      type="tel"
                      value={mobile}
                      onChange={(e) => {

                        const value =
                          e.target.value.replace(
                            /\D/g,
                            ""
                          )

                        if (value.length <= 10) {
                          setMobile(value)
                        }

                      }}
                      placeholder="Enter mobile number"
                      className="w-full border border-gray-300 rounded-r-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                    />

                  </div>

                </div>


                <button
                  type="submit"
                  className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 transition"
                >
                  Send OTP
                </button>

              </form>
            </>

          ) : (

            <>
              <div className="mb-6">

                <h2 className="text-xl font-bold text-gray-800">
                  Verify OTP
                </h2>

                <p className="text-gray-500 text-sm mt-1">
                  Enter the 6-digit OTP sent to
                </p>

                <p className="font-semibold text-gray-800 mt-1">
                  +91 {mobile}
                </p>

              </div>


              <form
                onSubmit={handleVerifyOTP}
                className="space-y-5"
              >

                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    OTP
                  </label>

                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => {

                      const value =
                        e.target.value.replace(
                          /\D/g,
                          ""
                        )

                      if (value.length <= 6) {
                        setOtp(value)
                      }

                    }}
                    placeholder="Enter 6-digit OTP"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3 text-center text-xl tracking-[0.5em] outline-none focus:ring-2 focus:ring-blue-500"
                  />

                </div>


                <button
                  type="submit"
                  className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 transition"
                >
                  Verify & Continue
                </button>

              </form>


              <button
                onClick={() => {
                  setStep("mobile")
                  setOtp("")
                }}
                className="w-full mt-4 text-sm text-blue-600"
              >
                ← Change Mobile Number
              </button>

            </>

          )}

        </div>

      </div>

    </div>
  )
}

export default PatientLogin