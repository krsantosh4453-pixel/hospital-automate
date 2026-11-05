import { useCallback, useEffect, useState } from "react"
import { RefreshCw, ShieldAlert } from "lucide-react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import api from "../services/api.js"
import { displayPatientId } from "../utils/patientIdentity.js"
import {
  Alert, Badge, Button, Card, CardHeader, EmptyState, Field, Input, PageHeader, SkeletonRows, TableWrap, Textarea,
  usePrompt,
} from "../components/ui"

// Break-glass emergency access (G-8) over /api/audit/break-glass/. A Doctor or
// Nurse opens time-limited access to a patient outside their care; an Admin or
// Hospital Manager reviews every grant. The server enforces who may do what,
// the time limit and the audit trail; this page only offers the actions.

const CLINICAL_ROLES = ["Doctor", "Nurse"]
const REVIEWER_ROLES = ["Admin", "Hospital Manager"]
const MIN_REASON_LENGTH = 20

function formatWhen(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
}

// Patient numbers are shown as P012 elsewhere; accept that or the bare number.
function parsePatientId(text) {
  const digits = String(text || "").trim().replace(/^P/i, "")
  return /^\d+$/.test(digits) ? Number(digits) : null
}

function rowsOf(data) {
  return Array.isArray(data) ? data : data?.results || []
}

function GrantState({ grant }) {
  const { t } = useLanguage()
  if (grant.is_active) return <Badge tone="danger" dot>{t("Active")}</Badge>
  if (grant.ended_at) return <Badge tone="neutral">{t("Ended")}</Badge>
  return <Badge tone="neutral">{t("Expired")}</Badge>
}

