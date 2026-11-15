import { useCallback, useEffect, useState } from "react"
import { ShieldCheck } from "lucide-react"
import api from "../../services/api.js"
import { useToast } from "../Toast.jsx"
import { Alert, Badge, Button, Card, CardHeader, EmptyState, Field, Modal, Select, TableWrap, Textarea } from "../ui"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

const OPEN = "received,in_progress"
const shortDate = (value) => (value ? new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "")

/**
 * P1-03 (DPDP Act 2023): open data requests and complaints from patients, for
 * the hospital's Admin or Manager to answer by their due date. Erasure is
 * decided here, by a person, against medical-record retention duties.
 */
export default function DataRightsRequests() {
  const { t } = useLanguage()
  const toast = useToast()
  const [rows, setRows] = useState([])
  const [error, setError] = useState("")
  const [answering, setAnswering] = useState(null)
  const [answer, setAnswer] = useState({ status: "completed", response: "" })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      setRows((await api.consent.rights.list({ status: OPEN }))?.results || [])
      setError("")
    } catch (err) {
      setError(err.message || "Data requests could not be loaded.")
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const open = (row) => {
    setAnswering(row)
    setAnswer({ status: "completed", response: "" })
  }

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await api.consent.rights.respond(answering.id, answer)
      toast.success(t("Answer recorded."))
      setAnswering(null)
      load()
    } catch (err) {
      toast.error(err.message || "The answer was not saved.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className="mt-6">
      <CardHeader icon={ShieldCheck} title="Patients' data requests"
        description="Requests and complaints under the DPDP Act, answered by their due date." />
      {error && <Alert tone="danger" className="mx-5 mb-4">{error}</Alert>}
      {rows.length === 0 && !error ? (
        <EmptyState compact title={t("No open data requests")} />
      ) : (
        <TableWrap>
          <table className="hms-table">
            <thead>
              <tr><th>{t("Patient")}</th><th>{t("Request")}</th><th>{t("Due")}</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.patient_name}</td>
                  <td>{row.kind_label}{row.details ? <span className="block text-xs text-ink-500">{row.details}</span> : null}</td>
                  <td className="tabular-nums">{shortDate(row.due_at)}{row.overdue && <Badge tone="danger" className="ml-2">{t("Overdue")}</Badge>}</td>
                  <td className="text-right"><Button size="sm" variant="secondary" onClick={() => open(row)}>{t("Answer")}</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}
      <Modal open={Boolean(answering)} onClose={() => setAnswering(null)} title={t("Answer the request")}
        footer={<><Button variant="secondary" onClick={() => setAnswering(null)}>{t("Cancel")}</Button>
          <Button type="submit" form="rights-answer" loading={saving}>{t("Save")}</Button></>}>
        <form id="rights-answer" onSubmit={save} className="space-y-3">
          <Field label="Outcome" required>
            <Select value={answer.status} onChange={(e) => setAnswer({ ...answer, status: e.target.value })}>
              <option value="in_progress">{t("In progress")}</option>
              <option value="completed">{t("Completed")}</option>
              <option value="refused">{t("Refused")}</option>
            </Select>
          </Field>
          <Field label="Answer to the patient" hint="What was done, or why not (for example a record that must be kept by law).">
            <Textarea rows={4} maxLength={2000} value={answer.response}
              onChange={(e) => setAnswer({ ...answer, response: e.target.value })} />
          </Field>
        </form>
      </Modal>
    </Card>
  )
}
