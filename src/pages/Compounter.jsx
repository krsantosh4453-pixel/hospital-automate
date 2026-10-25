import { useMemo, useState, useEffect } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import { ChartColumnIcon, ClipboardListIcon, DropletIcon, HeartPulseIcon, HospitalIcon, HouseIcon, NotebookPenIcon, PillIcon, StethoscopeIcon, UserIcon, UsersIcon, WalletIcon } from "lucide-react"

function Compounder() {
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
    alert("Profile updated successfully.")
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
      alert(
        "Only Admin can add a compounder."
      )
      return
    }

    if (!selectedHospital) {
      alert(
        "Please select a hospital first."
      )
      return
    }

    if (!newCompounder.name.trim()) {
      alert(
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

  const removeCompounder = (compounder) => {
    if (!isAdmin) {
      alert(
        "Only Admin can remove a compounder."
      )
      return
    }

    if (
      !selectedHospital ||
      compounder.hospitalId !==
      selectedHospital.id
    ) {
      alert(
        "You can only remove compounders from the selected hospital."
      )
      return
    }

    const confirmed =
      window.confirm(
        `Remove ${compounder.name}?`
      )

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
      alert("Please select patient.")
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
      alert(
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
      alert(
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
      alert(
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
      alert(
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

  const dischargePatient = (patient) => {
    if (!selectedHospital) return

    const confirmed =
      window.confirm(
        `Start discharge process for ${patient.name}?`
      )

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

    alert(
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
      icon: <HouseIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "profile",
      label: "My Profile",
      icon: <UserIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "patients",
      label: "Patients",
      icon: <UsersIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "assessment",
      label: "Assessment",
      icon: <StethoscopeIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "vitals",
      label: "Vitals",
      icon: <HeartPulseIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "notes",
      label: "Notes",
      icon: <NotebookPenIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "orders",
      label: "Orders",
      icon: <ClipboardListIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "mar",
      label: "Medicine / MAR",
      icon: <PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "blood",
      label: "Blood",
      icon: <DropletIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "discharge",
      label: "Discharge",
      icon: <HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "billing",
      label: "Billing",
      icon: <WalletIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
    {
      id: "reports",
      label: "Reports",
      icon: <ChartColumnIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />,
    },
  ]

  // =====================================================
  // NO HOSPITAL
  // =====================================================

  if (!selectedHospital) {
    return (
      <div className="p-6">

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 text-center">

          <div className="text-5xl mb-4">
            <HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />
          </div>

          <h1 className="text-2xl font-bold text-gray-800">
            Compounder Portal
          </h1>

          <p className="text-gray-500 mt-2">
            Please select a hospital to continue.
          </p>

        </div>

      </div>
    )
  }

  // =====================================================
  // MAIN UI
  // =====================================================

  return (
    <div className="p-6">

      {/* HEADER */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">

        <div>

          <h1 className="text-2xl font-bold text-gray-800">
            Compounder Portal
          </h1>

          <p className="text-gray-500 mt-1">
            {selectedHospital.name}
          </p>

          <p className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm max-w-2xl" role="note">
            The patient, vitals, notes, orders and medicine sections on this page are not connected to
            the hospital record yet and are not saved. Record vitals and notes on the Nurses page,
            dispense from Pharmacy, and view prescriptions on the Prescription page.
          </p>

        </div>

        <div className="flex items-center gap-3">

          <div className="px-4 py-2 rounded-xl bg-blue-50 border border-blue-200">

            <p className="text-xs text-gray-500">
              Logged in as
            </p>

            <p className="font-semibold text-blue-700">
              {profile.name}
            </p>

          </div>

          {/* ADMIN ONLY */}
          {isAdmin && (
            <button
              onClick={() =>
                setShowAddCompounder(
                  true
                )
              }
              className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-3 rounded-xl font-medium"
            >
              + Add Compounder
            </button>
          )}

        </div>

      </div>


      {/* HOSPITAL */}
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 mb-6">

        <p className="text-sm text-gray-500">
          Selected Hospital
        </p>

        <p className="font-semibold text-blue-700 mt-1">
          <HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> {selectedHospital.name}
        </p>

      </div>


      {/* TABS */}
      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-3 mb-6 overflow-x-auto">

        <div className="flex gap-2 min-w-max">

          {tabs.map((tab) => (

            <button
              key={tab.id}
              onClick={() =>
                setActiveTab(tab.id)
              }
              className={`px-4 py-2.5 rounded-xl text-sm font-medium ${activeTab === tab.id
                  ? "bg-blue-600 text-white"
                  : "text-gray-600 hover:bg-gray-100"
                }`}
            >
              {tab.icon} {tab.label}
            </button>

          ))}

        </div>

      </div>


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
              title="Medicines"
              value={
                hospitalMedicines.length
              }
              icon={<PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
              subtitle="Medicine records"
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
              title="Blood Requests"
              value={
                hospitalBlood.length
              }
              icon={<DropletIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
              subtitle="Blood records"
            />

          </div>


          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

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


            <SectionCard
              title="Pending Medicines"
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
          subtitle={`Compounder profile — ${selectedHospital.name}`}
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
                      Save Profile
                    </button>

                    <button
                      onClick={() =>
                        setEditingProfile(
                          false
                        )
                      }
                      className="px-5 py-2.5 rounded-xl bg-gray-100 text-gray-700"
                    >
                      Cancel
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

          <input
            type="text"
            value={patientSearch}
            onChange={(e) =>
              setPatientSearch(
                e.target.value
              )
            }
            placeholder="Search patient..."
            className="hms-input w-full mb-5"
          />

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
              + New Assessment
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
          title="Patient Vitals"
          subtitle="Record vital signs"
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
          title="Notes"
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
          MEDICINE / MAR
      ================================================= */}

      {activeTab === "mar" && (

        <SectionCard
          title="Medicine / MAR"
          subtitle="Medicine administration records"
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
                              Give
                            </button>

                          ) : (

                            <span className="text-sm text-gray-400">
                              Given
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
          subtitle={`Blood records — ${selectedHospital.name}`}
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
                        {item.units} unit(s)
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
                        Request
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
          title="Discharge"
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
                    Start Discharge
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
          title="Billing"
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
            title="Patients"
            value={
              hospitalPatients.length
            }
            icon={<UsersIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Vitals"
            value={
              hospitalVitals.length
            }
            icon={<HeartPulseIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Assessments"
            value={
              hospitalAssessments.length
            }
            icon={<StethoscopeIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Notes"
            value={
              hospitalNotes.length
            }
            icon={<NotebookPenIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Orders"
            value={
              hospitalOrders.length
            }
            icon={<ClipboardListIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Medicines"
            value={
              hospitalMedicines.length
            }
            icon={<PillIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Blood"
            value={
              hospitalBlood.length
            }
            icon={<DropletIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />}
          />

          <ReportCard
            title="Billing"
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
          title="Add Compounder"
          subtitle={`Add to ${selectedHospital.name}`}
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
                Cancel
              </button>

              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-blue-600 text-white font-medium"
              >
                Add Compounder
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
          title="Record Vitals"
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
          title="Add Note"
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
                Note
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
                placeholder="Enter note..."
                className="hms-input w-full"
              />

            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-xl"
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
          title="New Assessment"
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
                placeholder="Enter assessment..."
                className="hms-input w-full"
              />

            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-xl"
            >
              Save Assessment
            </button>

          </form>

        </Modal>

      )}

    </div>
  )
}


// =======================================================
// DASHBOARD CARD
// =======================================================

function DashboardCard({
  title,
  value,
  icon,
  subtitle,
}) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">

      <div className="flex items-center justify-between">

        <div>

          <p className="text-sm text-gray-500">
            {title}
          </p>

          <p className="text-3xl font-bold text-gray-800 mt-2">
            {value}
          </p>

          <p className="text-xs text-gray-400 mt-1">
            {subtitle}
          </p>

        </div>

        <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-2xl">
          {icon}
        </div>

      </div>

    </div>
  )
}


// =======================================================
// SECTION CARD
// =======================================================

function SectionCard({
  title,
  subtitle,
  action,
  children,
}) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100">

      <div className="p-6 border-b flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">

        <div>

          <h2 className="text-lg font-semibold text-gray-800">
            {title}
          </h2>

          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">
              {subtitle}
            </p>
          )}

        </div>

        {action}

      </div>

      <div className="p-6">
        {children}
      </div>

    </div>
  )
}


// =======================================================
// INPUT
// =======================================================

function Input({
  label,
  name,
  value,
  onChange,
  type = "text",
  placeholder = "",
  required = false,
}) {
  return (
    <div>

      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>

      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        className="hms-input w-full"
      />

    </div>
  )
}


// =======================================================
// SELECT
// =======================================================

function Select({
  label,
  value,
  onChange,
  options,
  optionLabels,
}) {
  return (
    <div>

      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>

      <select
        value={value}
        onChange={onChange}
        className="hms-input w-full"
        required
      >

        <option value="">
          Select {label}
        </option>

        {options.map(
          (option, index) => (

            <option
              key={option}
              value={option}
            >
              {optionLabels
                ? optionLabels[index]
                : option}
            </option>

          )
        )}

      </select>

    </div>
  )
}


// =======================================================
// INFO
// =======================================================

function Info({
  label,
  value,
}) {
  return (
    <div className="bg-gray-50 rounded-xl p-4">

      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="font-medium text-gray-800 mt-1">
        {value || "-"}
      </p>

    </div>
  )
}


// =======================================================
// REPORT CARD
// =======================================================

function ReportCard({
  title,
  value,
  icon,
}) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">

      <div className="flex items-center justify-between">

        <div>

          <p className="text-sm text-gray-500">
            {title}
          </p>

          <p className="text-3xl font-bold text-gray-800 mt-2">
            {value}
          </p>

        </div>

        <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-2xl">
          {icon}
        </div>

      </div>

    </div>
  )
}


// =======================================================
// MODAL
// =======================================================

function Modal({
  title,
  subtitle,
  onClose,
  children,
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">

      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">

        <div className="flex items-center justify-between px-6 py-5 border-b">

          <div>

            <h2 className="text-xl font-semibold text-gray-800">
              {title}
            </h2>

            {subtitle && (
              <p className="text-sm text-gray-500 mt-1">
                {subtitle}
              </p>
            )}

          </div>

          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-2xl"
          >
            ×
          </button>

        </div>

        <div className="p-6">
          {children}
        </div>

      </div>

    </div>
  )
}

export default Compounder