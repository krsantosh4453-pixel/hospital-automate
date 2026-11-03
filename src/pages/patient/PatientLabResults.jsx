import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { FlaskConical, Printer } from "lucide-react"
import { Alert, Button, Card, EmptyState, PrintSheet, SegmentedControl, SkeletonRows, StatusBadge } from "../../components/ui"
import { ImagingReportDocument, LabReportDocument } from "../../components/documents/ClinicalDocuments.jsx"
import { useLanguage } from "../../assets/context/LanguageContext.jsx"

function PatientLabResults() {
  const { t } = useLanguage()
  const { patient } = useAuth()
  const [labTests, setLabTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState("all")
  const [printing, setPrinting] = useState(null)
  // Signed radiology reports (G4); the server returns only signed ones to patients.
  const [imaging, setImaging] = useState([])
  const [printingStudy, setPrintingStudy] = useState(null)

  useEffect(() => {
    if (!patient?.id) return

    const fetchLabTests = async () => {
      setLoading(true)
      try {
        const data = await api.laboratory.tests.list(null, patient.id)
        const patientTests = data?.results || data || []
        setLabTests(patientTests)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchLabTests()
    api.imaging
      .list()
      .then((data) => setImaging(data?.results || data || []))
      .catch(() => setImaging([]))
  }, [patient?.id])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  // Results are shown to patients only after the lab releases them.
  const filteredTests = labTests.filter((test) => {
    if (filter === "ready") return test.status === "Released"
    if (filter === "progress") return test.status !== "Released" && test.status !== "Cancelled"
    return true
  })

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink-900 sm:text-2xl">{t("Lab reports")}</h1>
          <p className="mt-1 text-sm text-ink-500">{t("Results appear here once the laboratory has verified and released them.")}</p>
        </div>
        <SegmentedControl
          label="Filter lab tests"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: "All" },
            { value: "ready", label: "Results ready" },
            { value: "progress", label: "In progress" },
          ]}
        />
      </header>

      {error && <Alert tone="danger">{error}</Alert>}

      {loading ? (
        <Card><SkeletonRows rows={3} /></Card>
      ) : filteredTests.length === 0 ? (
        <Card>
          <EmptyState
            icon={FlaskConical}
            title={labTests.length ? "No tests match this filter" : "No lab tests yet"}
          />
        </Card>
      ) : (
        <ul className="space-y-4">
          {filteredTests.map((test) => {
            const released = test.status === "Released"
            return (
              <li key={test.id}>
                <Card>
                  <div className="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
                    <div>
                      <p className="font-semibold text-ink-900">{test.name || "Lab test"}</p>
                      <p className="text-[13px] text-ink-500">
                        {t("Ordered")}{" "}{formatDate(test.test_date)}
                        {test.doctor_name ? ` by ${test.doctor_name}` : ""}
                        {released && test.released_at ? ` · released ${formatDate(test.released_at)}` : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={released ? "Released" : test.status === "Cancelled" ? "Cancelled" : "In progress"} />
                      {released && (
                        <Button size="sm" variant="secondary" icon={Printer} onClick={() => setPrinting(test)}>{t("Print")}</Button>
                      )}
                    </div>
                  </div>
                  <div className="border-t border-line px-5 py-3 text-sm">
                    {released ? (
                      <p className="whitespace-pre-wrap text-ink-900">{test.result || "No result text was entered."}</p>
                    ) : test.status === "Cancelled" ? (
                      <p className="text-ink-500">{t("This test was cancelled.")}</p>
                    ) : (
                      <p className="text-ink-500">{t("Your result will appear here once it is verified by the laboratory.")}</p>
                    )}
                  </div>
                </Card>
              </li>
            )
          })}
        </ul>
      )}

      {imaging.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold text-ink-900">{t("Imaging reports")}</h2>
          <ul className="space-y-3">
            {imaging.map((study) => (
              <li key={study.id}>
                <Card>
                  <div className="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
                    <div>
                      <p className="font-semibold text-ink-900">{study.modality} · {study.body_part}</p>
                      <p className="text-[13px] text-ink-500">{t("Reported")}{" "}{formatDate(study.reported_at)}{study.reported_by_name ? ` by ${study.reported_by_name}` : ""}</p>
                    </div>
                    <Button size="sm" variant="secondary" icon={Printer} onClick={() => setPrintingStudy(study)}>{t("Print")}</Button>
                  </div>
                  <p className="border-t border-line px-5 py-3 text-sm text-ink-900"><span className="font-medium">{t("Impression:")}</span> {study.impression}</p>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      )}

      <PrintSheet open={Boolean(printingStudy)} onClose={() => setPrintingStudy(null)} title={t("Imaging report")}>
        {printingStudy && <ImagingReportDocument study={printingStudy} />}
      </PrintSheet>

      <PrintSheet open={Boolean(printing)} onClose={() => setPrinting(null)} title={t("Lab report")}>
        {printing && <LabReportDocument test={printing} />}
      </PrintSheet>
    </div>
  )
}

export default PatientLabResults
