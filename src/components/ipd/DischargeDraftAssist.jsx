import { useEffect, useRef, useState } from "react"
import { Sparkles } from "lucide-react"
import api from "../../services/api.js"
import { Alert, Button, useConfirm } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

/**
 * "Draft with AI" for the IPD discharge summary dialog. Put it inside the
 * summary <form>. The draft only fills the text box; a required "I have
 * reviewed" checkbox then blocks saving until the clinician confirms, and on
 * save the outcome (accepted as drafted / edited) is recorded for audit.
 */
export default function DischargeDraftAssist({ admission, text, onText }) {
  const { t } = useLanguage()
  const [confirm, confirmDialog] = useConfirm()
  const [draft, setDraft] = useState(null)
  const [reviewed, setReviewed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const anchor = useRef(null)
  const latest = useRef({ draft, text, reviewed })
  latest.current = { draft, text, reviewed }

  // Report what the clinician did with the draft when the form is saved.
  useEffect(() => {
    const form = anchor.current?.closest("form")
    if (!form || !admission) return undefined
    const onSubmit = () => {
      const { draft: current, text: saved, reviewed: ok } = latest.current
      if (!current || !ok) return
      const outcome = saved.trim() === current.text.trim() ? "accepted" : "edited"
      api.ai.dischargeDrafts.review(admission.id, { draft_id: current.draft_id, outcome }).catch(() => {})
    }
    form.addEventListener("submit", onSubmit)
    return () => form.removeEventListener("submit", onSubmit)
  }, [admission])

  const generate = async () => {
    if (!admission) return
    if (text.trim()) {
      const ok = await confirm({
        title: "Replace the current text?",
        message: "The AI draft replaces what is in the summary box now.",
        confirmLabel: "Replace",
      })
      if (!ok) return
    }
    setLoading(true)
    setError("")
    try {
      const result = await api.ai.dischargeDrafts.generate(admission.id)
      setDraft(result)
      setReviewed(false)
      onText(result.text)
    } catch (err) {
      setError(err.message || "Could not draft the summary.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div ref={anchor} className="mb-4 space-y-3">
      {confirmDialog}
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="subtle" size="sm" icon={Sparkles} loading={loading} onClick={generate}>
          Draft with AI
        </Button>
        <span className="text-xs text-ink-500">{t("From this admission's notes, vitals, medicines and lab results.")}</span>
      </div>
      {error && <Alert tone="danger" onDismiss={() => setError("")}>{error}</Alert>}
      {draft && (
        <Alert tone="warning" title={t(draft.notice)}>
          {draft.source === "llm" ? t("Written by {provider} ({model}). ", { provider: draft.provider, model: draft.model }) : ""}
          {(draft.warnings || []).join(" ")} {t("Replace every “[clinician to complete]”.")}
          <label className="mt-2 flex items-start gap-2 font-medium">
            <input type="checkbox" required checked={reviewed} onChange={(e) => setReviewed(e.target.checked)} />
            {t("I have reviewed this draft against the record and edited it where needed.")}
          </label>
        </Alert>
      )}
    </div>
  )
}
