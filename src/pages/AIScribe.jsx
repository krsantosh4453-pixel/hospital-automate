import { useEffect, useMemo, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"

const DIAGNOSIS_TYPES = [
  "Provisional",
  "Differential",
  "Final",
  "Confirmed",
]

const formatDateTime = (value) => {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

const formatDay = (value) => {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}

const mapVisitFromApi = (record) => ({
  apiId: record.id,
  patientName: record.patient_name || "Patient",
  doctorName: record.doctor_name || "Unassigned",
  patientApiId: record.patient || null,
  doctorApiId: record.doctor || null,
  visitType: record.visit_type || "OPD",
  chiefComplaint: record.chief_complaint || "",
  status: record.status || "Waiting",
  visitDate: record.visit_date || null,
  visitDay: formatDay(record.visit_date),
  hospitalId: record.hospital || null,
})

const readResults = (data) =>
  Array.isArray(data) ? data : data?.results || []

const mapTranscriptFromApi = (record) => ({
  apiId: record.id,
  text: record.text || "",
  structuredData: record.structured_data || {},
  provider: record.provider || "",
  providerModel: record.provider_model || "",
  detectedLanguage: record.detected_language || "",
  languageConfidence: record.language_confidence,
  status: record.status || "pending",
  errorMessage: record.error_message || "",
  createdAt: record.created_at || null,
  processingCompletedAt: record.processing_completed_at || null,
})

const mapDraftFromApi = (record) => ({
  apiId: record.id,
  consultationId: record.consultation || record.consultation_id,
  version: record.version,
  structuredExtraction: record.structured_extraction || {},
  summary: record.summary || "",
  provider: record.provider || "",
  providerModel: record.provider_model || "",
  promptVersion: record.prompt_version || "v1",
  providerMetadata: record.provider_metadata || {},
  status: record.status || "generated",
  reviewedBy: record.reviewed_by,
  reviewedByName: record.reviewed_by_name,
  approvedBy: record.approved_by,
  approvedByName: record.approved_by_name,
  reviewedAt: record.reviewed_at,
  approvedAt: record.approved_at,
  createdAt: record.created_at,
  updatedAt: record.updated_at,
})

const mapReviewFromApi = (record) => ({
  apiId: record.id,
  action: record.action,
  section: record.section,
  aiValue: record.ai_value || {},
  doctorValue: record.doctor_value || {},
  notes: record.notes || "",
  doctorName: record.doctor_name || "",
  createdAt: record.created_at,
})

const SECTION_LABELS = {
  chief_complaint: "Chief Complaint",
  symptoms: "Symptoms",
  history: "History",
  allergies: "Allergies",
  medications: "Current Medications",
  examination: "Examination Findings",
  vitals: "Vital Signs",
  assessment: "Assessment",
  investigations: "Investigations",
  plan: "Plan",
  follow_up: "Follow-up",
}

const SECTION_ORDER = [
  "chief_complaint",
  "symptoms",
  "history",
  "allergies",
  "medications",
  "examination",
  "vitals",
  "assessment",
  "investigations",
  "plan",
  "follow_up",
]

function AIScribe() {
  const { selectedHospital } = usePatient()

  // Visit selection
  const [visits, setVisits] = useState([])
  const [loadingVisits, setLoadingVisits] = useState(false)
  const [visitsError, setVisitsError] = useState("")
  const [selectedVisitId, setSelectedVisitId] = useState("")

  // Consultation session
  const [session, setSession] = useState(null)
  const [loadingSession, setLoadingSession] = useState(false)
  const [sessionError, setSessionError] = useState("")

  // Transcript
  const [transcript, setTranscript] = useState(null)
  const [loadingTranscript, setLoadingTranscript] = useState(false)
  const [transcriptError, setTranscriptError] = useState("")

  // AI Drafts
  const [drafts, setDrafts] = useState([])
  const [loadingDrafts, setLoadingDrafts] = useState(false)
  const [draftsError, setDraftsError] = useState("")
  const [selectedDraftId, setSelectedDraftId] = useState(null)

  // Reviews for selected draft
  const [reviews, setReviews] = useState([])
  const [loadingReviews, setLoadingReviews] = useState(false)

  // UI state
  const [activeTab, setActiveTab] = useState("recording")
  const [successMessage, setSuccessMessage] = useState("")
  const [errorMessage, setErrorMessage] = useState("")
  const [reloadToken, setReloadToken] = useState(0)

  // Audio recording state
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState(null)
  const [mediaRecorder, setMediaRecorder] = useState(null)
  const [recordingTime, setRecordingTime] = useState(0)

  const selectedVisit = useMemo(
    () =>
      visits.find(
        (visit) => String(visit.apiId) === String(selectedVisitId)
      ) || null,
    [visits, selectedVisitId]
  )

  const selectedDraft = useMemo(
    () =>
      drafts.find((d) => String(d.apiId) === String(selectedDraftId)) || null,
    [drafts, selectedDraftId]
  )

  // Load visits
  useEffect(() => {
    let cancelled = false

    const loadVisits = async () => {
      if (!selectedHospital) {
        setVisits([])
        setSelectedVisitId("")
        return
      }

      setLoadingVisits(true)
      setVisitsError("")

      try {
        const data = await api.visits.list(selectedHospital.id)
        if (cancelled) return

        const mapped = readResults(data).map(mapVisitFromApi)
        setVisits(mapped)

        setSelectedVisitId((current) => {
          const stillThere = mapped.some(
            (visit) => String(visit.apiId) === String(current)
          )
          return stillThere ? current : (mapped.length ? String(mapped[0].apiId) : "")
        })
      } catch (error) {
        if (cancelled) return
        setVisits([])
        setVisitsError(error.message || "Failed to load visits.")
      } finally {
        if (!cancelled) setLoadingVisits(false)
      }
    }

    loadVisits()
    return () => { cancelled = true }
  }, [selectedHospital, reloadToken])

  // Load session, transcript, drafts when visit changes
  useEffect(() => {
    if (!selectedVisitId) {
      setSession(null)
      setTranscript(null)
      setDrafts([])
      return
    }

    const loadSession = async () => {
      setLoadingSession(true)
      try {
        // Try to find existing session for this visit
        const sessionsData = await api.aiScribe.consultationSessions.list(selectedHospital?.id)
        const sessions = readResults(sessionsData)
        const existingSession = sessions.find(s => s.visit === selectedVisitId)

        if (existingSession) {
          setSession(existingSession)
          await loadTranscript(existingSession.id)
          await loadDrafts(existingSession.id)
        } else {
          // Create new session
          const newSession = await api.aiScribe.consultationSessions.create({
            visit: selectedVisitId,
            hospital: selectedHospital.id,
            patient: selectedVisit.patientApiId,
            doctor: selectedVisit.doctorApiId,
          })
          setSession(newSession)
        }
      } catch (error) {
        setSessionError(error.message || "Failed to load/create session")
      } finally {
        setLoadingSession(false)
      }
    }

    const loadTranscript = async (sessionId) => {
      setLoadingTranscript(true)
      try {
        const transcriptsData = await api.aiScribe.transcripts.list(sessionId)
        const transcripts = readResults(transcriptsData)
        if (transcripts.length > 0) {
          setTranscript(mapTranscriptFromApi(transcripts[0]))
        }
      } catch (error) {
        setTranscriptError(error.message || "Failed to load transcript")
      } finally {
        setLoadingTranscript(false)
      }
    }

    const loadDrafts = async (sessionId) => {
      setLoadingDrafts(true)
      try {
        const draftsData = await api.aiScribe.drafts.list(sessionId)
        const draftsList = readResults(draftsData).map(mapDraftFromApi)
        setDrafts(draftsList)
        if (draftsList.length > 0) {
          setSelectedDraftId(draftsList[0].apiId)
          await loadReviews(draftsList[0].apiId)
        }
      } catch (error) {
        setDraftsError(error.message || "Failed to load drafts")
      } finally {
        setLoadingDrafts(false)
      }
    }

    const loadReviews = async (draftId) => {
      setLoadingReviews(true)
      try {
        const reviewsData = await api.aiScribe.reviews.list(draftId)
        const reviewsList = readResults(reviewsData).map(mapReviewFromApi)
        setReviews(reviewsList)
      } catch (error) {
        console.error("Failed to load reviews", error)
      } finally {
        setLoadingReviews(false)
      }
    }

    loadSession()
  }, [selectedVisitId, selectedVisit, selectedHospital])

  // Load reviews when draft changes
  useEffect(() => {
    if (selectedDraftId) {
      setLoadingReviews(true)
      const loadReviews = async () => {
        try {
          const reviewsData = await api.aiScribe.reviews.list(selectedDraftId)
          const reviewsList = readResults(reviewsData).map(mapReviewFromApi)
          setReviews(reviewsList)
        } catch (error) {
          console.error("Failed to load reviews", error)
        } finally {
          setLoadingReviews(false)
        }
      }
      loadReviews()
    }
  }, [selectedDraftId])

  // Auto-dismiss success message
  useEffect(() => {
    if (!successMessage) return
    const timer = setTimeout(() => setSuccessMessage(""), 3000)
    return () => clearTimeout(timer)
  }, [successMessage])

  // Recording timer
  useEffect(() => {
    let interval = null
    if (isRecording) {
      interval = setInterval(() => setRecordingTime(t => t + 1), 1000)
    }
    return () => clearInterval(interval)
  }, [isRecording])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, "0")
    const secs = (seconds % 60).toString().padStart(2, "0")
    return `${mins}:${secs}`
  }

  // Audio recording handlers
  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      })
      const chunks = []

      recorder.ondataavailable = (e) => chunks.push(e.data)
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" })
        setAudioBlob(blob)
        stream.getTracks().forEach(t => t.stop())
      }

      setMediaRecorder(recorder)
      recorder.start(100) // Collect data every 100ms
      setIsRecording(true)
      setRecordingTime(0)

      // Start recording on backend
      if (session) {
        await api.aiScribe.consultationSessions.startRecording(session.id)
        setSession({ ...session, status: "recording" })
      }
    } catch (error) {
      setErrorMessage("Failed to start recording: " + error.message)
    }
  }

  const handleStopRecording = async () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop()
      setIsRecording(false)

      // Wait for blob to be ready
      await new Promise(resolve => setTimeout(resolve, 500))

      if (audioBlob && session) {
        try {
          await api.aiScribe.consultationSessions.uploadAudio(session.id, audioBlob, {
            duration_seconds: recordingTime,
            format: "webm",
          })

          await api.aiScribe.consultationSessions.stopRecording(session.id, {
            duration_seconds: recordingTime,
            format: "webm",
          })

          setSession({ ...session, status: "completed" })
          setSuccessMessage("Recording uploaded successfully")
        } catch (error) {
          setErrorMessage("Failed to upload recording: " + error.message)
        }
      }
    }
  }

  const handleTranscribe = async () => {
    if (!session) return

    setLoadingTranscript(true)
    setTranscriptError("")
    try {
      const result = await api.aiScribe.consultationSessions.transcribe(session.id)
      setTranscript(mapTranscriptFromApi(result.transcript || result))
      setSuccessMessage("Transcription completed")
    } catch (error) {
      setTranscriptError(error.message || "Transcription failed")
    } finally {
      setLoadingTranscript(false)
    }
  }

  const handleGenerateDraft = async () => {
    if (!selectedDraftId || !session) return

    setLoadingDrafts(true)
    setDraftsError("")
    try {
      const result = await api.aiScribe.drafts.generate(selectedDraftId)
      const newDraft = mapDraftFromApi(result)
      setDrafts(prev => [newDraft, ...prev.filter(d => d.apiId !== newDraft.apiId)])
      setSelectedDraftId(newDraft.apiId)
      setSuccessMessage("AI draft generated")
    } catch (error) {
      setDraftsError(error.message || "Failed to generate draft")
    } finally {
      setLoadingDrafts(false)
    }
  }

  const handleRegenerateDraft = async () => {
    if (!selectedDraftId) return

    setLoadingDrafts(true)
    try {
      const result = await api.aiScribe.drafts.regenerate(selectedDraftId)
      const newDraft = mapDraftFromApi(result)
      setDrafts(prev => [newDraft, ...prev])
      setSelectedDraftId(newDraft.apiId)
      setSuccessMessage("New draft version generated")
    } catch (error) {
      setDraftsError(error.message || "Failed to regenerate draft")
    } finally {
      setLoadingDrafts(false)
    }
  }

  const handleReviewAction = async (action, section, aiValue, doctorValue, notes) => {
    if (!selectedDraftId) return

    try {
      await api.aiScribe.drafts.review(selectedDraftId, {
        action,
        section,
        ai_value: aiValue,
        doctor_value: doctorValue,
        notes,
      })
      setSuccessMessage("Review recorded")
      // Reload draft and reviews
      const draftsData = await api.aiScribe.drafts.list(session.id)
      setDrafts(readResults(draftsData).map(mapDraftFromApi))
      const reviewsData = await api.aiScribe.reviews.list(selectedDraftId)
      setReviews(readResults(reviewsData).map(mapReviewFromApi))
    } catch (error) {
      setErrorMessage(error.message || "Failed to record review")
    }
  }

  const handleApproveDraft = async () => {
    if (!selectedDraftId) return

    if (!window.confirm("Approve this AI draft and create final clinical note? This action cannot be undone.")) {
      return
    }

    setLoadingDrafts(true)
    try {
      const result = await api.aiScribe.drafts.approve(selectedDraftId)
      setSuccessMessage("Draft approved and clinical note created")
      const draftsData = await api.aiScribe.drafts.list(session.id)
      setDrafts(readResults(draftsData).map(mapDraftFromApi))
      setSelectedDraftId(result.draft?.id || selectedDraftId)
    } catch (error) {
      setErrorMessage(error.message || "Failed to approve draft")
    } finally {
      setLoadingDrafts(false)
    }
  }

  const handleRejectDraft = async () => {
    if (!selectedDraftId) return

    const notes = window.prompt("Enter rejection reason:")
    if (notes === null) return

    setLoadingDrafts(true)
    try {
      await api.aiScribe.drafts.reject(selectedDraftId, { notes })
      setSuccessMessage("Draft rejected")
      const draftsData = await api.aiScribe.drafts.list(session.id)
      setDrafts(readResults(draftsData).map(mapDraftFromApi))
    } catch (error) {
      setErrorMessage(error.message || "Failed to reject draft")
    } finally {
      setLoadingDrafts(false)
    }
  }

  const renderSection = (sectionKey, extraction, reviews) => {
    const label = SECTION_LABELS[sectionKey] || sectionKey
    const value = extraction[sectionKey]
    const sectionReviews = reviews.filter(r => r.section === sectionKey)
    const lastReview = sectionReviews[sectionReviews.length - 1]
    const isEdited = lastReview?.action === "edited_section"

    const displayValue = isEdited ? lastReview.doctorValue : value

    if (!displayValue || (Array.isArray(displayValue) && displayValue.length === 0)) {
      return (
        <div className="mb-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
          <div className="flex items-center justify-between">
            <label className="text-sm font-semibold text-slate-700">{label}</label>
            <span className="text-xs text-slate-400">Not extracted</span>
          </div>
        </div>
      )
    }

    const formattedValue = Array.isArray(displayValue)
      ? displayValue.map((v, i) => <div key={i} className="ml-4">• {v}</div>)
      : typeof displayValue === "object"
        ? Object.entries(displayValue).map(([k, v]) => <div key={k} className="ml-4"><strong>{k}:</strong> {v}</div>)
        : <div className="ml-4">{displayValue}</div>

    return (
      <div className="mb-4 p-4 bg-white rounded-xl border border-slate-200">
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-semibold text-slate-700">{label}</label>
          <div className="flex items-center gap-2">
            {isEdited && <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded">Edited by Doctor</span>}
            <select
              value={sectionReviews.length > 0 ? sectionReviews[sectionReviews.length - 1].action : "viewed"}
              onChange={(e) => handleReviewAction(e.target.value, sectionKey, value, displayValue, "")}
              className="text-xs border border-slate-300 rounded px-2 py-1 bg-white"
            >
              <option value="viewed">Viewed</option>
              <option value="accepted_section">Accept</option>
              <option value="edited_section">Edit</option>
              <option value="rejected_section">Reject</option>
            </select>
          </div>
        </div>
        <div className="text-sm text-slate-700">{formattedValue}</div>
        {isEdited && (
          <div className="mt-2 text-xs text-amber-600">
            Original AI: {Array.isArray(value) ? value.join(", ") : JSON.stringify(value)}
          </div>
        )}
      </div>
    )
  }

  const tabs = [
    { id: "recording", label: "Recording", icon: "🎙️" },
    { id: "transcript", label: "Transcript", icon: "📝" },
    { id: "draft", label: "AI Draft", icon: "🤖" },
    { id: "review", label: "Review", icon: "✅" },
  ]

  return (
    <div className="p-4 md:p-6 space-y-6 bg-slate-50 min-h-screen">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">AI Medical Scribe</h1>
          <p className="text-sm text-slate-500 mt-1">
            Record consultation, transcribe, generate AI clinical draft, review & approve
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-4 py-2 rounded-xl bg-white border border-slate-200 text-sm text-slate-600">
            🏥 <strong className="text-slate-800">{selectedHospital?.name || "No hospital"}</strong>
          </span>
        </div>
      </div>

      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm">
          ✅ {successMessage}
        </div>
      )}

      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-start justify-between gap-3">
          <span>⚠️ {errorMessage}</span>
          <button onClick={() => setErrorMessage("")} className="text-red-500 hover:text-red-700 font-bold cursor-pointer">✕</button>
        </div>
      )}

      {!selectedHospital && (
        <div className="p-6 rounded-2xl bg-white border border-slate-200 text-center text-slate-500">
          Select a hospital from the navbar to start.
        </div>
      )}

      {selectedHospital && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
          <div className="flex flex-col md:flex-row md:items-end gap-4">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wide">
                Select Visit
              </label>
              <select
                value={selectedVisitId}
                onChange={(e) => setSelectedVisitId(e.target.value)}
                disabled={loadingVisits}
                className="w-full border border-slate-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-slate-100"
              >
                <option value="">
                  {loadingVisits ? "Loading visits…" : visits.length ? "-- Choose a visit --" : "No visits available"}
                </option>
                {visits.map((visit) => (
                  <option key={visit.apiId} value={visit.apiId}>
                    #{visit.apiId} · {visit.patientName} · {visit.visitType} · {visit.visitDay}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {selectedVisit && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
              <div><p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Patient</p><p className="text-sm text-slate-700 mt-1">{selectedVisit.patientName}</p></div>
              <div><p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Doctor</p><p className="text-sm text-slate-700 mt-1">{selectedVisit.doctorName}</p></div>
              <div><p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Visit Type</p><p className="text-sm text-slate-700 mt-1">{selectedVisit.visitType}</p></div>
              <div><p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Visit Date</p><p className="text-sm text-slate-700 mt-1">{formatDateTime(selectedVisit.visitDate)}</p></div>
            </div>
          )}
        </div>
      )}

      {selectedVisitId && session && (
        <>
          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition cursor-pointer border ${activeTab === tab.id ? "bg-blue-600 text-white border-blue-600" : "bg-white text-slate-600 border-slate-200 hover:bg-slate-100"}`}
                disabled={tab.id === "transcript" && !transcript}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* RECORDING TAB */}
          {activeTab === "recording" && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
              <h2 className="text-xl font-semibold text-slate-800">Audio Recording</h2>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-4xl font-mono font-bold text-blue-600">{formatTime(recordingTime)}</p>
                    <p className="text-sm text-slate-500">{isRecording ? "Recording in progress..." : "Ready to record"}</p>
                  </div>
                  <div className="flex gap-3">
                    {!isRecording ? (
                      <button
                        onClick={handleStartRecording}
                        disabled={loadingSession}
                        className="px-6 py-3 rounded-xl bg-red-600 hover:bg-red-700 text-white text-lg font-medium transition cursor-pointer disabled:bg-red-300"
                      >
                        🎙️ Start Recording
                      </button>
                    ) : (
                      <button
                        onClick={handleStopRecording}
                        className="px-6 py-3 rounded-xl bg-slate-600 hover:bg-slate-700 text-white text-lg font-medium transition cursor-pointer"
                      >
                        ⏹️ Stop Recording
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {audioBlob && (
                <div className="p-4 rounded-xl bg-green-50 border border-green-200">
                  <p className="text-sm text-green-700">Audio recorded ({formatTime(recordingTime)}). Ready to upload.</p>
                </div>
              )}

              {session.status === "completed" && (
                <div className="p-4 rounded-xl bg-blue-50 border border-blue-200">
                  <p className="text-sm text-blue-700">Recording completed. Proceed to Transcript tab.</p>
                </div>
              )}
            </div>
          )}

          {/* TRANSCRIPT TAB */}
          {activeTab === "transcript" && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
              <h2 className="text-xl font-semibold text-slate-800">Transcript</h2>

              {!transcript && (
                <div className="text-center py-12">
                  <p className="text-slate-500">No transcript available. Click &quot;Transcribe&quot; to generate.</p>
                  <button
                    onClick={handleTranscribe}
                    disabled={loadingTranscript || !session?.audio_file}
                    className="mt-4 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:bg-blue-300 cursor-pointer"
                  >
                    {loadingTranscript ? "Transcribing…" : "Transcribe Audio"}
                  </button>
                </div>
              )}

              {transcript && (
                <>
                  <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200">
                    <div>
                      <p className="text-sm text-slate-500">Status: <span className="font-medium capitalize">{transcript.status}</span></p>
                      <p className="text-sm text-slate-500">Provider: {transcript.provider} ({transcript.providerModel})</p>
                      {transcript.detectedLanguage && <p className="text-sm text-slate-500">Language: {transcript.detectedLanguage} ({transcript.languageConfidence ? Math.round(transcript.languageConfidence * 100) + "%" : "N/A"})</p>}
                    </div>
                    {transcript.status !== "completed" && (
                      <button
                        onClick={handleTranscribe}
                        disabled={loadingTranscript}
                        className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm disabled:bg-blue-300 cursor-pointer"
                      >
                        {loadingTranscript ? "Processing…" : "Re-transcribe"}
                      </button>
                    )}
                  </div>

                  <div className="prose max-w-none p-4 bg-white border border-slate-200 rounded-xl whitespace-pre-wrap font-mono text-sm">
                    {transcript.text || "No transcript text available"}
                  </div>
                </>
              )}
            </div>
          )}

          {/* AI DRAFT TAB */}
          {activeTab === "draft" && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-slate-800">AI Clinical Draft</h2>
                {selectedDraft && selectedDraft.status !== "approved" && (
                  <div className="flex gap-2">
                    <button
                      onClick={handleRegenerateDraft}
                      disabled={loadingDrafts}
                      className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-sm font-medium transition cursor-pointer disabled:bg-slate-100"
                    >
                      🔄 Regenerate
                    </button>
                    {selectedDraft.status === "generated" && (
                      <button
                        onClick={handleGenerateDraft}
                        disabled={loadingDrafts || !transcript}
                        className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition cursor-pointer disabled:bg-blue-300"
                      >
                        {loadingDrafts ? "Generating…" : "Generate Draft"}
                      </button>
                    )}
                  </div>
                )}
              </div>

              {drafts.length === 0 && (
                <div className="text-center py-12">
                  <p className="text-slate-500">No drafts yet. Generate a draft from the transcript.</p>
                </div>
              )}

              {selectedDraft && (
                <>
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="flex flex-wrap items-center gap-4 text-sm">
                      <span className={`px-3 py-1 rounded-full ${selectedDraft.status === "approved" ? "bg-emerald-100 text-emerald-700" : selectedDraft.status === "under_review" ? "bg-blue-100 text-blue-700" : selectedDraft.status === "edited" ? "bg-amber-100 text-amber-700" : selectedDraft.status === "rejected" ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-700"}`}>
                        {selectedDraft.status.replace("_", " ").toUpperCase()}
                      </span>
                      <span>Version: {selectedDraft.version}</span>
                      <span>Provider: {selectedDraft.provider} ({selectedDraft.providerModel})</span>
                      <span>Prompt: {selectedDraft.promptVersion}</span>
                    </div>
                  </div>

                  {selectedDraft.summary && (
                    <div className="mb-6 p-4 rounded-xl bg-blue-50 border border-blue-200">
                      <h3 className="font-semibold text-blue-800 mb-2">AI Summary</h3>
                      <p className="text-blue-700">{selectedDraft.summary}</p>
                    </div>
                  )}

                  <div className="space-y-4">
                    {SECTION_ORDER.map((key) => renderSection(key, selectedDraft.structuredExtraction, reviews))}
                  </div>

                  {selectedDraft.status !== "approved" && selectedDraft.status !== "rejected" && (
                    <div className="pt-4 border-t border-slate-200 flex gap-3">
                      <button
                        onClick={handleApproveDraft}
                        className="flex-1 px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium cursor-pointer"
                      >
                        ✅ Approve & Create Clinical Note
                      </button>
                      <button
                        onClick={handleRejectDraft}
                        className="px-6 py-3 rounded-xl bg-red-600 hover:bg-red-700 text-white font-medium cursor-pointer"
                      >
                        ❌ Reject
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* REVIEW TAB */}
          {activeTab === "review" && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
              <h2 className="text-xl font-semibold text-slate-800">Review History</h2>

              {reviews.length === 0 ? (
                <p className="text-slate-500 text-center py-8">No review actions recorded yet.</p>
              ) : (
                <div className="space-y-3">
                  {reviews.map((review) => (
                    <div key={review.apiId} className="p-4 rounded-xl border border-slate-200 bg-slate-50">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 text-sm">
                            <span className="px-2 py-1 rounded-full bg-blue-100 text-blue-700 font-medium">
                              {review.action.replace("_", " ").toUpperCase()}
                            </span>
                            {review.section && (
                              <span className="text-slate-600">Section: <strong>{SECTION_LABELS[review.section] || review.section}</strong></span>
                            )}
                            <span className="text-slate-400">by {review.doctorName || "Unknown"}</span>
                            <span className="text-slate-400">{formatDateTime(review.createdAt)}</span>
                          </div>
                          {review.notes && <p className="mt-2 text-sm text-slate-600">{review.notes}</p>}
                        </div>
                      </div>
                      {(review.action === "edited_section" || review.action === "rejected_section") && (
                        <div className="mt-3 p-3 bg-white rounded-lg border border-slate-200 text-xs">
                          <p className="text-amber-700"><strong>AI Value:</strong> {JSON.stringify(review.aiValue)}</p>
                          {review.doctorValue && <p className="text-emerald-700"><strong>Doctor Value:</strong> {JSON.stringify(review.doctorValue)}</p>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {!selectedVisitId && selectedHospital && visits.length === 0 && (
        <div className="p-6 rounded-2xl bg-white border border-slate-200 text-center text-slate-500">
          No visits found for this hospital.
        </div>
      )}
    </div>
  )
}

export default AIScribe