function GrantTable({ grants, showUser, onEnd, onReview }) {
  const { t } = useLanguage()
  return (
    <TableWrap>
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th scope="col">{t("Opened")}</th>
            {showUser && <th scope="col">{t("Clinician")}</th>}
            <th scope="col">{t("Patient")}</th>
            <th scope="col">{t("Reason")}</th>
            <th scope="col">{t("Status")}</th>
            <th scope="col">{t("Review")}</th>
            <th scope="col"><span className="sr-only">{t("Actions")}</span></th>
          </tr>
        </thead>
        <tbody>
          {grants.map((grant) => (
            <tr key={grant.id}>
              <td className="whitespace-nowrap tabular-nums">
                {formatWhen(grant.created_at)}
                <div className="text-xs text-ink-500">{t("until")} {formatWhen(grant.ended_at || grant.expires_at)}</div>
              </td>
              {showUser && <td>{grant.username}</td>}
              <td className="font-medium text-ink-900">{grant.patient_name} <span className="text-ink-500">{displayPatientId({ id: grant.patient, uhid: grant.patient_uhid })}</span></td>
              <td className="max-w-xs text-ink-700">{grant.reason}</td>
              <td><GrantState grant={grant} /></td>
              <td className="text-ink-700">
                {grant.reviewed_at
                  ? <>{grant.reviewed_by_username}{grant.review_note ? `: ${grant.review_note}` : ""}</>
                  : <Badge tone="warning">{t("Awaiting review")}</Badge>}
              </td>
              <td className="text-right">
                {onEnd && grant.is_active && <Button size="sm" variant="secondary" onClick={() => onEnd(grant)}>{t("End now")}</Button>}
                {onReview && !grant.reviewed_at && <Button size="sm" onClick={() => onReview(grant)}>{t("Review")}</Button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  )
}

function OpenAccessForm({ hospitalId, onOpened }) {
  const { t } = useLanguage()
  const [patientText, setPatientText] = useState("")
  const [reason, setReason] = useState("")
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    const patientId = parsePatientId(patientText)
    if (!patientId) {
      setError(t("Enter the patient number, for example P012."))
      return
    }
    if (reason.trim().length < MIN_REASON_LENGTH) {
      setError(t("Describe the emergency in at least {count} characters.", { count: MIN_REASON_LENGTH }))
      return
    }
    setSaving(true)
    setError("")
    try {
      await api.breakGlass.open(hospitalId, patientId, reason.trim())
      setPatientText("")
      setReason("")
      onOpened()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="mb-5">
      <CardHeader
        title={t("Open emergency access")}
        description={t("For a patient outside your care who needs you now. Access is time-limited, every record you open is logged, and an administrator reviews it.")}
      />
      <form onSubmit={submit} className="grid gap-4 p-5 md:grid-cols-3">
        <Field label="Patient number" required>
          <Input value={patientText} onChange={(e) => setPatientText(e.target.value)} placeholder="P012" />
        </Field>
        <Field label="Reason" required className="md:col-span-2" hint={t("At least {count} characters.", { count: MIN_REASON_LENGTH })}>
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} />
        </Field>
        {error && <Alert tone="danger" className="md:col-span-3">{error}</Alert>}
        <div className="md:col-span-3">
          <Button type="submit" icon={ShieldAlert} disabled={saving}>{saving ? t("Opening…") : t("Open access")}</Button>
        </div>
      </form>
    </Card>
  )
}

function EmergencyAccess() {
  const { t } = useLanguage()
  const { selectedHospital } = usePatient()
  const { activeRoleName } = useRole()
  const [promptText, promptDialog] = usePrompt()
  const [grants, setGrants] = useState([])
  const [pendingOnly, setPendingOnly] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [reloadToken, setReloadToken] = useState(0)

  const isClinician = CLINICAL_ROLES.includes(activeRoleName)
  const isReviewer = REVIEWER_ROLES.includes(activeRoleName)
  const reload = useCallback(() => setReloadToken((n) => n + 1), [])

  useEffect(() => {
    if (!selectedHospital?.id || !(isClinician || isReviewer)) {
      setLoading(false)
      return undefined
    }
    let cancelled = false
    setLoading(true)
    setError("")
    api.breakGlass
      .list(selectedHospital.id, { pendingReview: isReviewer && pendingOnly })
      .then((data) => !cancelled && setGrants(rowsOf(data)))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [selectedHospital?.id, isClinician, isReviewer, pendingOnly, reloadToken])

  const act = async (call) => {
    setError("")
    try {
      await call()
      reload()
    } catch (err) {
      setError(err.message)
    }
  }

  const endGrant = (grant) => act(() => api.breakGlass.end(grant.id))

  const reviewGrant = async (grant) => {
    const note = await promptText({
      title: t("Review emergency access"),
      label: t("Review note (what you checked)"),
      confirmLabel: t("Sign off"),
    })
    if (note === null) return
    await act(() => api.breakGlass.review(grant.id, note))
  }

  const header = (
    <PageHeader
      title={t("Emergency access")}
      description={t("Break-glass access to patients outside a clinician's care, with the reason and review.")}
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Emergency access" }]}
      actions={(isClinician || isReviewer) && <Button variant="secondary" icon={RefreshCw} onClick={reload}>{t("Refresh")}</Button>}
    />
  )

  if (!selectedHospital) {
    return <div>{header}<Card><EmptyState icon={ShieldAlert} title={t("Select a hospital")} /></Card></div>
  }

  if (!isClinician && !isReviewer) {
    return (
      <div>
        {header}
        <Card>
          <EmptyState
            icon={ShieldAlert}
            title={t("Not available for your role")}
            description={t("Doctors and Nurses open emergency access; Admins and Hospital Managers review it.")}
          />
        </Card>
      </div>
    )
  }

  return (
    <div>
      {header}
      {error && <Alert tone="danger" className="mb-4">{error}</Alert>}
      {isClinician && <OpenAccessForm hospitalId={selectedHospital.id} onOpened={reload} />}
      <Card>
        <CardHeader
          title={isReviewer ? t("Grants at {hospital}", { hospital: selectedHospital.name }) : t("Your emergency access")}
          actions={isReviewer && (
            <div className="flex gap-2">
              <Button size="sm" variant={pendingOnly ? "primary" : "secondary"} onClick={() => setPendingOnly(true)}>{t("Awaiting review")}</Button>
              <Button size="sm" variant={pendingOnly ? "secondary" : "primary"} onClick={() => setPendingOnly(false)}>{t("All")}</Button>
            </div>
          )}
        />
        {loading ? (
          <SkeletonRows rows={4} />
        ) : grants.length === 0 ? (
          <EmptyState icon={ShieldAlert} title={isReviewer && pendingOnly ? t("Nothing awaiting review") : t("No emergency access yet")} />
        ) : (
          <GrantTable
            grants={grants}
            showUser={isReviewer}
            onEnd={isClinician ? endGrant : null}
            onReview={isReviewer ? reviewGrant : null}
          />
        )}
      </Card>
      {promptDialog}
    </div>
  )
}

export default EmergencyAccess
