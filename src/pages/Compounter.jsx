import { useMemo, useState, useEffect, useId } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import { ChartColumnIcon, ClipboardListIcon, DropletIcon, HeartPulseIcon, HospitalIcon, HouseIcon, NotebookPenIcon, PillIcon, StethoscopeIcon, UserIcon, UsersIcon, WalletIcon } from "lucide-react"
import { useToast } from "../components/Toast.jsx"
import { Alert, Button, Card, CardHeader, EmptyState, Modal as UiModal, PageHeader as UiPageHeader, Tabs } from "../components/ui"
import { UserPlus as UserPlusIcon } from "lucide-react"
import { useConfirm } from "../components/ui"
import { useLanguage } from "../assets/context/LanguageContext.jsx"

function Compounder() {
  const { t } = useLanguage()
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()

  const { selectedHospital } = usePatient()

  // =====================================================
  // CURRENT USER
  // =====================================================

  const currentUser = {
    id: "C001",
    name: "Rakesh Kumar",
    role: "Compounder",
    hospitalId: selectedHospital?.id || 1,
    department: "General Medicine",
    shift: "Morning",
    phone: "9876543210",
    email: "rakesh@example.com",
    qualification: "Diploma in Pharmacy",
    joiningDate: "10 Jan 2025",
    status: "On Duty",
  }

  const isAdmin = currentUser.role === "Admin"
  const isCompounder =
    currentUser.role === "Compounder"

  // =====================================================
  // COMPOUNDER DATA
  // =====================================================

  const [compounders, setCompounders] =
    useState([])

  useEffect(() => {
    if (!selectedHospital?.id) return
    let cancelled = false
    api.compounder
      .list(selectedHospital.id)
      .then((data) => {
        const results = Array.isArray(data) ? data : data?.results || []
        if (cancelled || results.length === 0) return
        setCompounders(
          results.map((item) => ({
            id: item.id,
            hospitalId: item.hospital || selectedHospital.id,
            name: item.name,
            department: item.department || item.qualification || "Pharmacy",
            shift: item.shift || "Morning",
            phone: item.phone || "",
            email: item.email || "",
            qualification: item.qualification || "",
            joiningDate: item.joining_date || item.joiningDate || "",
            status: item.status || "On Duty",
          }))
        )
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [selectedHospital])

  // =====================================================
  // PATIENTS
  // =====================================================

  const [patients] = useState([])

  // =====================================================
  // VITALS
  // =====================================================

  const [vitals, setVitals] = useState([])

  // =====================================================
  // ASSESSMENTS
  // =====================================================

  const [assessments, setAssessments] =
    useState([])

  // =====================================================
  // NOTES
  // =====================================================

  const [notes, setNotes] = useState([])

  // =====================================================
  // ORDERS
  // =====================================================

  const [orders] = useState([])

  // =====================================================
  // MEDICINE / MAR
  // =====================================================

  const [medicines, setMedicines] = useState([])

  // =====================================================
  // BLOOD
  // =====================================================

  const [bloodRequests, setBloodRequests] =
    useState([])

  // =====================================================
  // DISCHARGE
  // =====================================================

  const [discharges, setDischarges] = useState([])

  // =====================================================
  // BILLING
  // =====================================================

  const [billing] = useState([])

  // =====================================================
  // HOSPITAL DATA
  // =====================================================

  const hospitalCompounders = useMemo(() => {
    if (!selectedHospital) return []

    return compounders.filter(
      (item) =>
        item.hospitalId ===
        selectedHospital.id
    )
  }, [compounders, selectedHospital])

  const hospitalPatients = useMemo(() => {
    if (!selectedHospital) return []

    return patients.filter(
      (item) =>
        item.hospitalId ===
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

  const hospitalMedicines = useMemo(() => {
    if (!selectedHospital) return []

    return medicines.filter(
      (item) =>
        item.hospitalId ===
        selectedHospital.id
    )
  }, [medicines, selectedHospital])

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
  // PROFILE
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

  const saveProfile = () => {
    setEditingProfile(false)
    toast.success("Profile updated successfully.")
  }

  // =====================================================
  // ADD COMPOUNDER - ADMIN ONLY
  // =====================================================

  const [showAddCompounder, setShowAddCompounder] =
    useState(false)

  const [newCompounder, setNewCompounder] =
    useState({
      name: "",
      department: "General Medicine",
      shift: "Morning",
      phone: "",
      email: "",
      qualification: "D.Pharm",
      joiningDate: "",
      status: "On Duty",
    })

  const handleAddCompounder = (e) => {
    e.preventDefault()

    if (!isAdmin) {
      toast.warning(
        "Only Admin can add a compounder."
      )
      return
    }

    if (!selectedHospital) {
      toast.warning(
        "Please select a hospital first."
      )
      return
    }

    if (!newCompounder.name.trim()) {
      toast.warning(
        "Please enter compounder name."
      )
      return
    }

    const count =
      compounders.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length + 1

    const newId =
      `C${selectedHospital.id}${String(
        count
      ).padStart(2, "0")}`

    const compounder = {
      ...newCompounder,
      id: newId,
      hospitalId: selectedHospital.id,
      name: newCompounder.name.trim(),
    }

    setCompounders((prev) => [
      ...prev,
      compounder,
    ])

    setNewCompounder({
      name: "",
      department: "General Medicine",
      shift: "Morning",
      phone: "",
      email: "",
      qualification: "D.Pharm",
      joiningDate: "",
      status: "On Duty",
    })

    setShowAddCompounder(false)
  }

  // =====================================================
  // REMOVE COMPOUNDER - ADMIN ONLY
  // =====================================================

  const removeCompounder = async (compounder) => {
    if (!isAdmin) {
      toast.warning(
        "Only Admin can remove a compounder."
      )
      return
    }

    if (
      !selectedHospital ||
      compounder.hospitalId !==
      selectedHospital.id
    ) {
      toast.warning(
        "You can only remove compounders from the selected hospital."
      )
      return
    }

    const confirmed =
      (await confirm(
        `Remove ${compounder.name}?`
      ))

    if (!confirmed) return

    setCompounders((prev) =>
      prev.filter(
        (item) =>
          item.id !== compounder.id
      )
    )
  }

  // =====================================================
  // VITALS
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

  const saveVitals = (e) => {
    e.preventDefault()

    if (!selectedHospital) return

    if (!vitalForm.patientId) {
      toast.warning("Please select patient.")
      return
    }

    const newVital = {
      id: `V-${Date.now()}`,
      hospitalId:
        selectedHospital.id,
      patientId:
        vitalForm.patientId,
      temperature:
        vitalForm.temperature,
      bp: vitalForm.bp,
      pulse: vitalForm.pulse,
      spo2: vitalForm.spo2,
      respiratoryRate:
        vitalForm.respiratoryRate,
      recordedBy: profile.name,
      time:
        new Date().toLocaleTimeString(
          "en-IN",
          {
            hour: "2-digit",
            minute: "2-digit",
          }
        ),
    }

    setVitals((prev) => [
      newVital,
      ...prev,
    ])

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
  // NOTES
  // =====================================================

  const [showNoteForm, setShowNoteForm] =
    useState(false)

  const [noteForm, setNoteForm] =
    useState({
      patientId: "",
      text: "",
    })

  const saveNote = (e) => {
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

    const newNote = {
      id: `NOTE-${Date.now()}`,
      hospitalId:
        selectedHospital.id,
      patientId:
        noteForm.patientId,
      text: noteForm.text.trim(),
      createdBy: profile.name,
      date: new Date().toLocaleDateString(
        "en-IN"
      ),
    }

    setNotes((prev) => [
      newNote,
      ...prev,
    ])

    setNoteForm({
      patientId: "",
      text: "",
    })

    setShowNoteForm(false)
  }

  // =====================================================
  // ASSESSMENT
  // =====================================================

  const [showAssessmentForm, setShowAssessmentForm] =
    useState(false)

  const [assessmentForm, setAssessmentForm] =
    useState({
      patientId: "",
      assessment: "",
    })

  const saveAssessment = (e) => {
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

    const newAssessment = {
      id: `AS-${Date.now()}`,
      hospitalId:
        selectedHospital.id,
      patientId:
        assessmentForm.patientId,
      assessment:
        assessmentForm.assessment.trim(),
      createdBy: profile.name,
      date: new Date().toLocaleDateString(
        "en-IN"
      ),
    }

    setAssessments((prev) => [
      newAssessment,
      ...prev,
    ])

    setAssessmentForm({
      patientId: "",
      assessment: "",
    })

    setShowAssessmentForm(false)
  }

  // =====================================================
  // MEDICINE ADMINISTRATION
  // =====================================================

  const administerMedicine = (medicine) => {
    if (!selectedHospital) return

    if (
      medicine.hospitalId !==
      selectedHospital.id
    ) {
      toast.error(
        "Invalid hospital access."
      )
      return
    }

    setMedicines((prev) =>
      prev.map((item) =>
        item.id === medicine.id
          ? {
            ...item,
            status: "Given",
            administeredBy:
              profile.name,
          }
          : item
      )
    )
  }

  // =====================================================
  // BLOOD
  // =====================================================

  const requestBlood = (item) => {
    if (!selectedHospital) return

    if (
      item.hospitalId !==
      selectedHospital.id
    ) {
      toast.error(
        "Invalid hospital access."
      )
      return
    }

    setBloodRequests((prev) =>
      prev.map((blood) =>
        blood.id === item.id
          ? {
            ...blood,
            status: "Requested",
          }
          : blood
      )
    )
  }

  // =====================================================
  // DISCHARGE
  // =====================================================

  const dischargePatient = async (patient) => {
    if (!selectedHospital) return

    const confirmed =
      (await confirm(
        t("Start discharge process for {patient}?", { patient: patient.name })
      ))

    if (!confirmed) return

    const discharge = {
      id: `DIS-${Date.now()}`,
      hospitalId:
        selectedHospital.id,
      patientId: patient.id,
      patientName: patient.name,
      date: new Date().toLocaleDateString(
        "en-IN"
      ),
      preparedBy: profile.name,
      status: "Discharge Requested",
    }

    setDischarges((prev) => [
      discharge,
      ...prev,
    ])

    toast.success(
      "Discharge request created."
    )
  }

  // =====================================================
  // NAVIGATION
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
      label: "Medicine / MAR",
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
        <UiPageHeader title={t("Compounder")} breadcrumbs={[{ label: "Home", to: "/" }, { label: "Compounder" }]} />
        <Card><EmptyState icon={HospitalIcon} title={t("Select a hospital")} description="Choose a hospital in the header to open the compounder workspace." /></Card>
      </div></>
    )
  }

  // =====================================================
  // MAIN UI
  // =====================================================

  return (
    <>{confirmDialog}<div className="space-y-5">
      <UiPageHeader
        title={t("Compounder")}
        description={t("{hospital} · signed in as {name}", { hospital: selectedHospital.name, name: profile.name })}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Compounder" }]}
        actions={isAdmin && <Button icon={UserPlusIcon} onClick={() => setShowAddCompounder(true)}>{t("Add compounder")}</Button>}
      />

      <Alert tone="warning" title={t("Most sections here are not saved")}>
        {t("The patient, vitals, notes, orders and medicine sections on this page are not connected to the hospital record yet. Record vitals and notes on the Nursing page, dispense from Pharmacy, and view prescriptions on the Prescriptions page.")}
      </Alert>

      <Tabs tabs={tabs} value={activeTab} onChange={setActiveTab} label="Compounder sections" />

      {/* =================================================
          HOME
      ================================================= */}

      {activeTab === "home" && (

        <div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">

            <DashboardCard
              title={t("Patients")}
              value={
                hospitalPatients.length
              }
              icon={<UsersIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
              subtitle="Hospital patients"
            />

            <DashboardCard
              title={t("Medicines")}
              value={
                hospitalMedicines.length
              }
              icon={<PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
              subtitle="Medicine records"
            />

            <DashboardCard
              title={t("Pending Orders")}
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
              title={t("Blood Requests")}
              value={
                hospitalBlood.length
              }
              icon={<DropletIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
              subtitle="Blood records"
            />

          </div>


          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            <SectionCard
              title={t("Recent Patients")}
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


            <SectionCard
              title={t("Pending Medicines")}
              subtitle="Medicine administration"
            >

              {hospitalMedicines
                .filter(
                  (item) =>
                    item.status ===
                    "Pending"
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
                        className="px-3 py-2 rounded-lg bg-green-100 text-green-700 text-sm font-medium"
                      >
                        {t("Give")}
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
          title={t("My Profile")}
          subtitle={t("Compounder profile — {hospital}", { hospital: selectedHospital.name })}
        >

          <div className="flex flex-col md:flex-row gap-6">

            <div className="w-24 h-24 rounded-full bg-blue-100 flex items-center justify-center text-5xl">
              <PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />
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
                    value={
                      profile.department
                    }
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
                    value={
                      profile.department
                    }
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
                      {t("Save Profile")}
                    </button>

                    <button
                      onClick={() =>
                        setEditingProfile(
                          false
                        )
                      }
                      className="px-5 py-2.5 rounded-xl bg-gray-100 text-gray-700"
                    >
                      {t("Cancel")}
                    </button>

                  </div>

                ) : (

                  <button
                    onClick={() =>
                      setEditingProfile(
                        true
                      )
                    }
                    className="px-5 py-2.5 rounded-xl bg-blue-600 text-white font-medium"
                  >
                    {t("Edit Profile")}
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
          title={t("Patient List")}
          subtitle={`Patients — ${selectedHospital.name}`}
        >

          <input
            type="text"
            value={patientSearch}
            onChange={(e) =>
              setPatientSearch(
                e.target.value
              )
            }
            placeholder={t("Search patient...")}
            className="hms-input w-full mb-5"
          />

          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="bg-gray-50">

                <tr>

                  <th className="text-left px-5 py-4">
                    {t("Patient")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Department")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Doctor")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Ward / Bed")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Status")}
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
                          {patient.age}{" "}{t("years")}
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
          title={t("Patient Assessment")}
          subtitle="Assessment records"
          action={
            <button
              onClick={() =>
                setShowAssessmentForm(
                  true
                )
              }
              className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm"
            >
              {t("+ New Assessment")}
            </button>
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

                    <p className="font-semibold text-gray-800">
                      {patient?.name}
                    </p>

                    <p className="text-sm text-gray-500 mt-1">
                      {item.date} ·{" "}
                      {item.createdBy}
                    </p>

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
          title={t("Patient Vitals")}
          subtitle="Record vital signs"
          action={
            <button
              onClick={() =>
                setShowVitalsForm(true)
              }
              className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm"
            >
              {t("+ Record Vitals")}
            </button>
          }
        >

          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="bg-gray-50">

                <tr>

                  <th className="text-left px-5 py-4">
                    {t("Patient")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Temperature")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("BP")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Pulse")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("SpO₂")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Time")}
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
          title={t("Notes")}
          subtitle="Patient care notes"
          action={
            <button
              onClick={() =>
                setShowNoteForm(true)
              }
              className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm"
            >
              {t("+ Add Note")}
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
                      {t("By")}{" "}{note.createdBy}
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
          title={t("Orders")}
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
          MEDICINE / MAR
      ================================================= */}

      {activeTab === "mar" && (

        <SectionCard
          title={t("Medicine / MAR")}
          subtitle="Medicine administration records"
        >

          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="bg-gray-50">

                <tr>

                  <th className="text-left px-5 py-4">
                    {t("Patient")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Medicine")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Dose")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Route")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Frequency")}
                  </th>

                  <th className="text-left px-5 py-4">
                    {t("Status")}
                  </th>

                  <th className="text-right px-5 py-4">
                    {t("Action")}
                  </th>

                </tr>

              </thead>

              <tbody className="divide-y">

                {hospitalMedicines.map(
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
                            className={`px-3 py-1 rounded-full text-xs ${item.status ===
                                "Given"
                                ? "bg-green-100 text-green-700"
                                : "bg-yellow-100 text-yellow-700"
                              }`}
                          >
                            {item.status}
                          </span>

                        </td>

                        <td className="px-5 py-4 text-right">

                          {item.status ===
                            "Pending" ? (

                            <button
                              onClick={() =>
                                administerMedicine(
                                  item
                                )
                              }
                              className="px-3 py-2 rounded-lg bg-green-600 text-white text-sm"
                            >
                              {t("Give")}
                            </button>

                          ) : (

                            <span className="text-sm text-gray-400">
                              {t("Given")}
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
          title={t("Blood Management")}
          subtitle={t("Blood records — {hospital}", { hospital: selectedHospital.name })}
        >

          <div className="space-y-4">

            {hospitalBlood.map(
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
                    className="border rounded-xl p-4 flex items-center justify-between gap-4"
                  >

                    <div>

                      <p className="font-medium text-gray-800">
                        {patient?.name}
                      </p>

                      <p className="text-sm text-gray-500">
                        {item.bloodGroup} ·{" "}
                        {item.units}{" "}{t("unit(s)")}
                      </p>

                    </div>

                    <div className="flex items-center gap-3">

                      <span
                        className={`px-3 py-1 rounded-full text-xs ${item.urgency ===
                            "Urgent"
                            ? "bg-red-100 text-red-700"
                            : "bg-gray-100 text-gray-600"
                          }`}
                      >
                        {item.urgency}
                      </span>

                      <button
                        onClick={() =>
                          requestBlood(
                            item
                          )
                        }
                        className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm"
                      >
                        {t("Request")}
                      </button>

                    </div>

                  </div>
                )
              }
            )}

          </div>

        </SectionCard>

      )}


      {/* =================================================
          DISCHARGE
      ================================================= */}

      {activeTab === "discharge" && (

        <SectionCard
          title={t("Discharge")}
          subtitle="Patient discharge requests"
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
                    className="px-4 py-2 rounded-xl bg-orange-500 text-white text-sm font-medium"
                  >
                    {t("Start Discharge")}
                  </button>

                </div>

              )
            )}

          </div>

        </SectionCard>

      )}


      {/* =================================================
          BILLING
      ================================================= */}

      {activeTab === "billing" && (

        <SectionCard
          title={t("Billing")}
          subtitle={`Billing — ${selectedHospital.name}`}
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

                    <p className="text-2xl font-bold mt-5">
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
            title={t("Patients")}
            value={
              hospitalPatients.length
            }
            icon={<UsersIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title={t("Vitals")}
            value={
              hospitalVitals.length
            }
            icon={<HeartPulseIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title={t("Assessments")}
            value={
              hospitalAssessments.length
            }
            icon={<StethoscopeIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title={t("Notes")}
            value={
              hospitalNotes.length
            }
            icon={<NotebookPenIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title={t("Orders")}
            value={
              hospitalOrders.length
            }
            icon={<ClipboardListIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title={t("Medicines")}
            value={
              hospitalMedicines.length
            }
            icon={<PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title={t("Blood")}
            value={
              hospitalBlood.length
            }
            icon={<DropletIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title={t("Billing")}
            value={
              hospitalBilling.length
            }
            icon={<WalletIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

        </div>

      )}


      {/* =================================================
          ADD COMPOUNDER MODAL - ADMIN ONLY
      ================================================= */}

      {showAddCompounder && isAdmin && (

        <Modal
          title={t("Add Compounder")}
          subtitle={t("Add to {hospital}", { hospital: selectedHospital.name })}
          onClose={() =>
            setShowAddCompounder(
              false
            )
          }
        >

          <form
            onSubmit={
              handleAddCompounder
            }
            className="space-y-4"
          >

            <Input
              label="Compounder Name"
              value={
                newCompounder.name
              }
              onChange={(e) =>
                setNewCompounder({
                  ...newCompounder,
                  name: e.target.value,
                })
              }
              required
            />

            <Input
              label="Phone"
              value={
                newCompounder.phone
              }
              onChange={(e) =>
                setNewCompounder({
                  ...newCompounder,
                  phone: e.target.value,
                })
              }
              required
            />

            <Input
              label="Email"
              value={
                newCompounder.email
              }
              onChange={(e) =>
                setNewCompounder({
                  ...newCompounder,
                  email: e.target.value,
                })
              }
            />

            <Select
              label="Department"
              value={
                newCompounder.department
              }
              onChange={(e) =>
                setNewCompounder({
                  ...newCompounder,
                  department:
                    e.target.value,
                })
              }
              options={[
                "General Medicine",
                "Emergency",
                "Pharmacy",
                "Cardiology",
                "Orthopedics",
                "Laboratory",
              ]}
            />

            <Select
              label="Shift"
              value={
                newCompounder.shift
              }
              onChange={(e) =>
                setNewCompounder({
                  ...newCompounder,
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
                newCompounder.qualification
              }
              onChange={(e) =>
                setNewCompounder({
                  ...newCompounder,
                  qualification:
                    e.target.value,
                })
              }
              options={[
                "D.Pharm",
                "Diploma in Pharmacy",
                "B.Pharm",
              ]}
            />

            <Input
              label="Joining Date"
              type="date"
              value={
                newCompounder.joiningDate
              }
              onChange={(e) =>
                setNewCompounder({
                  ...newCompounder,
                  joiningDate:
                    e.target.value,
                })
              }
            />

            <Select
              label="Status"
              value={
                newCompounder.status
              }
              onChange={(e) =>
                setNewCompounder({
                  ...newCompounder,
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
                  setShowAddCompounder(
                    false
                  )
                }
                className="px-5 py-2.5 rounded-xl bg-gray-100 text-gray-700"
              >
                {t("Cancel")}
              </button>

              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-blue-600 text-white font-medium"
              >
                {t("Add Compounder")}
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
          title={t("Record Vitals")}
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
              {t("Save Vitals")}
            </button>

          </form>

        </Modal>

      )}


      {/* =================================================
          NOTE MODAL
      ================================================= */}

      {showNoteForm && (

        <Modal
          title={t("Add Note")}
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
                {t("Note")}
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
                placeholder={t("Enter note...")}
                className="hms-input w-full"
              />

            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-xl"
            >
              {t("Save Note")}
            </button>

          </form>

        </Modal>

      )}


      {/* =================================================
          ASSESSMENT MODAL
      ================================================= */}

      {showAssessmentForm && (

        <Modal
          title={t("New Assessment")}
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
                {t("Assessment")}
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
                placeholder={t("Enter assessment...")}
                className="hms-input w-full"
              />

            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-xl"
            >
              {t("Save Assessment")}
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
  const { t } = useLanguage()
  return (
    <div className="flex items-start gap-3.5 rounded-2xl border border-line bg-white p-4">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-xl text-brand-700">{icon}</span>
      <div className="min-w-0">
        <p className="text-[13px] font-medium text-ink-500">{t(title)}</p>
        <p className="mt-0.5 text-2xl font-semibold leading-8 tracking-tight text-ink-900 tabular-nums">{value}</p>
        {subtitle && <p className="mt-0.5 text-xs text-ink-500">{t(subtitle)}</p>}
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
  const { t } = useLanguage()
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="hms-label">
        {t(label)}
        {required && <span className="ml-0.5 text-red-600" aria-hidden="true">*</span>}
      </label>
      <input id={id} type={type} name={name} value={value} onChange={onChange} placeholder={placeholder} required={required} className="hms-input w-full" />
    </div>
  )
}

function Select({ label, value, onChange, options, optionLabels }) {
  const { t } = useLanguage()
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="hms-label">
        {t(label)}
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
  const { t } = useLanguage()
  return (
    <div className="rounded-xl bg-ink-50 px-4 py-3">
      <p className="text-xs font-medium text-ink-500">{t(label)}</p>
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

export default Compounder
