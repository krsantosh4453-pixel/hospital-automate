import { useState, useEffect } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import api from "../services/api.js"
import { useLinkedPatient } from "../utils/linkedPatient.js"
import { Eye, FlaskConical, Hospital, Pencil, Plus, Printer, RefreshCw, ScanLine, Tag, XCircle } from "lucide-react"
import { useToast } from "../components/Toast.jsx"
import {
  Badge,
  Button,
  Card,
  DescriptionList,
  EmptyState,
  ErrorState,
  Field,
  Modal,
  PageHeader,
  PrintSheet,
  SearchInput,
  Select,
  SkeletonRows,
  StatTile,
  StatusBadge,
  TableWrap,
  Tabs,
  Toolbar,
  useConfirm,
  usePrompt,
} from "../components/ui"
import { LabReportDocument } from "../components/documents/ClinicalDocuments.jsx"
import SampleLabel from "../components/laboratory/SampleLabel.jsx"
import SampleScanDialog from "../components/laboratory/SampleScanDialog.jsx"
import CriticalResults from "../components/laboratory/CriticalResults.jsx"
import PatientPicker from "../components/patients/PatientPicker.jsx"
import VisitSelect from "../components/clinical/VisitSelect.jsx"
import { useLanguage } from "../assets/context/LanguageContext.jsx"

