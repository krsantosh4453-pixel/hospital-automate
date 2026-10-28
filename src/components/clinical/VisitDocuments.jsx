import { useEffect, useState } from "react"
import { FileText, Printer, Send } from "lucide-react"
import api from "../../services/api.js"
import {
  Alert,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  Input,
  PrintSheet,
  Select,
  SkeletonRows,
  StatusBadge,
  Textarea,
} from "../ui"
import { formatPrintDate } from "../../utils/printDate.js"
import { CertificateDocument, ReferralDocument } from "../documents/ClinicalDocuments.jsx"

// Medical certificates (D10) and referrals (D11) for the patient of the
// selected visit. Both are signed on the server by the signed-in doctor.

const readResults = (data) => (Array.isArray(data) ? data : data?.results || [])

const today = () => new Date().toISOString().slice(0, 10)

const emptyCertificate = () => ({ kind: "Sick leave", diagnosis: "", startDate: today(), endDate: "", remarks: "" })
const emptyReferral = { target: "internal", doctorId: "", external: "", specialty: "", urgency: "Routine", reason: "" }

const REFERRAL_STATUSES = ["Pending", "Accepted", "Declined", "Completed"]

export default function VisitDocuments({ visit }) {
  const patientId = visit.patientApiId
  const [certificates, setCertificates] = useState([])
  const [referrals, setReferrals] = useState([])
  const [doctors, setDoctors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [certificateForm, setCertificateForm] = useState(emptyCertificate)
  const [referralForm, setReferralForm] = useState(emptyReferral)
  const [saving, setSaving] = useState("")
  const [printing, setPrinting] = useState(null)

  useEffect(() => {
    if (!patientId) return undefined
    let cancelled = false
    setLoading(true)
    setError("")
    Promise.all([
      api.clinical.certificates.list({ patientId }),
      api.clinical.referrals.list({ patientId }),
      api.doctors.list(),
    ])
      .then(([certs, refs, docs]) => {
        if (cancelled) return
        setCertificates(readResults(certs))
        setReferrals(readResults(refs))
        setDoctors(readResults(docs))
      })
      .catch((err) => !cancelled && setError(err.message || "Could not load the patient's documents."))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [patientId])

  const run = async (kind, action, success) => {
    setSaving(kind)
    setError("")
    setNotice("")
    try {
      await action()
      setNotice(success)
    } catch (err) {
      setError(err.message || "Could not save.")
    } finally {
      setSaving("")
    }
  }

  const issueCertificate = (event) => {
    event.preventDefault()
    run("certificate", async () => {
      const created = await api.clinical.certificates.create({
        patient: patientId,
        kind: certificateForm.kind,
        diagnosis: certificateForm.diagnosis,
        start_date: certificateForm.startDate,
        end_date: certificateForm.endDate || null,
        remarks: certificateForm.remarks,
      })
      setCertificates((prev) => [created, ...prev])
      setCertificateForm(emptyCertificate())
      setPrinting({ type: "certificate", record: created })
    }, "Certificate issued.")
  }

  const makeReferral = (event) => {
    event.preventDefault()
    const internal = referralForm.target === "internal"
    run("referral", async () => {
      const created = await api.clinical.referrals.create({
        patient: patientId,
        visit: visit.apiId,
        referred_to_doctor: internal ? Number(referralForm.doctorId) || null : null,
        referred_to_external: internal ? "" : referralForm.external,
        specialty: referralForm.specialty,
        urgency: referralForm.urgency,
        reason: referralForm.reason,
      })
      setReferrals((prev) => [created, ...prev])
      setReferralForm(emptyReferral)
      setPrinting({ type: "referral", record: created })
    }, "Referral sent.")
  }

  const changeStatus = (referral, status) =>
    run(`status-${referral.id}`, async () => {
      const updated = await api.clinical.referrals.setStatus(referral.id, status)
      setReferrals((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
    }, `Referral marked ${status.toLowerCase()}.`)

  const setCert = (field) => (event) => setCertificateForm({ ...certificateForm, [field]: event.target.value })
  const setRef = (field) => (event) => setReferralForm({ ...referralForm, [field]: event.target.value })
  const otherDoctors = doctors.filter((doctor) => String(doctor.id) !== String(visit.doctorApiId))

  return (
    <div className="space-y-5">
      {error && <Alert tone="danger" onDismiss={() => setError("")}>{error}</Alert>}
      {notice && <Alert tone="success" onDismiss={() => setNotice("")}>{notice}</Alert>}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card as="form" onSubmit={issueCertificate}>
          <CardHeader title="Issue medical certificate" description={`For ${visit.patientName}. Signed by you; cannot be edited later.`} />
          <div className="space-y-4 px-5 py-4">
            <Field label="Type" required>
              <Select value={certificateForm.kind} onChange={setCert("kind")}>
                <option>Sick leave</option>
                <option>Fitness</option>
                <option>Other</option>
              </Select>
            </Field>
            <Field label="Diagnosis"><Input value={certificateForm.diagnosis} onChange={setCert("diagnosis")} maxLength={255} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="From" required><Input type="date" value={certificateForm.startDate} onChange={setCert("startDate")} /></Field>
              <Field label="To" required={certificateForm.kind === "Sick leave"}>
                <Input type="date" min={certificateForm.startDate} value={certificateForm.endDate} onChange={setCert("endDate")} />
              </Field>
            </div>
            <Field label="Remarks"><Textarea rows={2} value={certificateForm.remarks} onChange={setCert("remarks")} /></Field>
            <Button type="submit" icon={FileText} loading={saving === "certificate"} className="w-full justify-center">Issue certificate</Button>
          </div>
        </Card>

        <Card as="form" onSubmit={makeReferral}>
          <CardHeader title="Refer patient" description="To a colleague here, or to an outside doctor or facility." />
          <div className="space-y-4 px-5 py-4">
            <Field label="Refer to" required>
              <Select value={referralForm.target} onChange={setRef("target")}>
                <option value="internal">A doctor at this hospital</option>
                <option value="external">Outside doctor or facility</option>
              </Select>
            </Field>
            {referralForm.target === "internal" ? (
              <Field label="Doctor" required>
                <Select value={referralForm.doctorId} onChange={setRef("doctorId")}>
                  <option value="">Choose a doctor</option>
                  {otherDoctors.map((doctor) => (
                    <option key={doctor.id} value={doctor.id}>{doctor.name} ({doctor.specialization})</option>
                  ))}
                </Select>
              </Field>
            ) : (
              <Field label="Doctor or facility" required><Input value={referralForm.external} onChange={setRef("external")} maxLength={200} /></Field>
            )}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Specialty"><Input value={referralForm.specialty} onChange={setRef("specialty")} maxLength={100} /></Field>
              <Field label="Urgency">
                <Select value={referralForm.urgency} onChange={setRef("urgency")}>
                  <option>Routine</option>
                  <option>Urgent</option>
                  <option>Emergency</option>
                </Select>
              </Field>
            </div>
            <Field label="Reason" required><Textarea rows={3} value={referralForm.reason} onChange={setRef("reason")} /></Field>
            <Button type="submit" icon={Send} loading={saving === "referral"} className="w-full justify-center">Send referral</Button>
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="Certificates and referrals" description={`All of ${visit.patientName}'s, newest first`} />
        <div className="px-5 py-4">
          {loading ? (
            <SkeletonRows rows={3} />
          ) : certificates.length + referrals.length === 0 ? (
            <EmptyState title="None yet" description="Issued certificates and referrals appear here." />
          ) : (
            <ul className="divide-y divide-line">
              {certificates.map((cert) => (
                <li key={`c${cert.id}`} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div>
                    <p className="font-medium text-ink-900">Certificate: {cert.kind}</p>
                    <p className="text-xs text-ink-500">{formatPrintDate(cert.issued_at)} · {cert.doctor_name}</p>
                  </div>
                  <Button size="sm" variant="secondary" icon={Printer} onClick={() => setPrinting({ type: "certificate", record: cert })}>Print</Button>
                </li>
              ))}
              {referrals.map((ref) => (
                <li key={`r${ref.id}`} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div>
                    <p className="font-medium text-ink-900">
                      Referral to {ref.referred_to_doctor_name || ref.referred_to_external}
                    </p>
                    <p className="text-xs text-ink-500">{formatPrintDate(ref.created_at)} · {ref.urgency} · {ref.referring_doctor_name}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={ref.status} />
                    <Select
                      aria-label={`Status of referral ${ref.id}`}
                      className="w-36"
                      value={ref.status}
                      disabled={saving === `status-${ref.id}`}
                      onChange={(event) => changeStatus(ref, event.target.value)}
                    >
                      {REFERRAL_STATUSES.map((status) => <option key={status}>{status}</option>)}
                    </Select>
                    <Button size="sm" variant="secondary" icon={Printer} onClick={() => setPrinting({ type: "referral", record: ref })}>Print</Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>

      <PrintSheet
        open={Boolean(printing)}
        onClose={() => setPrinting(null)}
        title={printing?.type === "referral" ? "Referral letter" : "Medical certificate"}
      >
        {printing?.type === "certificate" && <CertificateDocument certificate={printing.record} />}
        {printing?.type === "referral" && <ReferralDocument referral={printing.record} />}
      </PrintSheet>
    </div>
  )
}
