import { useMemo, useState, useEffect, useId } from "react"

import { usePatient } from "../assets/context/PatientContext.jsx"
import { useAuth } from "../assets/context/AuthContext.jsx"
import api from "../services/api.js"
import { ChartColumnIcon, ClipboardListIcon, DropletIcon, HeartPulseIcon, HospitalIcon, HouseIcon, NotebookPenIcon, PillIcon, StethoscopeIcon, UserIcon, UserRoundIcon, UsersIcon, WalletIcon } from "lucide-react"
import { useToast } from "../components/Toast.jsx"
import { Alert, Button, Card, CardHeader, EmptyState, Modal as UiModal, PageHeader as UiPageHeader, Tabs } from "../components/ui"
import { UserPlus as UserPlusIcon } from "lucide-react"
import { useConfirm } from "../components/ui"

function Nurses() {
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()

  const { selectedHospital } = usePatient()

  // =====================================================
  // CURRENT USER (the signed-in staff member)
  // =====================================================

  const { user: authUser } = useAuth()
  const staff = authUser?.user || authUser || {}
  const staffRoles = staff.roles || authUser?.roles || []
  const currentUser = {
    id: staff.id,
    name:
      [staff.first_name, staff.last_name].filter(Boolean).join(" ") ||
      staff.full_name ||
      staff.username ||
      "Staff member",
    role: staff.staff_role || staffRoles[0] || "",
    hospitalId: selectedHospital?.id,
    department: staff.department || "",
    shift: "",
    phone: staff.phone || "",
    email: staff.email || "",
    qualification: "",
    joiningDate: "",
    status: "On Duty",
  }

  // Admin and Hospital Manager manage the nurse roster (the backend enforces this too).
  const isAdmin = staffRoles.includes("Admin") || staffRoles.includes("Hospital Manager")
  const isNurse = staffRoles.includes("Nurse")

  // =====================================================
  // STATE - loaded from the API only (no demo data)
  // =====================================================

  const [nurses, setNurses] = useState([])
  const [patients, setPatients] = useState([])
  const [vitals, setVitals] = useState([])
  const [assessments, setAssessments] = useState([])
  const [notes, setNotes] = useState([])
  const [orders] = useState([])
  const [mar, setMar] = useState([])
  const [bloodRequests, setBloodRequests] = useState([])
  const [discharges] = useState([])
  const [billing, setBilling] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const rows = (data) => (Array.isArray(data) ? data : data?.results || [])
  const fmtTime = (value) =>
    value ? new Date(value).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : ""
  const fmtDate = (value) => (value ? new Date(value).toLocaleDateString("en-IN") : "")

  const loadData = async () => {
    if (!selectedHospital) return
    const hospitalId = selectedHospital.id
    setLoading(true)
    setError(null)
    const sources = [
      ["nurses", api.nurses.list(hospitalId)],
      ["admitted patients", api.ipd.admissions.list(hospitalId)],
      ["assessments", api.nurses.assessments.list(hospitalId)],
      ["notes", api.nurses.notes.list(hospitalId)],
      ["medication schedule", api.nurses.mar.dueMedications(hospitalId)],
      ["blood requests", api.bloodbank.requests.list(hospitalId)],
      ["bills", api.billing.invoices.list(hospitalId)],
    ]
    const results = await Promise.allSettled(sources.map(([, promise]) => promise))
    const failed = []
    const value = (index) => {
      const result = results[index]
      if (result.status === "fulfilled") return rows(result.value)
      failed.push(`${sources[index][0]} (${result.reason?.message || "error"})`)
      return []
    }

    setNurses(value(0).map((n) => ({
      id: n.id,
      hospitalId: n.hospital,
      name: n.name,
      department: n.department || "",
      shift: n.shift || "",
      phone: n.phone || "",
      email: n.email || "",
      qualification: n.qualification || "",
      joiningDate: n.joining_date || "",
      status: n.status || "",
    })))

    const admissions = value(1).filter((a) => a.status === "Admitted" || a.status === "Discharge Initiated")
    setPatients(admissions.map((a) => ({
      id: a.patient,
      admissionId: a.id,
      hospitalId: a.hospital,
      name: a.patient_name || `Patient #${a.patient}`,
      age: a.patient_age ?? "",
      ward: a.current_bed?.ward_name || "",
      bed: a.current_bed?.bed_number || "",
      doctor: a.admitting_doctor_name || "",
      department: "",
      status: a.status,
    })))

    // Vitals are recorded as nursing "Focused" assessments with a vitals record.
    const assessmentRows = value(2)
    setVitals(assessmentRows.filter((a) => a.vitals && Object.keys(a.vitals).length > 0).map((a) => ({
      id: a.id,
      hospitalId: a.hospital,
      patientId: a.patient,
      patientName: a.patient_name,
      temperature: a.vitals.temperature ?? "",
      bp: a.vitals.bp ?? "",
      pulse: a.vitals.pulse ?? "",
      spo2: a.vitals.spo2 ?? "",
      respiratoryRate: a.vitals.respiratory_rate ?? "",
      recordedBy: a.nurse_name || a.recorded_by_name || "",
      time: fmtTime(a.assessed_at),
    })))
    setAssessments(assessmentRows.filter((a) => a.plan_of_care).map((a) => ({
      id: a.id,
      hospitalId: a.hospital,
      patientId: a.patient,
      patientName: a.patient_name,
      assessment: a.plan_of_care,
      nurse: a.nurse_name || "",
      date: fmtDate(a.assessed_at),
    })))

    setNotes(value(3).map((n) => ({
      id: n.id,
      hospitalId: n.hospital,
      patientId: n.patient,
      text: n.note,
      createdBy: n.nurse_name || "",
      date: fmtDate(n.created_at),
    })))

    setMar(value(4).map((d) => ({
      id: d.id,
      hospitalId: d.hospital,
      patientId: d.patient,
      patientName: d.patient_name,
      medicine: d.medicine_name,
      dose: d.dose,
      route: d.route,
      frequency: d.frequency,
      time: fmtTime(d.scheduled_time),
      status: d.status === "Scheduled" ? (d.is_delayed ? "Delayed" : "Due") : d.status,
    })))

    setBloodRequests(value(5).map((b) => ({
      id: b.id,
      hospitalId: b.hospital,
      patientId: b.patient,
      patientName: b.patient_name,
      bloodGroup: b.blood_group,
      units: b.units,
      urgency: b.priority || b.urgency || "",
      status: b.status,
    })))

    setBilling(value(6).map((bill) => ({
      id: bill.id,
      hospitalId: bill.hospital,
      patientId: bill.patient,
      amount: bill.total_amount ?? bill.total,
      status: bill.status,
    })))

    if (failed.length > 0) {
      setError(`Could not load: ${failed.join("; ")}`)
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHospital?.id])

  // Data shown on the page is exactly what the API returned.
  const nursesData = nurses
  const patientsData = patients
  const vitalsData = vitals
  const assessmentsData = assessments
  const notesData = notes
  const ordersData = orders
  const marData = mar
  const bloodData = bloodRequests
  const billingData = billing

  // =====================================================
  // REPORTS
  // =====================================================

  const reports = useMemo(() => {
    if (!selectedHospital) {
      return {
        patients: 0,
        vitals: 0,
        assessments: 0,
        orders: 0,
        mar: 0,
        blood: 0,
        billing: 0,
      }
    }

    return {
      patients: patientsData.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      vitals: vitalsData.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      assessments: assessmentsData.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      orders: ordersData.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      mar: marData.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      blood: bloodData.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      billing: billingData.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,
    }
  }, [
    selectedHospital,
    patientsData,
    vitalsData,
    assessmentsData,
    ordersData,
    marData,
    bloodData,
    billingData,
  ]);

  // =====================================================
  // SELECTED HOSPITAL DATA
  // =====================================================

  const hospitalNurses = useMemo(() => {
    if (!selectedHospital) return []

    return nurses.filter(
      (nurse) =>
        nurse.hospitalId ===
        selectedHospital.id
    )
  }, [nurses, selectedHospital])

  const hospitalPatients = useMemo(() => {
    if (!selectedHospital) return []

    return patients.filter(
      (patient) =>
        patient.hospitalId ===
        selectedHospital.id
    )
  }, [patients, selectedHospital])

  const hospitalVitals = useMemo(() => {
    if (!selectedHospital) return []

    return vitals.filter(
      (item) =>
        item.hospitalId ===
        selectedHospital.id
    )
  }, [vitals, selectedHospital])

  const hospitalAssessments = useMemo(() => {
    if (!selectedHospital) return []

    return assessments.filter(
      (item) =>
        item.hospitalId ===
        selectedHospital.id
    )
  }, [assessments, selectedHospital])

  const hospitalNotes = useMemo(() => {
    if (!selectedHospital) return []

    return notes.filter(
      (item) =>
        item.hospitalId ===
        selectedHospital.id
    )
  }, [notes, selectedHospital])

  const hospitalOrders = useMemo(() => {
    if (!selectedHospital) return []

    return orders.filter(
      (item) =>
        item.hospitalId ===
        selectedHospital.id
    )
  }, [orders, selectedHospital])

  const hospitalMAR = useMemo(() => {
    if (!selectedHospital) return []

    return mar.filter(
      (item) =>
        item.hospitalId ===
        selectedHospital.id
    )
  }, [mar, selectedHospital])

  const hospitalBlood = useMemo(() => {
    if (!selectedHospital) return []

    return bloodRequests.filter(
      (item) =>
        item.hospitalId ===
        selectedHospital.id
    )
  }, [bloodRequests, selectedHospital])

  const hospitalBilling = useMemo(() => {
    if (!selectedHospital) return []

    return billing.filter(
      (item) =>
        item.hospitalId ===
        selectedHospital.id
    )
  }, [billing, selectedHospital])

  // =====================================================
  // SEARCH
  // =====================================================

  const [patientSearch, setPatientSearch] =
    useState("")

  const filteredPatients =
    hospitalPatients.filter((patient) =>
      patient.name
        .toLowerCase()
        .includes(
          patientSearch.toLowerCase()
        )
    )

  // =====================================================
  // TABS
  // =====================================================

  const [activeTab, setActiveTab] =
    useState("home")

  // =====================================================
  // PROFILE EDIT
  // =====================================================

  const [profile, setProfile] =
    useState(currentUser)

  const [editingProfile, setEditingProfile] =
    useState(false)

  const handleProfileChange = (e) => {
    setProfile((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }))
  }

  // Staff profiles are maintained by the hospital administrator; nothing here
  // is sent to the server, so do not claim it was saved.
  const saveProfile = () => {
    setEditingProfile(false)
    toast.error("Profile changes are not saved here. Ask your hospital administrator to update your staff record.")
  }

  // =====================================================
  // ADD NURSE
  // ADMIN ONLY
  // =====================================================

  const [showAddNurse, setShowAddNurse] =
    useState(false)

  const [newNurse, setNewNurse] =
    useState({
      name: "",
      department: "General Medicine",
      shift: "Morning",
      phone: "",
      email: "",
      qualification: "GNM",
      joiningDate: "",
      status: "On Duty",
    })

  const handleAddNurse = async (e) => {
    e.preventDefault()

    if (!isAdmin) {
      toast.warning(
        "Only Admin can add a nurse."
      )
      return
    }

    if (!selectedHospital) {
      toast.warning(
        "Please select a hospital first."
      )
      return
    }

    setSaving(true)
    try {
      await api.nurses.create({
        hospital: selectedHospital.id,
        name: newNurse.name,
        department: newNurse.department,
        shift: newNurse.shift,
        phone: newNurse.phone,
        email: newNurse.email,
        qualification: newNurse.qualification,
        joining_date: newNurse.joiningDate || null,
        status: newNurse.status,
      })
      setNewNurse({
        name: "",
        department: "General Medicine",
        shift: "Morning",
        phone: "",
        email: "",
        qualification: "GNM",
        joiningDate: "",
        status: "On Duty",
      })
      setShowAddNurse(false)
      await loadData()
    } catch (err) {
      toast.error(`Could not add nurse: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  // =====================================================
  // REMOVE NURSE
  // ADMIN ONLY
  // =====================================================

  const removeNurse = async (nurse) => {
    if (!isAdmin) {
      toast.warning(
        "Only Admin can remove a nurse."
      )
      return
    }

    if (
      !selectedHospital ||
      nurse.hospitalId !==
      selectedHospital.id
    ) {
      toast.warning(
        "You can only remove nurses from the selected hospital."
      )
      return
    }

    const confirmRemove =
      (await confirm(
        `Remove ${nurse.name}?`
      ))

    if (!confirmRemove) return

    try {
      await api.nurses.delete(nurse.id)
      await loadData()
    } catch (err) {
      toast.error(`Could not remove nurse: ${err.message}`)
    }
  }

  // =====================================================
  // ADD VITAL
  // =====================================================

  const [showVitalsForm, setShowVitalsForm] =
    useState(false)

  const [vitalForm, setVitalForm] =
    useState({
      patientId: "",
      temperature: "",
      bp: "",
      pulse: "",
      spo2: "",
      respiratoryRate: "",
    })

  const saveVitals = async (e) => {
    e.preventDefault()

    if (!selectedHospital) return

    const patient =
      hospitalPatients.find(
        (item) => String(item.id) === String(vitalForm.patientId)
      )

    if (!patient) {
      toast.warning("Select a patient.")
      return
    }

    setSaving(true)
    try {
      await api.nurses.assessments.create({
        hospital: selectedHospital.id,
        patient: patient.id,
        admission: patient.admissionId,
        assessment_type: "Focused",
        vitals: {
          temperature: vitalForm.temperature,
          bp: vitalForm.bp,
          pulse: vitalForm.pulse,
          spo2: vitalForm.spo2,
          respiratory_rate: vitalForm.respiratoryRate,
        },
      })
    } catch (err) {
      toast.error(`Vitals were not saved: ${err.message}`)
      setSaving(false)
      return
    }
    setSaving(false)
    await loadData()

    setVitalForm({
      patientId: "",
      temperature: "",
      bp: "",
      pulse: "",
      spo2: "",
      respiratoryRate: "",
    })

    setShowVitalsForm(false)
  }

  // =====================================================
  // ADD NOTE
  // =====================================================

  const [showNoteForm, setShowNoteForm] =
    useState(false)

  const [noteForm, setNoteForm] =
    useState({
      patientId: "",
      text: "",
    })

  const saveNote = async (e) => {
    e.preventDefault()

    if (!selectedHospital) return

    if (
      !noteForm.patientId ||
      !noteForm.text.trim()
    ) {
      toast.warning(
        "Please select patient and enter note."
      )
      return
    }

    const notePatient = hospitalPatients.find((item) => String(item.id) === String(noteForm.patientId))
    setSaving(true)
    try {
      await api.nurses.notes.create({
        hospital: selectedHospital.id,
        patient: noteForm.patientId,
        admission: notePatient?.admissionId,
        note_type: "Progress",
        note: noteForm.text.trim(),
      })
    } catch (err) {
      toast.error(`Note was not saved: ${err.message}`)
      setSaving(false)
      return
    }
    setSaving(false)
    await loadData()

    setNoteForm({
      patientId: "",
      text: "",
    })

    setShowNoteForm(false)
  }

  // =====================================================
  // ADD ASSESSMENT
  // =====================================================

  const [showAssessmentForm, setShowAssessmentForm] =
    useState(false)

  const [assessmentForm, setAssessmentForm] =
    useState({
      patientId: "",
      assessment: "",
    })

  const saveAssessment = async (e) => {
    e.preventDefault()

    if (!selectedHospital) return

    if (
      !assessmentForm.patientId ||
      !assessmentForm.assessment.trim()
    ) {
      toast.warning(
        "Please select patient and enter assessment."
      )
      return
    }

    const assessedPatient = hospitalPatients.find((item) => String(item.id) === String(assessmentForm.patientId))
    setSaving(true)
    try {
      await api.nurses.assessments.create({
        hospital: selectedHospital.id,
        patient: assessmentForm.patientId,
        admission: assessedPatient?.admissionId,
        assessment_type: "Shift",
        plan_of_care: assessmentForm.assessment.trim(),
      })
    } catch (err) {
      toast.error(`Assessment was not saved: ${err.message}`)
      setSaving(false)
      return
    }
    setSaving(false)
    await loadData()

    setAssessmentForm({
      patientId: "",
      assessment: "",
    })

    setShowAssessmentForm(false)
  }

  // =====================================================
  // MAR - GIVE MEDICINE
  // =====================================================

  const administerMedicine = async (item) => {
    if (!selectedHospital) return

    if (
      item.hospitalId !==
      selectedHospital.id
    ) {
      toast.info(
        "Invalid hospital access."
      )
      return
    }

    if (!(await confirm(`Record ${item.medicine} ${item.dose} as given to ${item.patientName || "this patient"} now?`))) return

    try {
      await api.nurses.marAdministrations.administer(item.id, {})
      await loadData()
    } catch (err) {
      toast.error(`Dose was not recorded: ${err.message}`)
    }
  }

  // =====================================================
  // BLOOD REQUEST
  // =====================================================

  // Blood requests are raised and tracked on the Blood Bank page; this list
  // shows their live status.
  const requestBlood = () => {
    window.location.assign("/blood-bank")
  }

  // =====================================================
  // DISCHARGE
  // =====================================================

  const dischargePatient = async (patient) => {
    if (!selectedHospital) return

    const confirmed =
      (await confirm(
        `Start discharge process for ${patient.name}?`
      ))

    if (!confirmed) return

    try {
      await api.ipd.admissions.initiateDischarge(patient.admissionId)
      await loadData()
      toast.success(
        "Discharge initiated. A doctor must finalize the discharge summary before discharge can be completed."
      )
    } catch (err) {
      toast.error(`Discharge was not started: ${err.message}`)
    }
  }

  // =====================================================
  // TAB BUTTON
  // =====================================================

  const tabs = [
    {
      id: "home",
      label: "Home",
      icon: HouseIcon,
    },
    {
      id: "profile",
      label: "My Profile",
      icon: UserIcon,
    },
    {
      id: "patients",
      label: "Patients",
      icon: UsersIcon,
    },
    {
      id: "assessment",
      label: "Assessment",
      icon: StethoscopeIcon,
    },
    {
      id: "vitals",
      label: "Vitals",
      icon: HeartPulseIcon,
    },
    {
      id: "notes",
      label: "Notes",
      icon: NotebookPenIcon,
    },
    {
      id: "orders",
      label: "Orders",
      icon: ClipboardListIcon,
    },
    {
      id: "mar",
      label: "MAR",
      icon: PillIcon,
    },
    {
      id: "blood",
      label: "Blood",
      icon: DropletIcon,
    },
    {
      id: "discharge",
      label: "Discharge",
      icon: HospitalIcon,
    },
    {
      id: "billing",
      label: "Billing",
      icon: WalletIcon,
    },
    {
      id: "reports",
      label: "Reports",
      icon: ChartColumnIcon,
    },
  ]

  // =====================================================
  // NO HOSPITAL
  // =====================================================

  if (!selectedHospital) {
    return (
      <>{confirmDialog}<div className="space-y-5">
        <UiPageHeader title="Nursing" breadcrumbs={[{ label: "Home", to: "/" }, { label: "Nursing" }]} />
        <Card><EmptyState icon={HospitalIcon} title="Select a hospital" description="Choose a hospital in the header to open the nursing workspace." /></Card>
      </div></>
    )
  }

  // =====================================================
  // MAIN
  // =====================================================

  return (
    <>{confirmDialog}<div className="space-y-5">
      <UiPageHeader
        title="Nursing"
        description={`Ward work for ${selectedHospital.name} · signed in as ${profile.name}`}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Nursing" }]}
        actions={isAdmin && <Button icon={UserPlusIcon} onClick={() => setShowAddNurse(true)}>Add nurse</Button>}
      />

      {error && (
        <Alert tone="warning" title="Some ward data did not load" action={<Button size="sm" variant="secondary" onClick={loadData}>Retry</Button>}>
          {error}
        </Alert>
      )}
      {loading && <p className="text-sm text-ink-500" role="status">Loading ward data…</p>}

      <Tabs tabs={tabs} value={activeTab} onChange={setActiveTab} label="Nursing sections" />

      {/* =================================================
          HOME
      ================================================= */}

      {activeTab === "home" && (

        <div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">

            <DashboardCard
              title="Patients"
              value={
                hospitalPatients.length
              }
              icon={<UsersIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
              subtitle="Hospital patients"
            />

            <DashboardCard
              title="Vitals Recorded"
              value={
                hospitalVitals.length
              }
              icon={<HeartPulseIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
              subtitle="All recorded"
            />

            <DashboardCard
              title="Pending Orders"
              value={
                hospitalOrders.filter(
                  (item) =>
                    item.status ===
                    "Pending"
                ).length
              }
              icon={<ClipboardListIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
              subtitle="Orders waiting"
            />

            <DashboardCard
              title="Pending MAR"
              value={
                hospitalMAR.filter(
                  (item) =>
                    item.status === "Due" || item.status === "Delayed"
                ).length
              }
              icon={<PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
              subtitle="Medicine doses"
            />

          </div>


          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Patients */}
            <SectionCard
              title="Recent Patients"
              subtitle={selectedHospital.name}
            >

              {hospitalPatients
                .slice(0, 5)
                .map((patient) => (

                  <div
                    key={patient.id}
                    className="flex items-center justify-between py-4 border-b last:border-b-0"
                  >

                    <div>

                      <p className="font-medium text-gray-800">
                        {patient.name}
                      </p>

                      <p className="text-sm text-gray-500">
                        {patient.id} ·{" "}
                        {patient.department}
                      </p>

                    </div>

                    <span className="text-xs px-3 py-1 rounded-full bg-green-100 text-green-700">
                      {patient.status}
                    </span>

                  </div>

                ))}

            </SectionCard>


            {/* MAR */}
            <SectionCard
              title="Medicine Administration"
              subtitle="Pending medication"
            >

              {hospitalMAR
                .filter(
                  (item) =>
                    item.status === "Due" || item.status === "Delayed"
                )
                .map((item) => {

                  const patient =
                    hospitalPatients.find(
                      (p) =>
                        p.id ===
                        item.patientId
                    )

                  return (
                    <div
                      key={item.id}
                      className="flex items-center justify-between py-4 border-b last:border-b-0"
                    >

                      <div>

                        <p className="font-medium text-gray-800">
                          {item.medicine}
                        </p>

                        <p className="text-sm text-gray-500">
                          {patient?.name} ·{" "}
                          {item.dose}
                        </p>

                      </div>

                      <button
                        onClick={() =>
                          administerMedicine(
                            item
                          )
                        }
                        className="px-3 py-2 rounded-lg bg-green-100 text-green-700 text-sm font-medium hover:bg-green-200"
                      >
                        Give
                      </button>

                    </div>
                  )
                })}

            </SectionCard>

          </div>

        </div>

      )}


      {/* =================================================
          PROFILE
      ================================================= */}

      {activeTab === "profile" && (

        <SectionCard
          title="My Profile"
          subtitle={`Nurse profile — ${selectedHospital.name}`}
        >

          <div className="flex flex-col md:flex-row gap-6">

            <div className="w-24 h-24 rounded-full bg-blue-100 flex items-center justify-center text-5xl">
              <UserRoundIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />
            </div>

            <div className="flex-1">

              {editingProfile ? (

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

                  <Input
                    label="Name"
                    name="name"
                    value={profile.name}
                    onChange={
                      handleProfileChange
                    }
                  />

                  <Input
                    label="Phone"
                    name="phone"
                    value={profile.phone}
                    onChange={
                      handleProfileChange
                    }
                  />

                  <Input
                    label="Email"
                    name="email"
                    value={profile.email}
                    onChange={
                      handleProfileChange
                    }
                  />

                  <Input
                    label="Department"
                    name="department"
                    value={profile.department}
                    onChange={
                      handleProfileChange
                    }
                  />

                  <Input
                    label="Qualification"
                    name="qualification"
                    value={
                      profile.qualification
                    }
                    onChange={
                      handleProfileChange
                    }
                  />

                  <Input
                    label="Shift"
                    name="shift"
                    value={profile.shift}
                    onChange={
                      handleProfileChange
                    }
                  />

                </div>

              ) : (

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

                  <Info
                    label="Name"
                    value={profile.name}
                  />

                  <Info
                    label="Role"
                    value={profile.role}
                  />

                  <Info
                    label="Department"
                    value={profile.department}
                  />

                  <Info
                    label="Shift"
                    value={profile.shift}
                  />

                  <Info
                    label="Phone"
                    value={profile.phone}
                  />

                  <Info
                    label="Email"
                    value={profile.email}
                  />

                  <Info
                    label="Qualification"
                    value={
                      profile.qualification
                    }
                  />

                  <Info
                    label="Joining Date"
                    value={
                      profile.joiningDate
                    }
                  />

                </div>

              )}

              <div className="mt-6">

                {editingProfile ? (

                  <div className="flex gap-3">

                    <button
                      onClick={saveProfile}
                      className="px-5 py-2.5 rounded-xl bg-blue-600 text-white font-medium"
                    >
                      Save Profile
                    </button>

                    <button
                      onClick={() =>
                        setEditingProfile(false)
                      }
                      className="px-5 py-2.5 rounded-xl bg-gray-100 text-gray-700"
                    >
                      Cancel
                    </button>

                  </div>

                ) : (

                  <button
                    onClick={() =>
                      setEditingProfile(true)
                    }
                    className="px-5 py-2.5 rounded-xl bg-blue-600 text-white font-medium"
                  >
                    Edit Profile
                  </button>

                )}

              </div>

            </div>

          </div>

        </SectionCard>

      )}


      {/* =================================================
          PATIENTS
      ================================================= */}

      {activeTab === "patients" && (

        <SectionCard
          title="Patient List"
          subtitle={`Patients — ${selectedHospital.name}`}
        >

          <div className="mb-5">

            <input
              type="text"
              value={patientSearch}
              onChange={(e) =>
                setPatientSearch(
                  e.target.value
                )
              }
              placeholder="Search patient..."
              className="hms-input w-full"
            />

          </div>

          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="bg-gray-50">

                <tr>

                  <th className="text-left px-5 py-4">
                    Patient
                  </th>

                  <th className="text-left px-5 py-4">
                    Department
                  </th>

                  <th className="text-left px-5 py-4">
                    Doctor
                  </th>

                  <th className="text-left px-5 py-4">
                    Ward / Bed
                  </th>

                  <th className="text-left px-5 py-4">
                    Status
                  </th>

                  <th className="text-right px-5 py-4">
                    Action
                  </th>

                </tr>

              </thead>

              <tbody className="divide-y">

                {filteredPatients.map(
                  (patient) => (

                    <tr
                      key={patient.id}
                      className="hover:bg-gray-50"
                    >

                      <td className="px-5 py-4">

                        <p className="font-medium text-gray-800">
                          {patient.name}
                        </p>

                        <p className="text-xs text-gray-500">
                          {patient.id} ·{" "}
                          {patient.age} years
                        </p>

                      </td>

                      <td className="px-5 py-4 text-sm text-gray-600">
                        {patient.department}
                      </td>

                      <td className="px-5 py-4 text-sm text-gray-600">
                        {patient.doctor}
                      </td>

                      <td className="px-5 py-4 text-sm text-gray-600">
                        {patient.ward} /{" "}
                        {patient.bed}
                      </td>

                      <td className="px-5 py-4">

                        <span className="px-3 py-1 rounded-full text-xs bg-green-100 text-green-700">
                          {patient.status}
                        </span>

                      </td>

                      <td className="px-5 py-4 text-right">

                        <button
                          onClick={() =>
                            setActiveTab(
                              "assessment"
                            )
                          }
                          className="text-blue-600 font-medium text-sm"
                        >
                          Assess
                        </button>

                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        </SectionCard>

      )}


      {/* =================================================
          ASSESSMENT
      ================================================= */}

      {activeTab === "assessment" && (

        <SectionCard
          title="Patient Assessment"
          subtitle="Nursing assessments"
          action={
            isNurse && (
              <button
                onClick={() =>
                  setShowAssessmentForm(
                    true
                  )
                }
                className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm"
              >
                + New Assessment
              </button>
            )
          }
        >

          <div className="space-y-4">

            {hospitalAssessments.map(
              (item) => {

                const patient =
                  hospitalPatients.find(
                    (p) =>
                      p.id ===
                      item.patientId
                  )

                return (
                  <div
                    key={item.id}
                    className="border rounded-xl p-4"
                  >

                    <div className="flex justify-between gap-4">

                      <div>

                        <p className="font-semibold text-gray-800">
                          {patient?.name}
                        </p>

                        <p className="text-sm text-gray-500">
                          {item.date} ·{" "}
                          {item.nurse}
                        </p>

                      </div>

                    </div>

                    <p className="mt-3 text-gray-700">
                      {item.assessment}
                    </p>

                  </div>
                )
              }
            )}

          </div>

        </SectionCard>

      )}


      {/* =================================================
          VITALS
      ================================================= */}

      {activeTab === "vitals" && (

        <SectionCard
          title="Patient Vitals"
          subtitle="Record and monitor vital signs"
          action={
            <button
              onClick={() =>
                setShowVitalsForm(true)
              }
              className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm"
            >
              + Record Vitals
            </button>
          }
        >

          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="bg-gray-50">

                <tr>

                  <th className="text-left px-5 py-4">
                    Patient
                  </th>

                  <th className="text-left px-5 py-4">
                    Temperature
                  </th>

                  <th className="text-left px-5 py-4">
                    BP
                  </th>

                  <th className="text-left px-5 py-4">
                    Pulse
                  </th>

                  <th className="text-left px-5 py-4">
                    SpO₂
                  </th>

                  <th className="text-left px-5 py-4">
                    Resp.
                  </th>

                  <th className="text-left px-5 py-4">
                    Time
                  </th>

                </tr>

              </thead>

              <tbody className="divide-y">

                {hospitalVitals.map(
                  (item) => {

                    const patient =
                      hospitalPatients.find(
                        (p) =>
                          p.id ===
                          item.patientId
                      )

                    return (
                      <tr
                        key={item.id}
                      >

                        <td className="px-5 py-4 font-medium">
                          {patient?.name}
                        </td>

                        <td className="px-5 py-4">
                          {item.temperature} °F
                        </td>

                        <td className="px-5 py-4">
                          {item.bp}
                        </td>

                        <td className="px-5 py-4">
                          {item.pulse}
                        </td>

                        <td className="px-5 py-4">
                          {item.spo2}%
                        </td>

                        <td className="px-5 py-4">
                          {item.respiratoryRate}
                        </td>

                        <td className="px-5 py-4 text-sm text-gray-500">
                          {item.time}
                        </td>

                      </tr>
                    )
                  }
                )}

              </tbody>

            </table>

          </div>

        </SectionCard>

      )}


      {/* =================================================
          NOTES
      ================================================= */}

      {activeTab === "notes" && (

        <SectionCard
          title="Nursing Notes"
          subtitle="Patient care notes"
          action={
            <button
              onClick={() =>
                setShowNoteForm(true)
              }
              className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm"
            >
              + Add Note
            </button>
          }
        >

          <div className="space-y-4">

            {hospitalNotes.map(
              (note) => {

                const patient =
                  hospitalPatients.find(
                    (p) =>
                      p.id ===
                      note.patientId
                  )

                return (
                  <div
                    key={note.id}
                    className="border rounded-xl p-4"
                  >

                    <div className="flex justify-between">

                      <p className="font-semibold text-gray-800">
                        {patient?.name}
                      </p>

                      <span className="text-xs text-gray-500">
                        {note.date}
                      </span>

                    </div>

                    <p className="text-gray-700 mt-2">
                      {note.text}
                    </p>

                    <p className="text-xs text-gray-500 mt-2">
                      By {note.createdBy}
                    </p>

                  </div>
                )
              }
            )}

          </div>

        </SectionCard>

      )}


      {/* =================================================
          ORDERS
      ================================================= */}

      {activeTab === "orders" && (

        <SectionCard
          title="Orders"
          subtitle="Doctor and hospital orders"
        >

          <div className="space-y-4">

            {hospitalOrders.map(
              (order) => {

                const patient =
                  hospitalPatients.find(
                    (p) =>
                      p.id ===
                      order.patientId
                  )

                return (
                  <div
                    key={order.id}
                    className="flex items-center justify-between border rounded-xl p-4"
                  >

                    <div>

                      <p className="font-medium text-gray-800">
                        {order.order}
                      </p>

                      <p className="text-sm text-gray-500">
                        {patient?.name} ·{" "}
                        {order.doctor}
                      </p>

                    </div>

                    <span
                      className={`px-3 py-1 rounded-full text-xs ${order.status ===
                          "Completed"
                          ? "bg-green-100 text-green-700"
                          : "bg-yellow-100 text-yellow-700"
                        }`}
                    >
                      {order.status}
                    </span>

                  </div>
                )
              }
            )}

          </div>

        </SectionCard>

      )}


      {/* =================================================
          MAR
      ================================================= */}

      {activeTab === "mar" && (

        <SectionCard
          title="MAR — Medicine Administration Record"
          subtitle="Administer medicines according to authorized orders"
        >

          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="bg-gray-50">

                <tr>

                  <th className="text-left px-5 py-4">
                    Patient
                  </th>

                  <th className="text-left px-5 py-4">
                    Medicine
                  </th>

                  <th className="text-left px-5 py-4">
                    Dose
                  </th>

                  <th className="text-left px-5 py-4">
                    Route
                  </th>

                  <th className="text-left px-5 py-4">
                    Frequency
                  </th>

                  <th className="text-left px-5 py-4">
                    Status
                  </th>

                  <th className="text-right px-5 py-4">
                    Action
                  </th>

                </tr>

              </thead>

              <tbody className="divide-y">

                {hospitalMAR.map(
                  (item) => {

                    const patient =
                      hospitalPatients.find(
                        (p) =>
                          p.id ===
                          item.patientId
                      )

                    return (
                      <tr
                        key={item.id}
                      >

                        <td className="px-5 py-4 font-medium">
                          {patient?.name}
                        </td>

                        <td className="px-5 py-4">
                          {item.medicine}
                        </td>

                        <td className="px-5 py-4">
                          {item.dose}
                        </td>

                        <td className="px-5 py-4">
                          {item.route}
                        </td>

                        <td className="px-5 py-4">
                          {item.frequency}
                        </td>

                        <td className="px-5 py-4">

                          <span
                            className={`px-3 py-1 rounded-full text-xs ${item.status === "Administered"
                                ? "bg-green-100 text-green-700"
                                : item.status === "Delayed"
                                  ? "bg-red-100 text-red-700"
                                  : "bg-yellow-100 text-yellow-700"
                              }`}
                          >
                            {item.status}
                          </span>

                        </td>

                        <td className="px-5 py-4 text-right">

                          {item.status === "Due" || item.status === "Delayed" ? (

                            <button
                              onClick={() =>
                                administerMedicine(
                                  item
                                )
                              }
                              className="px-3 py-2 rounded-lg bg-green-600 text-white text-sm"
                            >
                              Give Medicine
                            </button>

                          ) : (

                            <span className="text-sm text-gray-400">
                              Completed
                            </span>

                          )}

                        </td>

                      </tr>
                    )
                  }
                )}

              </tbody>

            </table>

          </div>

        </SectionCard>

      )}


      {/* =================================================
          BLOOD
      ================================================= */}

      {activeTab === "blood" && (

        <SectionCard
          title="Blood Management"
          subtitle="Blood requests for selected hospital"
        >

          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="bg-gray-50">

                <tr>

                  <th className="text-left px-5 py-4">
                    Patient
                  </th>

                  <th className="text-left px-5 py-4">
                    Blood Group
                  </th>

                  <th className="text-left px-5 py-4">
                    Units
                  </th>

                  <th className="text-left px-5 py-4">
                    Urgency
                  </th>

                  <th className="text-left px-5 py-4">
                    Status
                  </th>

                  <th className="text-right px-5 py-4">
                    Action
                  </th>

                </tr>

              </thead>

              <tbody className="divide-y">

                {hospitalBlood.map(
                  (item) => {

                    const patient =
                      hospitalPatients.find(
                        (p) =>
                          p.id ===
                          item.patientId
                      )

                    return (
                      <tr
                        key={item.id}
                      >

                        <td className="px-5 py-4 font-medium">
                          {patient?.name}
                        </td>

                        <td className="px-5 py-4">
                          {item.bloodGroup}
                        </td>

                        <td className="px-5 py-4">
                          {item.units}
                        </td>

                        <td className="px-5 py-4">

                          <span
                            className={`px-3 py-1 rounded-full text-xs ${item.urgency ===
                                "Urgent"
                                ? "bg-red-100 text-red-700"
                                : "bg-gray-100 text-gray-600"
                              }`}
                          >
                            {item.urgency}
                          </span>

                        </td>

                        <td className="px-5 py-4">
                          {item.status}
                        </td>

                        <td className="px-5 py-4 text-right">

                          {item.status !==
                            "Requested" && (

                              <button
                                onClick={() =>
                                  requestBlood(
                                    item
                                  )
                                }
                                className="text-blue-600 text-sm font-medium"
                              >
                                Request
                              </button>

                            )}

                        </td>

                      </tr>
                    )
                  }
                )}

              </tbody>

            </table>

          </div>

        </SectionCard>

      )}


      {/* =================================================
          DISCHARGE
      ================================================= */}

      {activeTab === "discharge" && (

        <SectionCard
          title="Discharge"
          subtitle="Discharge requests for admitted patients"
        >

          <div className="space-y-4">

            {hospitalPatients.map(
              (patient) => (

                <div
                  key={patient.id}
                  className="border rounded-xl p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4"
                >

                  <div>

                    <p className="font-medium text-gray-800">
                      {patient.name}
                    </p>

                    <p className="text-sm text-gray-500">
                      {patient.id} ·{" "}
                      {patient.ward} ·{" "}
                      {patient.bed}
                    </p>

                  </div>

                  <button
                    onClick={() =>
                      dischargePatient(
                        patient
                      )
                    }
                    className="px-4 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium"
                  >
                    Start Discharge
                  </button>

                </div>

              )
            )}

          </div>

          {discharges.length > 0 && (

            <div className="mt-6 pt-6 border-t">

              <h3 className="font-semibold text-gray-800 mb-3">
                Discharge Requests
              </h3>

              <div className="space-y-3">

                {discharges
                  .filter(
                    (item) =>
                      item.hospitalId ===
                      selectedHospital.id
                  )
                  .map((item) => (

                    <div
                      key={item.id}
                      className="p-4 bg-orange-50 rounded-xl"
                    >

                      <p className="font-medium">
                        {item.patientName}
                      </p>

                      <p className="text-sm text-gray-500">
                        {item.status} ·{" "}
                        {item.date}
                      </p>

                    </div>

                  ))}

              </div>

            </div>

          )}

        </SectionCard>

      )}


      {/* =================================================
          BILLING
      ================================================= */}

      {activeTab === "billing" && (

        <SectionCard
          title="Billing"
          subtitle={`Billing information — ${selectedHospital.name}`}
        >

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

            {hospitalBilling.map(
              (bill) => {

                const patient =
                  hospitalPatients.find(
                    (p) =>
                      p.id ===
                      bill.patientId
                  )

                return (
                  <div
                    key={bill.id}
                    className="border rounded-xl p-5"
                  >

                    <div className="flex justify-between">

                      <div>

                        <p className="font-semibold text-gray-800">
                          {patient?.name}
                        </p>

                        <p className="text-sm text-gray-500">
                          {bill.id}
                        </p>

                      </div>

                      <span
                        className={`px-3 py-1 rounded-full text-xs h-fit ${bill.status ===
                            "Paid"
                            ? "bg-green-100 text-green-700"
                            : "bg-yellow-100 text-yellow-700"
                          }`}
                      >
                        {bill.status}
                      </span>

                    </div>

                    <p className="text-2xl font-bold text-gray-800 mt-5">
                      ₹
                      {bill.amount.toLocaleString(
                        "en-IN"
                      )}
                    </p>

                  </div>
                )
              }
            )}

          </div>

        </SectionCard>

      )}


      {/* =================================================
          REPORTS
      ================================================= */}

      {activeTab === "reports" && (

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">

          <ReportCard
            title="Patients"
            value={reports.patients}
            icon={<UsersIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Vitals"
            value={reports.vitals}
            icon={<HeartPulseIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Assessments"
            value={reports.assessments}
            icon={<StethoscopeIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Orders"
            value={reports.orders}
            icon={<ClipboardListIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="MAR Records"
            value={reports.mar}
            icon={<PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Blood Records"
            value={reports.blood}
            icon={<DropletIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Billing Records"
            value={reports.billing}
            icon={<WalletIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

        </div>

      )}


      {/* =================================================
          ADD NURSE MODAL
      ================================================= */}

      {showAddNurse && isAdmin && (

        <Modal
          title="Add Nurse"
          subtitle={`Add nurse to ${selectedHospital.name}`}
          onClose={() =>
            setShowAddNurse(false)
          }
        >

          <form
            onSubmit={handleAddNurse}
            className="space-y-4"
          >

            <Input
              label="Nurse Name"
              value={newNurse.name}
              onChange={(e) =>
                setNewNurse({
                  ...newNurse,
                  name: e.target.value,
                })
              }
              required
            />

            <Input
              label="Phone"
              value={newNurse.phone}
              onChange={(e) =>
                setNewNurse({
                  ...newNurse,
                  phone: e.target.value,
                })
              }
              required
            />

            <Input
              label="Email"
              value={newNurse.email}
              onChange={(e) =>
                setNewNurse({
                  ...newNurse,
                  email: e.target.value,
                })
              }
            />

            <Select
              label="Department"
              value={newNurse.department}
              onChange={(e) =>
                setNewNurse({
                  ...newNurse,
                  department:
                    e.target.value,
                })
              }
              options={[
                "General Medicine",
                "Emergency",
                "ICU",
                "Cardiology",
                "Orthopedics",
                "Pediatrics",
                "Laboratory",
              ]}
            />

            <Select
              label="Shift"
              value={newNurse.shift}
              onChange={(e) =>
                setNewNurse({
                  ...newNurse,
                  shift: e.target.value,
                })
              }
              options={[
                "Morning",
                "Evening",
                "Night",
              ]}
            />

            <Select
              label="Qualification"
              value={
                newNurse.qualification
              }
              onChange={(e) =>
                setNewNurse({
                  ...newNurse,
                  qualification:
                    e.target.value,
                })
              }
              options={[
                "GNM",
                "B.Sc Nursing",
                "M.Sc Nursing",
              ]}
            />

            <Input
              label="Joining Date"
              type="date"
              value={
                newNurse.joiningDate
              }
              onChange={(e) =>
                setNewNurse({
                  ...newNurse,
                  joiningDate:
                    e.target.value,
                })
              }
            />

            <Select
              label="Status"
              value={newNurse.status}
              onChange={(e) =>
                setNewNurse({
                  ...newNurse,
                  status:
                    e.target.value,
                })
              }
              options={[
                "On Duty",
                "Off Duty",
              ]}
            />

            <div className="flex justify-end gap-3 pt-3">

              <button
                type="button"
                onClick={() =>
                  setShowAddNurse(false)
                }
                className="px-5 py-2.5 rounded-xl bg-gray-100 text-gray-700"
              >
                Cancel
              </button>

              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-blue-600 text-white font-medium"
              >
                Add Nurse
              </button>

            </div>

          </form>

        </Modal>

      )}


      {/* =================================================
          VITALS MODAL
      ================================================= */}

      {showVitalsForm && (

        <Modal
          title="Record Patient Vitals"
          subtitle={selectedHospital.name}
          onClose={() =>
            setShowVitalsForm(false)
          }
        >

          <form
            onSubmit={saveVitals}
            className="space-y-4"
          >

            <Select
              label="Patient"
              value={
                vitalForm.patientId
              }
              onChange={(e) =>
                setVitalForm({
                  ...vitalForm,
                  patientId:
                    e.target.value,
                })
              }
              options={hospitalPatients.map(
                (p) => p.id
              )}
              optionLabels={hospitalPatients.map(
                (p) =>
                  `${p.name} (${p.id})`
              )}
            />

            <Input
              label="Temperature °F"
              value={
                vitalForm.temperature
              }
              onChange={(e) =>
                setVitalForm({
                  ...vitalForm,
                  temperature:
                    e.target.value,
                })
              }
            />

            <Input
              label="Blood Pressure"
              placeholder="120/80"
              value={vitalForm.bp}
              onChange={(e) =>
                setVitalForm({
                  ...vitalForm,
                  bp: e.target.value,
                })
              }
            />

            <Input
              label="Pulse"
              value={
                vitalForm.pulse
              }
              onChange={(e) =>
                setVitalForm({
                  ...vitalForm,
                  pulse: e.target.value,
                })
              }
            />

            <Input
              label="SpO₂"
              value={
                vitalForm.spo2
              }
              onChange={(e) =>
                setVitalForm({
                  ...vitalForm,
                  spo2: e.target.value,
                })
              }
            />

            <Input
              label="Respiratory Rate"
              value={
                vitalForm.respiratoryRate
              }
              onChange={(e) =>
                setVitalForm({
                  ...vitalForm,
                  respiratoryRate:
                    e.target.value,
                })
              }
            />

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium"
            >
              Save Vitals
            </button>

          </form>

        </Modal>

      )}


      {/* =================================================
          NOTE MODAL
      ================================================= */}

      {showNoteForm && (

        <Modal
          title="Add Nursing Note"
          subtitle={selectedHospital.name}
          onClose={() =>
            setShowNoteForm(false)
          }
        >

          <form
            onSubmit={saveNote}
            className="space-y-4"
          >

            <Select
              label="Patient"
              value={
                noteForm.patientId
              }
              onChange={(e) =>
                setNoteForm({
                  ...noteForm,
                  patientId:
                    e.target.value,
                })
              }
              options={hospitalPatients.map(
                (p) => p.id
              )}
              optionLabels={hospitalPatients.map(
                (p) =>
                  `${p.name} (${p.id})`
              )}
            />

            <div>

              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nursing Note
              </label>

              <textarea
                rows="5"
                value={noteForm.text}
                onChange={(e) =>
                  setNoteForm({
                    ...noteForm,
                    text: e.target.value,
                  })
                }
                placeholder="Enter nursing note..."
                className="hms-input w-full"
              />

            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium"
            >
              Save Note
            </button>

          </form>

        </Modal>

      )}


      {/* =================================================
          ASSESSMENT MODAL
      ================================================= */}

      {showAssessmentForm && (

        <Modal
          title="New Patient Assessment"
          subtitle={selectedHospital.name}
          onClose={() =>
            setShowAssessmentForm(
              false
            )
          }
        >

          <form
            onSubmit={
              saveAssessment
            }
            className="space-y-4"
          >

            <Select
              label="Patient"
              value={
                assessmentForm.patientId
              }
              onChange={(e) =>
                setAssessmentForm({
                  ...assessmentForm,
                  patientId:
                    e.target.value,
                })
              }
              options={hospitalPatients.map(
                (p) => p.id
              )}
              optionLabels={hospitalPatients.map(
                (p) =>
                  `${p.name} (${p.id})`
              )}
            />

            <div>

              <label className="block text-sm font-medium text-gray-700 mb-2">
                Assessment
              </label>

              <textarea
                rows="5"
                value={
                  assessmentForm.assessment
                }
                onChange={(e) =>
                  setAssessmentForm({
                    ...assessmentForm,
                    assessment:
                      e.target.value,
                  })
                }
                placeholder="Enter patient assessment..."
                className="hms-input w-full"
              />

            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium"
            >
              Save Assessment
            </button>

          </form>

        </Modal>

      )}

    </div></>
  )
}


// =======================================================
// PRESENTATIONAL HELPERS (shared HMS styling)
// =======================================================

function DashboardCard({ title, value, icon, subtitle }) {
  return (
    <div className="flex items-start gap-3.5 rounded-2xl border border-line bg-white p-4">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-xl text-brand-700">{icon}</span>
      <div className="min-w-0">
        <p className="text-[13px] font-medium text-ink-500">{title}</p>
        <p className="mt-0.5 text-2xl font-semibold leading-8 tracking-tight text-ink-900 tabular-nums">{value}</p>
        {subtitle && <p className="mt-0.5 text-xs text-ink-500">{subtitle}</p>}
      </div>
    </div>
  )
}

function SectionCard({ title, subtitle, action, children }) {
  return (
    <Card>
      <CardHeader title={title} description={subtitle} actions={action} />
      <div className="px-5 py-4">{children}</div>
    </Card>
  )
}

function Input({ label, name, value, onChange, type = "text", placeholder = "", required = false }) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="hms-label">
        {label}
        {required && <span className="ml-0.5 text-red-600" aria-hidden="true">*</span>}
      </label>
      <input id={id} type={type} name={name} value={value} onChange={onChange} placeholder={placeholder} required={required} className="hms-input w-full" />
    </div>
  )
}

function Select({ label, value, onChange, options, optionLabels }) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="hms-label">
        {label}
        <span className="ml-0.5 text-red-600" aria-hidden="true">*</span>
      </label>
      <select id={id} value={value} onChange={onChange} className="hms-input w-full" required>
        <option value="">Select {String(label).toLowerCase()}</option>
        {options.map((option, index) => (
          <option key={option} value={option}>{optionLabels ? optionLabels[index] : option}</option>
        ))}
      </select>
    </div>
  )
}

function Info({ label, value }) {
  return (
    <div className="rounded-xl bg-ink-50 px-4 py-3">
      <p className="text-xs font-medium text-ink-500">{label}</p>
      <p className="mt-0.5 font-medium text-ink-900">{value || "—"}</p>
    </div>
  )
}

function ReportCard({ title, value, icon }) {
  return <DashboardCard title={title} value={value} icon={icon} />
}

function Modal({ title, subtitle, onClose, children }) {
  return (
    <UiModal open onClose={onClose} title={title} description={subtitle}>
      {children}
    </UiModal>
  )
}

export default Nurses