function Laboratory() {
  const { t } = useLanguage()
  // Doctors order tests; a Hospital Manager only views them.
  const { canAdd, activeRoleName } = useRole()
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()
  const [promptText, promptDialog] = usePrompt()


  const { selectedHospital } = usePatient()

  const [tests, setTests] = useState([])
  const [doctorOptions, setDoctorOptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)

  // Backend workflow status -> the three summary states this page shows.
  const SUMMARY = {
    Ordered: "Pending",
    "Sample Pending": "Pending",
    Collected: "Processing",
    Dispatched: "Processing",
    Received: "Processing",
    Processing: "Processing",
    "Result Entered": "Processing",
    Verified: "Processing",
    Released: "Completed",
    Cancelled: "Cancelled",
  }

  // Next lab action for each stage (label, client method, needs a result text).
  const NEXT_STEP = {
    Ordered: ["Collect Sample", "collectSample"],
    "Sample Pending": ["Collect Sample", "collectSample"],
    Collected: ["Dispatch Sample", "dispatchSample"],
    Dispatched: ["Receive in Lab", "receiveSample"],
    Received: ["Start Processing", "startProcessing"],
    Processing: ["Enter Result", "enterResult", true],
    "Result Entered": ["Verify Result", "verifyResult"],
    Verified: ["Release Result", "releaseResult"],
  }

  // L-1: a wrong result is sent back before release; the server keeps it.
  const REJECTABLE = ["Result Entered", "Verified"]

  const rows = (data) => (Array.isArray(data) ? data : data?.results || [])

  const toRow = (t) => ({
    id: `LAB-${t.id}`,
    apiId: t.id,
    patient: t.patient_name || `Patient #${t.patient}`,
    patientId: t.patient,
    test: t.name,
    doctor: t.doctor_name || "",
    doctorId: t.doctor,
    date: t.test_date ? new Date(t.test_date).toLocaleDateString("en-IN") : "",
    priority: t.priority || "Normal",
    stage: t.status,
    status: SUMMARY[t.status] || t.status,
    result: t.status === "Released" ? t.result || "—" : "Pending",
    hospitalId: t.hospital,
    // The API row as returned, for the printed report.
    record: t,
  })

  const loadTests = async () => {
    if (!selectedHospital) return
    setLoading(true)
    setError(null)
    try {
      // The order form finds its patient by search (PatientPicker), not a preloaded list.
      const [testData, doctorData] = await Promise.all([
        api.laboratory.tests.list(selectedHospital.id),
        api.doctors.list(selectedHospital.id),
      ])
      setTests(rows(testData).map(toRow))
      setDoctorOptions(rows(doctorData))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTests()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHospital?.id])

  const testsData = tests

  // Opened from another module (e.g. the ER) with ?q=<patient name>.
  const linked = useLinkedPatient()
  const [search, setSearch] = useState(linked.query)

  const [statusFilter, setStatusFilter] =
    useState("All Status")

  const [priorityFilter, setPriorityFilter] =
    useState("All Priority")

  const [showForm, setShowForm] =
    useState(false)

  const [showView, setShowView] =
    useState(false)

  const [printingTest, setPrintingTest] = useState(null)
  // Barcode scan (F6) and tube label printing.
  const [scanning, setScanning] = useState(false)
  const [labelTest, setLabelTest] = useState(null)
  const [selectedTest, setSelectedTest] =
    useState(null)

  const [formData, setFormData] = useState({
    patient: "",
    visit: "",
    test: "",
    doctor: "",
    date: "",
    priority: "Normal",
  })


  // =========================
  // Selected Hospital Tests
  // =========================

  const hospitalTests = selectedHospital
    ? testsData.filter(
      (test) =>
        test.hospitalId ===
        selectedHospital.id
    )
    : []


  // =========================
  // Filter Tests
  // =========================

  const filteredTests =
    hospitalTests.filter((test) => {

      const matchesSearch =
        test.patient
          .toLowerCase()
          .includes(
            search.toLowerCase()
          ) ||
        test.test
          .toLowerCase()
          .includes(
            search.toLowerCase()
          ) ||
        String(test.id)
          .toLowerCase()
          .includes(
            search.toLowerCase()
          )

      const matchesStatus =
        statusFilter ===
        "All Status" ||
        test.status ===
        statusFilter

      const matchesPriority =
        priorityFilter ===
        "All Priority" ||
        test.priority ===
        priorityFilter

      return (
        matchesSearch &&
        matchesStatus &&
        matchesPriority
      )
    })


  // =========================
  // Statistics
  // =========================

  const pendingCount =
    hospitalTests.filter(
      (test) =>
        test.status ===
        "Pending"
    ).length

  const processingCount =
    hospitalTests.filter(
      (test) =>
        test.status ===
        "Processing"
    ).length

  const completedCount =
    hospitalTests.filter(
      (test) =>
        test.status ===
        "Completed"
    ).length


  // =========================
  // Form Change
  // =========================

  const handleChange = (e) => {

    const { name, value } =
      e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }


  // =========================
  // Reset Form
  // =========================

  const resetForm = () => {

    setFormData({
      patient: "",
      visit: "",
      test: "",
      doctor: "",
      date: "",
      priority: "Normal",
    })

    setSelectedTest(null)

    setShowForm(false)
  }


  // =========================
  // New Lab Test
  // =========================

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!selectedHospital) {
      toast.warning(
        "Please select a hospital first."
      )
      return
    }

    try {
      await api.laboratory.tests.create({
        hospital: selectedHospital.id,
        patient: Number(formData.patient),
        doctor: formData.doctor ? Number(formData.doctor) : null,
        // Prompt 5 (INT-002): the order belongs to its visit when one is chosen.
        visit: formData.visit ? Number(formData.visit) : null,
        name: formData.test,
        priority: formData.priority,
      })
      resetForm()
      await loadTests()
    } catch (err) {
      toast.error(t("Lab order was not created: {reason}", { reason: err.message }))
    }
  }

  // =========================
  // View
  // =========================

  const handleView = (test) => {

    setSelectedTest(test)

    setShowView(true)
  }


  // =========================
  // Edit
  // =========================

  const handleEdit = (test) => {

    setSelectedTest(test)

    setFormData({

      patient:
        test.patientId ? String(test.patientId) : "",

      test:
        test.test,

      // The select holds doctor ids; using the name here cleared the doctor on save.
      doctor:
        test.doctorId ? String(test.doctorId) : "",

      date:
        test.date,

      priority:
        test.priority,
    })

    setShowForm(true)
  }


  // =========================
  // Update
  // =========================

  const handleUpdate = async (e) => {
    e.preventDefault()

    try {
      await api.laboratory.tests.update(selectedTest.apiId, {
        hospital: selectedHospital.id,
        patient: selectedTest.patientId,
        name: formData.test,
        doctor: formData.doctor ? Number(formData.doctor) : null,
        priority: formData.priority,
      })
      resetForm()
      await loadTests()
    } catch (err) {
      toast.error(t("Lab order was not updated: {reason}", { reason: err.message }))
    }
  }

  // =========================
  // Delete
  // =========================

  const handleDelete = async (id) => {
    const test = tests.find((t) => t.id === id)
    const confirmed =
      (await confirm(
        "Cancel this laboratory order? It stays in the record as cancelled."
      ))

    if (!confirmed || !test) {
      return
    }

    try {
      await api.laboratory.tests.cancel(test.apiId)
      await loadTests()
    } catch (err) {
      toast.error(t("Order was not cancelled: {reason}", { reason: err.message }))
    }
  }

  // =========================
  // Process
  // =========================

  const handleProcess = async (id) => {
    const test = tests.find((t) => t.id === id)
    const step = test && NEXT_STEP[test.stage]
    if (!step) return
    const [label, method, needsResult] = step
    let payload = {}
    if (needsResult) {
      payload = await askForResult(test)
      if (!payload) return
    }
    setBusyId(id)
    try {
      await api.laboratory.tests[method](test.apiId, payload)
      await loadTests()
    } catch (err) {
      toast.error(`${label} failed: ${err.message}`)
    } finally {
      setBusyId(null)
    }
  }

  // H-14: when the hospital has reference ranges for this test, ask for each
  // parameter's value so the server can flag it. Empty means "not measured".
  const askForResult = async (test) => {
    let ranges = []
    try {
      const data = await api.laboratory.referenceRanges.list(selectedHospital?.id, test.test)
      ranges = Array.isArray(data) ? data : data?.results || []
    } catch (err) {
      toast.warning(t("Reference ranges could not be loaded, so values will not be flagged: {reason}", { reason: err.message }))
    }
    const parameters = [...new Set(ranges.map((r) => r.parameter))]
    const resultData = {}
    for (const parameter of parameters) {
      const unit = ranges.find((r) => r.parameter === parameter)?.unit || ""
      const value = await promptText(t("{parameter} ({unit}) for {test}, empty if not measured:", { parameter, unit, test: test.test }))
      if (value === null) return null
      if (value.trim()) resultData[parameter] = value.trim()
    }
    const resultText = await promptText(
      parameters.length
        ? t("Comment for {test} ({patient}), optional:", { test: test.test, patient: test.patient })
        : t("Result for {test} ({patient}):", { test: test.test, patient: test.patient }),
    )
    if (resultText === null) return null
    if (!resultText.trim() && Object.keys(resultData).length === 0) return null
    return { result_text: resultText.trim(), result_data: resultData }
  }

  const handleReject = async (test) => {
    const reason = await promptText({
      title: t("Reject the result for {test}?", { test: test.test }),
      label: t("Why is it wrong? The test goes back to processing and the result is entered again."),
      confirmLabel: t("Reject Result"),
    })
    if (!reason || !reason.trim()) return
    setBusyId(test.id)
    try {
      await api.laboratory.tests.rejectResult(test.apiId, reason.trim())
      toast.success(t("Result sent back. Enter the corrected result."))
      await loadTests()
    } catch (err) {
      toast.error(t("Result not rejected: {reason}", { reason: err.message }))
    } finally {
      setBusyId(null)
    }
  }

  // Workflow stages in order, for the per-order progress indicator.
  const STAGES = ["Ordered", "Collected", "Dispatched", "Received", "Processing", "Result Entered", "Verified", "Released"]
  const stageIndex = (stage) => {
    const i = STAGES.indexOf(stage === "Sample Pending" ? "Ordered" : stage)
    return i === -1 ? 0 : i
  }

  const TEST_CHOICES = ["Complete Blood Count", "Blood Sugar", "Lipid Profile", "Liver Function Test", "Kidney Function Test", "Thyroid Profile"]

  const openNew = () => {
    if (!selectedHospital) {
      toast.warning("Please select a hospital first.")
      return
    }
    setSelectedTest(null)
    setFormData({ patient: "", test: "", doctor: "", date: "", priority: "Normal" })
    setShowForm(true)
  }

  const header = (
    <PageHeader
      title={t("Laboratory")}
      description={selectedHospital ? t("Orders, samples and results at {hospital}.", { hospital: selectedHospital.name }) : t("Select a hospital from the header to view laboratory orders.")}
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Laboratory" }]}
      actions={
        selectedHospital && (
          <>
            <Button variant="secondary" icon={RefreshCw} onClick={loadTests} disabled={loading}>{t("Refresh")}</Button>
            <Button variant="secondary" icon={ScanLine} onClick={() => setScanning(true)}>{t("Scan sample")}</Button>
            {canAdd("Laboratory") && <Button icon={Plus} onClick={openNew}>{t("New lab order")}</Button>}
          </>
        )
      }
    />
  )

  if (!selectedHospital) {
    return (
      <>{confirmDialog}{promptDialog}<div className="space-y-5">
        {header}
        <Card><EmptyState icon={Hospital} title={t("Select a hospital")} description="Choose a hospital in the header to see its laboratory worklist." /></Card>
      </div></>
    )
  }

  const statusTabs = [
    { id: "All Status", label: "All", count: hospitalTests.length },
    { id: "Pending", label: "Awaiting sample", count: pendingCount },
    { id: "Processing", label: "In lab", count: processingCount },
    { id: "Completed", label: "Released", count: completedCount },
  ]

  return (
    <>{confirmDialog}{promptDialog}<div className="space-y-5">
      {header}

      <CriticalResults
        hospitalId={selectedHospital.id}
        canAcknowledge={activeRoleName === "Doctor" || activeRoleName === "Admin"}
        promptText={promptText}
        onChange={loadTests}
      />

      {error ? (
        <Card><ErrorState title={t("Laboratory orders could not be loaded")} message={error} onRetry={loadTests} /></Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <StatTile icon={FlaskConical} label="All orders" value={loading ? null : hospitalTests.length} onClick={() => setStatusFilter("All Status")} />
            <StatTile icon={FlaskConical} tone="warning" label="Awaiting sample" value={loading ? null : pendingCount} onClick={() => setStatusFilter("Pending")} />
            <StatTile icon={FlaskConical} tone="accent" label="In the lab" value={loading ? null : processingCount} onClick={() => setStatusFilter("Processing")} />
            <StatTile icon={FlaskConical} tone="success" label="Released" value={loading ? null : completedCount} onClick={() => setStatusFilter("Completed")} />
          </div>

          <Card className="overflow-hidden">
            <div className="px-4 pt-2">
              <Tabs tabs={statusTabs} value={statusFilter} onChange={setStatusFilter} label="Filter by stage" />
            </div>
            <Toolbar>
              <SearchInput value={search} onChange={setSearch} placeholder={t("Patient, test or order ID")} label="Search lab orders" className="w-full sm:max-w-xs" />
              <Select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} aria-label={t("Filter by priority")} className="w-full sm:w-44">
                <option value="All Priority">{t("All Priority")}</option>
                <option value="Normal">{t("Normal")}</option>
                <option value="Urgent">{t("Urgent")}</option>
              </Select>
            </Toolbar>

            {loading ? (
              <SkeletonRows rows={5} />
            ) : filteredTests.length === 0 ? (
              <EmptyState
                icon={FlaskConical}
                title={hospitalTests.length ? t("No orders match these filters") : t("No laboratory orders yet")}
                action={!hospitalTests.length && canAdd("Laboratory") && <Button icon={Plus} onClick={openNew}>{t("New lab order")}</Button>}
              />
            ) : (
              <TableWrap>
                <table className="hms-table">
                  <caption className="sr-only">{t("Laboratory orders")}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t("Order")}</th>
                      <th scope="col">{t("Patient")}</th>
                      <th scope="col">{t("Test")}</th>
                      <th scope="col">{t("Priority")}</th>
                      <th scope="col">{t("Stage")}</th>
                      <th scope="col"><span className="sr-only">{t("Actions")}</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...filteredTests]
                      .sort((a, b) => (a.priority === "Urgent" ? 0 : 1) - (b.priority === "Urgent" ? 0 : 1))
                      .map((test) => {
                        const step = NEXT_STEP[test.stage]
                        const idx = stageIndex(test.stage)
                        return (
                          <tr key={test.id}>
                            <td className="whitespace-nowrap">
                              <span className="block font-medium text-ink-900 tabular-nums">{test.id}</span>
                              <span className="block text-xs text-ink-500 tabular-nums">{test.date}</span>
                            </td>
                            <td>
                              <span className="block font-medium text-ink-900">{test.patient}</span>
                              <span className="block text-xs text-ink-500">{test.doctor ? t("Ordered by {doctor}", { doctor: test.doctor }) : t("No referring doctor")}</span>
                            </td>
                            <td>{test.test}</td>
                            <td>{test.priority === "Urgent" ? <Badge tone="danger" dot>{t("Urgent")}</Badge> : <span className="text-ink-500">{t("Normal")}</span>}</td>
                            <td className="min-w-[11rem]">
                              {test.stage === "Cancelled" ? (
                                <StatusBadge status="Cancelled" />
                              ) : (
                                <>
                                  <span className="block text-[13px] font-medium text-ink-800">{test.stage}</span>
                                  <span className="mt-1.5 flex gap-0.5" aria-hidden="true">
                                    {STAGES.map((s, i) => (
                                      <span key={s} className={`h-1.5 flex-1 rounded-full ${i <= idx ? (test.stage === "Released" ? "bg-green-500" : "bg-brand-500") : "bg-ink-200"}`} />
                                    ))}
                                  </span>
                                  <span className="sr-only">{t("Step")}{" "}{idx + 1}{" "}{t("of")}{" "}{STAGES.length}</span>
                                </>
                              )}
                            </td>
                            <td>
                              <div className="flex items-center justify-end gap-1">
                                {step && (
                                  <Button size="sm" variant="subtle" loading={busyId === test.id} onClick={() => handleProcess(test.id)}>
                                    {step[0]}
                                  </Button>
                                )}
                                {REJECTABLE.includes(test.stage) && (
                                  <Button size="sm" variant="danger-ghost" disabled={busyId === test.id} onClick={() => handleReject(test)}>
                                    {t("Reject Result")}
                                  </Button>
                                )}
                                <Button variant="ghost" size="icon-sm" icon={Eye} onClick={() => handleView(test)} aria-label={`View ${test.id}`} title={t("View")} />
                                {test.record?.sample_collection?.sample_id && (
                                  <Button variant="ghost" size="icon-sm" icon={Tag} onClick={() => setLabelTest(test.record)} aria-label={t("Print sample label for {order}", { order: test.id })} title={t("Print sample label")} />
                                )}
                                {test.stage === "Released" && (
                                  <Button variant="ghost" size="icon-sm" icon={Printer} onClick={() => setPrintingTest(test.record)} aria-label={`Print ${test.id}`} title={t("Print report")} />
                                )}
                                {test.stage !== "Released" && test.stage !== "Cancelled" && (
                                  <>
                                    <Button variant="ghost" size="icon-sm" icon={Pencil} onClick={() => handleEdit(test)} aria-label={`Edit ${test.id}`} title={t("Edit")} />
                                    <Button variant="danger-ghost" size="icon-sm" icon={XCircle} onClick={() => handleDelete(test.id)} aria-label={`Cancel ${test.id}`} title={t("Cancel order")} />
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                  </tbody>
                </table>
              </TableWrap>
            )}
          </Card>
        </>
      )}

      {/* New / edit order */}
      <Modal
        open={showForm}
        onClose={resetForm}
        title={selectedTest ? `Edit ${selectedTest.id}` : t("New lab order")}
        description={selectedHospital.name}
        footer={
          <>
            <Button variant="secondary" onClick={resetForm}>{t("Cancel")}</Button>
            <Button type="submit" form="lab-form">{selectedTest ? t("Save changes") : t("Create order")}</Button>
          </>
        }
      >
        <form id="lab-form" onSubmit={selectedTest ? handleUpdate : handleSubmit} className="space-y-4">
          <Field label="Patient" required hint={selectedTest ? t("The patient of an existing order cannot be changed.") : undefined}>
            {/* Lookup: every ordering role may use it, including Lab Staff for walk-ins. */}
            <PatientPicker hospitalId={selectedHospital.id} source="lookup" value={formData.patient}
              disabled={Boolean(selectedTest)}
              selected={selectedTest ? { id: formData.patient, name: selectedTest.patient } : null}
              onChange={(id) => setFormData((current) => ({ ...current, patient: id, visit: "" }))} />
          </Field>
          {!selectedTest && (
            <VisitSelect hospitalId={selectedHospital.id} patientId={formData.patient}
              value={formData.visit} onChange={(visit) => setFormData((current) => ({ ...current, visit }))} />
          )}
          <Field label="Test" required>
            <Select name="test" value={formData.test} onChange={handleChange}>
              <option value="">{t("Select test")}</option>
              {TEST_CHOICES.map((t) => <option value={t} key={t}>{t}</option>)}
              {formData.test && !TEST_CHOICES.includes(formData.test) && <option>{formData.test}</option>}
            </Select>
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Referring doctor">
              <Select name="doctor" value={formData.doctor} onChange={handleChange}>
                <option value="">{t("Not specified")}</option>
                {doctorOptions.map((doctor) => <option key={doctor.id} value={doctor.id}>{doctor.name}</option>)}
              </Select>
            </Field>
            <Field label="Priority">
              <Select name="priority" value={formData.priority} onChange={handleChange}>
                <option value="Normal">{t("Normal")}</option>
                <option value="Urgent">{t("Urgent")}</option>
              </Select>
            </Field>
          </div>
          <p className="text-xs text-ink-500">{t("The order date is set by the server when the order is created.")}</p>
        </form>
      </Modal>

      {/* Details */}
      <Modal
        open={showView && Boolean(selectedTest)}
        onClose={() => setShowView(false)}
        title={t("Laboratory order")}
        description={selectedTest?.id}
        footer={<Button variant="secondary" onClick={() => setShowView(false)}>{t("Close")}</Button>}
      >
        {selectedTest && (
          <div className="space-y-5">
            <DescriptionList
              items={[
                { label: "Patient", value: selectedTest.patient },
                { label: "Test", value: selectedTest.test },
                { label: "Referring doctor", value: selectedTest.doctor },
                { label: "Ordered on", value: selectedTest.date },
                { label: "Priority", value: selectedTest.priority },
                { label: "Stage", value: selectedTest.stage },
              ]}
            />
            <div className="rounded-xl border border-line bg-ink-50 px-4 py-3">
              <p className="text-xs font-medium text-ink-500">{t("Result")}</p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-ink-900">
                {selectedTest.stage === "Released" ? selectedTest.result : t("Shown here once the result is verified and released.")}
              </p>
            </div>
          </div>
        )}
      </Modal>

      <PrintSheet open={Boolean(labelTest)} onClose={() => setLabelTest(null)} title={t("Sample label")}>
        {labelTest && <SampleLabel test={labelTest} />}
      </PrintSheet>

      <SampleScanDialog
        open={scanning}
        onClose={() => setScanning(false)}
        nextStepFor={(status) => NEXT_STEP[status]?.[0]}
        onNextStep={(found) => handleProcess(`LAB-${found.id}`)}
      />

      <PrintSheet open={Boolean(printingTest)} onClose={() => setPrintingTest(null)} title={t("Lab report")}>
        {printingTest && <LabReportDocument test={printingTest} />}
      </PrintSheet>
    </div></>
  )
}

export default Laboratory
