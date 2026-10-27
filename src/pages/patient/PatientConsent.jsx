import { useCallback, useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import { useHospitals } from "../../assets/context/HospitalsContext.jsx"
import api from "../../services/api.js"
import { CircleCheckIcon, ClipboardListIcon, PenLineIcon, XIcon } from "lucide-react"
import { Alert, Card, SkeletonRows, useConfirm } from "../../components/ui"

const SCOPE_LABELS = {
  visits: "Visit history",
  diagnoses: "Diagnoses",
  prescriptions: "Prescriptions",
  lab_results: "Released lab results",
  discharge_summaries: "Discharge summaries",
  allergies: "Allergies",
}

const readResults = (data) => (Array.isArray(data) ? data : data?.results || data?.forms || [])

const inDays = (days) => {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}

function PatientConsent() {
  const [confirm, confirmDialog] = useConfirm()

  const { patient } = useAuth()
  const { hospitals } = useHospitals()
  const [consentForms, setConsentForms] = useState([])
  const [consentRecords, setConsentRecords] = useState([])
  const [shares, setShares] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState("")
  const [selectedForm, setSelectedForm] = useState(null)
  const [signing, setSigning] = useState(false)
  const [signature, setSignature] = useState("")
  const [confirmed, setConfirmed] = useState(false)
  const [showSignModal, setShowSignModal] = useState(false)
  const [shareForm, setShareForm] = useState({
    recipient_hospital: "",
    scope: ["diagnoses"],
    purpose: "",
    expires_on: inDays(30),
  })
  const [sharing, setSharing] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [formsData, recordsData, sharesData] = await Promise.all([
        api.consent.forms.list(),
        api.consent.records.list(),
        api.consent.shares.list(),
      ])
      setConsentForms(readResults(formsData))
      setConsentRecords(readResults(recordsData))
      setShares(readResults(sharesData))
    } catch (err) {
      setError(err.message || "Could not load your consent information.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (patient?.id) load()
  }, [patient?.id, load])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  // The latest signature for a form that has not been revoked.
  const getRecordForForm = (formId) =>
    consentRecords.find((record) => record.form === formId && record.is_active)

  const handleSign = (form) => {
    setSelectedForm(form)
    setSignature("")
    setConfirmed(false)
    setShowSignModal(true)
  }

  const handleSubmitSignature = async () => {
    if (!selectedForm || !signature.trim() || !confirmed) return

    setSigning(true)
    setError(null)
    try {
      await api.consent.records.sign({
        form: selectedForm.id,
        signed_name: signature.trim(),
        confirm: true,
      })
      setShowSignModal(false)
      setNotice(`Signed: ${selectedForm.name}`)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSigning(false)
    }
  }

  const handleRevokeConsent = async (record) => {
    if (!(await confirm(`Withdraw your consent for "${record.form_name}"?`))) return
    setError(null)
    try {
      await api.consent.records.revoke(record.id)
      setNotice(`Consent withdrawn: ${record.form_name}`)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const toggleScope = (key) => {
    setShareForm((prev) => ({
      ...prev,
      scope: prev.scope.includes(key) ? prev.scope.filter((s) => s !== key) : [...prev.scope, key],
    }))
  }

  const handleCreateShare = async (e) => {
    e.preventDefault()
    setError(null)
    if (!shareForm.recipient_hospital || shareForm.scope.length === 0 || !shareForm.purpose.trim()) {
      setError("Choose a hospital, at least one record type, and the reason for sharing.")
      return
    }
    setSharing(true)
    try {
      await api.consent.shares.create({
        recipient_hospital: Number(shareForm.recipient_hospital),
        scope: shareForm.scope,
        purpose: shareForm.purpose.trim(),
        expires_at: new Date(`${shareForm.expires_on}T23:59:00`).toISOString(),
      })
      setNotice("Records shared. You can stop sharing at any time.")
      setShareForm({ recipient_hospital: "", scope: ["diagnoses"], purpose: "", expires_on: inDays(30) })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSharing(false)
    }
  }

  const handleRevokeShare = async (share) => {
    if (!(await confirm(`Stop sharing with ${share.recipient_hospital_name}? They will lose access immediately.`))) return
    setError(null)
    try {
      await api.consent.shares.revoke(share.id)
      setNotice(`Sharing with ${share.recipient_hospital_name} stopped.`)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <>{confirmDialog}<div className="space-y-6">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink-900 sm:text-2xl">Consent and sharing</h1>
        <p className="mt-1 text-sm text-ink-500">Review and sign consent forms, and control who can see your records.</p>
      </header>

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}
      {notice && !error && <Alert tone="success" onDismiss={() => setNotice("")}>{notice}</Alert>}

      {loading ? (
        <Card><SkeletonRows rows={3} /></Card>
      ) : consentForms.length > 0 ? (
        <div className="space-y-4">
          {consentForms.map((form) => {
            const record = getRecordForForm(form.id)
            const isSigned = Boolean(record)

            return (
              <div key={form.id} className="overflow-hidden rounded-2xl border border-line bg-white">
                <div className="p-5 border-b border-gray-100">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                      <h3 className="text-base font-semibold text-ink-900">{form.name}</h3>
                      <p className="text-sm text-gray-500 mt-1">{form.description}</p>
                      {form.version && <p className="text-xs text-gray-400 mt-1">Version {form.version}{form.required ? " • Required" : ""}</p>}
                    </div>
                    <div className="flex items-center gap-3">
                      {isSigned ? (
                        <>
                          <span className="px-4 py-2 bg-green-100 text-green-700 rounded-xl text-sm font-medium flex items-center gap-2">
                            <CircleCheckIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> Signed on {formatDate(record.signed_at)}
                          </span>
                          <button
                            onClick={() => handleRevokeConsent(record)}
                            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-200"
                          >
                            Withdraw
                          </button>
                        </>
                      ) : (
                        <>
                          <span className="px-4 py-2 bg-red-100 text-red-700 rounded-xl text-sm font-medium">
                            <ClipboardListIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> Not Signed
                          </span>
                          <button
                            onClick={() => handleSign(form)}
                            disabled={signing}
                            className="px-5 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50"
                          >
                            Review &amp; Sign
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {isSigned && (
                  <div className="p-5 bg-green-50 border-t border-green-100">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center text-green-600"><PenLineIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
                      <div>
                        <p className="font-medium text-green-800">Signed by {record.signed_by_proxy ? `proxy (${record.proxy_relationship})` : "Patient"}</p>
                        <p className="text-sm text-green-600">{record.signed_name}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="rounded-2xl border border-line bg-white p-12 text-center">
          <div className="text-4xl mb-3"><ClipboardListIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <h3 className="font-bold text-gray-800">No consent forms available</h3>
          <p className="text-sm text-gray-500 mt-1">You don&apos;t have any pending consent forms at the moment.</p>
        </div>
      )}

      {/* Record sharing */}
      {!loading && (
        <div className="overflow-hidden rounded-2xl border border-line bg-white">
          <div className="p-5 border-b border-gray-100">
            <h2 className="text-base font-semibold text-ink-900">Share My Records</h2>
            <p className="text-sm text-gray-500 mt-1">
              Let another hospital see selected records from this hospital until a date you choose.
              Every time they open your records it is logged here.
            </p>
          </div>

          <form onSubmit={handleCreateShare} className="p-5 grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="share-hospital" className="block text-xs font-medium text-gray-700 mb-1.5">Share with hospital</label>
              <select
                id="share-hospital"
                value={shareForm.recipient_hospital}
                onChange={(e) => setShareForm({ ...shareForm, recipient_hospital: e.target.value })}
                className="hms-input w-full"
                required
              >
                <option value="">Select a hospital</option>
                {hospitals.map((hospital) => (
                  <option key={hospital.id} value={hospital.id}>{hospital.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="share-expiry" className="block text-xs font-medium text-gray-700 mb-1.5">Access ends on</label>
              <input
                id="share-expiry"
                type="date"
                min={inDays(1)}
                max={inDays(365)}
                value={shareForm.expires_on}
                onChange={(e) => setShareForm({ ...shareForm, expires_on: e.target.value })}
                className="hms-input w-full"
                required
              />
            </div>
            <fieldset className="md:col-span-2">
              <legend className="block text-xs font-medium text-gray-700 mb-1.5">Records to share</legend>
              <div className="flex flex-wrap gap-3">
                {Object.entries(SCOPE_LABELS).map(([key, label]) => (
                  <label key={key} className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" checked={shareForm.scope.includes(key)} onChange={() => toggleScope(key)} />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="md:col-span-2">
              <label htmlFor="share-purpose" className="block text-xs font-medium text-gray-700 mb-1.5">Reason</label>
              <input
                id="share-purpose"
                type="text"
                maxLength={200}
                value={shareForm.purpose}
                onChange={(e) => setShareForm({ ...shareForm, purpose: e.target.value })}
                placeholder="e.g. Second opinion with cardiologist"
                className="hms-input w-full"
                required
              />
            </div>
            <div className="md:col-span-2 flex justify-end">
              <button
                type="submit"
                disabled={sharing}
                className="px-5 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {sharing ? "Sharing…" : "Share Records"}
              </button>
            </div>
          </form>

          <div className="border-t border-gray-100">
            {shares.length === 0 ? (
              <p className="p-5 text-sm text-gray-500">You are not sharing records with any hospital.</p>
            ) : (
              <ul className="divide-y divide-gray-100">
                {shares.map((share) => (
                  <li key={share.id} className="p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <div>
                      <p className="font-medium text-gray-800">
                        {share.recipient_hospital_name}
                        <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${share.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>
                          {share.is_active ? "Active" : share.revoked_at ? "Stopped" : "Expired"}
                        </span>
                      </p>
                      <p className="text-sm text-gray-500 mt-1">
                        {share.scope.map((key) => SCOPE_LABELS[key] || key).join(", ")} · until {formatDate(share.expires_at)} · opened {share.access_count} time(s)
                      </p>
                      <p className="text-xs text-gray-400 mt-1">{share.purpose}</p>
                    </div>
                    {share.is_active && (
                      <button
                        onClick={() => handleRevokeShare(share)}
                        className="px-4 py-2 bg-red-50 text-red-700 rounded-xl text-sm font-medium hover:bg-red-100"
                      >
                        Stop Sharing
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {showSignModal && selectedForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" role="dialog" aria-modal="true" aria-labelledby="consent-sign-title">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h2 id="consent-sign-title" className="text-base font-semibold text-ink-900">Sign Consent Form: {selectedForm.name}</h2>
              <button onClick={() => setShowSignModal(false)} className="text-gray-400 hover:text-gray-700 text-xl font-semibold" aria-label="Close"><XIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></button>
            </div>
            <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
              <div className="prose prose-sm max-w-none text-gray-700 border border-gray-200 rounded-xl p-4 bg-gray-50">
                {selectedForm.description}
                <p className="text-xs text-gray-500 mt-2">Version {selectedForm.version}. You can withdraw this consent later on this page.</p>
              </div>
              <div className="border-t pt-4">
                <h3 className="font-semibold text-gray-800 mb-3">Your Signature</h3>
                <label htmlFor="consent-signature" className="text-sm text-gray-500 mb-3 block">Type your full name to provide your electronic signature</label>
                <input
                  id="consent-signature"
                  type="text"
                  value={signature}
                  onChange={(e) => setSignature(e.target.value)}
                  placeholder="Enter your full name"
                  className="hms-input w-full"
                  required
                />
                <label className="flex items-start gap-2 text-xs text-gray-600 mt-3">
                  <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
                  I have read and understood this consent form and agree to its terms.
                </label>
              </div>
            </div>
            <div className="p-5 border-t border-gray-100 flex justify-end gap-3">
              <button onClick={() => setShowSignModal(false)} className="px-5 py-2 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200">Cancel</button>
              <button onClick={handleSubmitSignature} disabled={signing || !signature.trim() || !confirmed} className="px-5 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">{signing ? "Signing..." : "Sign Document"}</button>
            </div>
          </div>
        </div>
      )}
    </div></>
  )
}

export default PatientConsent
