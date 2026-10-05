import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"

function PatientConsent() {
  const { patient } = useAuth()
  const [consentForms, setConsentForms] = useState([])
  const [consentRecords, setConsentRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedForm, setSelectedForm] = useState(null)
  const [signing, setSigning] = useState(false)
  const [signature, setSignature] = useState("")
  const [showSignModal, setShowSignModal] = useState(false)

  useEffect(() => {
    if (!patient?.id) return

    const fetchConsent = async () => {
      setLoading(true)
      try {
        const [formsData, recordsData] = await Promise.all([
          api.consent.forms.list().catch(() => ({ results: [] })),
          api.consent.records.list({ patient: patient.id }).catch(() => ({ results: [] })),
        ])
        setConsentForms(formsData?.results || formsData || [])
        setConsentRecords(recordsData?.results || recordsData || [])
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchConsent()
  }, [patient?.id])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  const getRecordForForm = (formId) => {
    return consentRecords.find(r => r.consent_form === formId || r.form_id === formId)
  }

  const handleSign = (form) => {
    setSelectedForm(form)
    setSignature("")
    setShowSignModal(true)
  }

  const handleSubmitSignature = async () => {
    if (!selectedForm || !signature.trim()) return

    setSigning(true)
    try {
      await api.consent.records.sign(
        getRecordForForm(selectedForm.id)?.id,
        { signature_data: signature, signed_by_patient: true }
      )
      setShowSignModal(false)
      const recordsData = await api.consent.records.list({ patient: patient.id })
      setConsentRecords(recordsData?.results || recordsData || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setSigning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Consent Forms</h1>
        <p className="text-gray-500 mt-1">Review and sign consent forms</p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">✕</button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : consentForms.length > 0 ? (
        <div className="space-y-4">
          {consentForms.map((form) => {
            const record = getRecordForForm(form.id)
            const isSigned = record?.signed_at
            const isPending = !isSigned && record?.status === "Pending"

            return (
              <div key={form.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-gray-100">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                      <h3 className="font-semibold text-gray-800 text-lg">{form.title}</h3>
                      <p className="text-sm text-gray-500 mt-1">{form.description}</p>
                      {form.version && <p className="text-xs text-gray-400 mt-1">Version {form.version} • Updated {formatDate(form.updated_at)}</p>}
                    </div>
                    <div className="flex items-center gap-3">
                      {isSigned ? (
                        <span className="px-4 py-2 bg-green-100 text-green-700 rounded-xl text-sm font-medium flex items-center gap-2">
                          ✅ Signed on {formatDate(record.signed_at)}
                        </span>
                      ) : isPending ? (
                        <span className="px-4 py-2 bg-orange-100 text-orange-700 rounded-xl text-sm font-medium flex items-center gap-2">
                          ⏳ Pending Signature
                        </span>
                      ) : (
                        <span className="px-4 py-2 bg-red-100 text-red-700 rounded-xl text-sm font-medium">
                          📋 Not Signed
                        </span>
                      )}
                      {!isSigned && (
                        <button
                          onClick={() => handleSign(form)}
                          disabled={signing}
                          className="px-5 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {isPending ? "Sign Now" : "Review & Sign"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {!isSigned && (
                  <div className="p-5 bg-gray-50 border-t border-gray-100">
                    <div className="prose prose-sm max-w-none text-gray-700">
                      {form.content}
                    </div>
                  </div>
                )}

                {isSigned && record?.signature_data && (
                  <div className="p-5 bg-green-50 border-t border-green-100">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center text-green-600">✍️</div>
                      <div>
                        <p className="font-medium text-green-800">Signed by Patient</p>
                        <p className="text-sm text-green-600">{record.signature_data}</p>
                        {record.witness_name && <p className="text-sm text-green-600 mt-1">Witness: {record.witness_name}</p>}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
          <div className="text-4xl mb-3">📋</div>
          <h3 className="font-bold text-gray-800">No consent forms available</h3>
          <p className="text-sm text-gray-500 mt-1">You don't have any pending consent forms at the moment.</p>
        </div>
      )}

      {showSignModal && selectedForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-800">Sign Consent Form: {selectedForm.title}</h2>
              <button onClick={() => setShowSignModal(false)} className="text-gray-400 hover:text-gray-700 text-xl font-semibold">✕</button>
            </div>
            <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
              <div className="prose prose-sm max-w-none text-gray-700 border border-gray-200 rounded-xl p-4 bg-gray-50">
                {selectedForm.content}
              </div>
              <div className="border-t pt-4">
                <h3 className="font-semibold text-gray-800 mb-3">Your Signature</h3>
                <p className="text-sm text-gray-500 mb-3">Type your full name to provide your electronic signature</p>
                <input
                  type="text"
                  value={signature}
                  onChange={(e) => setSignature(e.target.value)}
                  placeholder="Enter your full name"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <p className="text-xs text-gray-500">By typing your name, you acknowledge that you have read and understood the consent form and agree to its terms.</p>
              </div>
            </div>
            <div className="p-5 border-t border-gray-100 flex justify-end gap-3">
              <button onClick={() => setShowSignModal(false)} className="px-5 py-2 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200">Cancel</button>
              <button onClick={handleSubmitSignature} disabled={signing || !signature.trim()} className="px-5 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">{signing ? "Signing..." : "Sign Document"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PatientConsent