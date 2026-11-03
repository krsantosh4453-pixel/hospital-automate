import { useState } from "react"
import { UsersIcon } from "lucide-react"
import api from "../../services/api.js"
import { Alert } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

const PRIMARY_BUTTON =
  "inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
const LINK_BUTTON = "rounded text-[13px] font-medium text-brand-700 hover:underline"

/**
 * Family member / caregiver sign-in: OTP to their own mobile, then choose the
 * patient whose records to view. Access is view-only and granted by the patient.
 *
 * @param {{ onSignedIn: (session: object) => void }} props
 */
export default function ProxyLoginPanel({ onSignedIn }) {
  const { t } = useLanguage()
  const [step, setStep] = useState("mobile") // "mobile" | "otp" | "choose"
  const [mobile, setMobile] = useState("")
  const [otp, setOtp] = useState("")
  const [ticket, setTicket] = useState("")
  const [grants, setGrants] = useState([])
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [loading, setLoading] = useState(false)

  const signInWith = async (ticketValue, grantId) => {
    const session = await api.auth.proxyLogin(ticketValue, grantId)
    onSignedIn(session)
  }

  const handleSendOtp = async (e) => {
    e?.preventDefault()
    setError("")
    if (mobile.length !== 10) {
      setError("Please enter a valid 10-digit mobile number.")
      return
    }
    setLoading(true)
    try {
      const data = await api.auth.requestProxyOtp(mobile)
      const testDelivery = data.delivery === "console" || data.delivery === "cache"
      setNotice(testDelivery ? data.message || "" : "")
      setStep("otp")
    } catch (err) {
      setError(err.message || "Could not send the verification code.")
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const data = await api.auth.verifyProxyOtp(mobile, otp)
      const available = data.grants || []
      if (available.length === 1) {
        await signInWith(data.ticket, available[0].id)
        return
      }
      setTicket(data.ticket)
      setGrants(available)
      setStep("choose")
    } catch (err) {
      setError(err.message || "Invalid or expired verification code.")
    } finally {
      setLoading(false)
    }
  }

  const handleChoose = async (grantId) => {
    setError("")
    setLoading(true)
    try {
      await signInWith(ticket, grantId)
    } catch (err) {
      setError(err.message || "Could not open these records. Request a new code.")
    } finally {
      setLoading(false)
    }
  }

  const restart = () => {
    setStep("mobile")
    setOtp("")
    setTicket("")
    setGrants([])
    setError("")
    setNotice("")
  }

  return (
    <div>
      <div className="mb-5">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-ink-900">
          <UsersIcon size="1em" aria-hidden="true" />{" "}{t("Family member or caregiver")}
        </h2>
        <p className="mt-0.5 text-[13px] text-ink-500">
          {t("View a relative's records with the access they gave you. Use your own mobile number. View only: you cannot change anything.")}
        </p>
      </div>

      {error && <Alert tone="danger" className="mb-4">{error}</Alert>}

      {step === "mobile" && (
        <form onSubmit={handleSendOtp} className="space-y-4">
          <div>
            <label htmlFor="proxy-mobile" className="hms-label">{t("Your mobile number")}</label>
            <div className="flex">
              <span className="flex items-center rounded-l-lg border border-r-0 border-line-strong bg-ink-50 px-3 text-sm text-ink-600">
                +91
              </span>
              <input
                id="proxy-mobile"
                type="tel"
                value={mobile}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, "")
                  if (val.length <= 10) setMobile(val)
                }}
                placeholder={t("Enter 10-digit number")}
                className="hms-input w-full rounded-l-none"
                required
              />
            </div>
          </div>
          <button type="submit" className={PRIMARY_BUTTON} disabled={loading}>
            {loading ? t("Sending...") : t("Send OTP")}
          </button>
          <p className="text-xs text-ink-500">
            {t("No access yet? Ask the patient to add you under Consent & Sharing → Family access in their portal.")}
          </p>
        </form>
      )}

      {step === "otp" && (
        <>
          <p className="mb-4 text-[13px] text-ink-500">
            {notice || (
              <>
                {t("If")}{" "}<span className="font-semibold text-ink-800">+91 {mobile}</span>{" "}{t("has family access, a 6-digit code was sent to it.")}
              </>
            )}
          </p>
          <form onSubmit={handleVerify} className="space-y-4">
            <div>
              <label htmlFor="proxy-otp" className="hms-label">{t("6-Digit OTP Code")}</label>
              <input
                id="proxy-otp"
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={otp}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, "")
                  if (val.length <= 6) setOtp(val)
                }}
                placeholder="• • • • • •"
                className="hms-input w-full text-center text-xl font-bold tracking-[0.5em]"
                required
              />
            </div>
            <button type="submit" className={PRIMARY_BUTTON} disabled={loading}>
              {loading ? t("Verifying...") : t("Verify & Continue")}
            </button>
          </form>
          <div className="mt-4 flex items-center justify-between text-xs">
            <button type="button" onClick={restart} className={LINK_BUTTON}>{t("Change number")}</button>
            <button type="button" onClick={handleSendOtp} className="rounded text-[13px] font-medium text-ink-600 hover:text-ink-900">
              {t("Resend code")}
            </button>
          </div>
        </>
      )}

      {step === "choose" && (
        <>
          <p className="mb-3 text-[13px] text-ink-500">{t("Whose records do you want to view?")}</p>
          <ul className="space-y-2">
            {grants.map((grant) => (
              <li key={grant.id}>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleChoose(grant.id)}
                  className="flex w-full items-center justify-between rounded-lg border border-line-strong bg-white px-4 py-3 text-left hover:bg-ink-50 disabled:opacity-50"
                >
                  <span className="text-sm font-semibold text-ink-900">{grant.patient_name}</span>
                  <span className="text-xs text-ink-500">{t("You:")}{" "}{grant.relationship}</span>
                </button>
              </li>
            ))}
          </ul>
          <button type="button" onClick={restart} className={`mt-4 ${LINK_BUTTON}`}>{t("Use a different number")}</button>
        </>
      )}
    </div>
  )
}
