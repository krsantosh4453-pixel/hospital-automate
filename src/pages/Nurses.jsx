import { useMemo, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"

function Nurses() {
  const { selectedHospital } = usePatient()

  // =====================================================
  // CURRENT USER
  // =====================================================

  const currentUser = {
    id: "N001",
    name: "Sunita Kumari",
    role: "Nurse",
    hospitalId: selectedHospital?.id || 1,
    department: "General Medicine",
    shift: "Morning",
    phone: "9876543201",
    email: "sunita@example.com",
    qualification: "B.Sc Nursing",
    joiningDate: "10 Jan 2025",
    status: "On Duty",
  }

  const isAdmin = currentUser.role === "Admin"
  const isNurse = currentUser.role === "Nurse"

  // =====================================================
  // NURSES
  // =====================================================

  const [nurses, setNurses] = useState([
    {
      id: "N001",
      hospitalId: 1,
      name: "Sunita Kumari",
      department: "General Medicine",
      shift: "Morning",
      phone: "9876543201",
      email: "sunita@example.com",
      qualification: "B.Sc Nursing",
      joiningDate: "10 Jan 2025",
      status: "On Duty",
    },
    {
      id: "N002",
      hospitalId: 1,
      name: "Pooja Singh",
      department: "Emergency",
      shift: "Evening",
      phone: "9876543202",
      email: "pooja@example.com",
      qualification: "GNM",
      joiningDate: "15 Mar 2025",
      status: "On Duty",
    },
    {
      id: "N003",
      hospitalId: 1,
      name: "Anita Kumari",
      department: "ICU",
      shift: "Night",
      phone: "9876543203",
      email: "anita@example.com",
      qualification: "B.Sc Nursing",
      joiningDate: "20 Apr 2025",
      status: "Off Duty",
    },
    {
      id: "N004",
      hospitalId: 2,
      name: "Neha Singh",
      department: "General Medicine",
      shift: "Morning",
      phone: "9876543204",
      email: "neha@example.com",
      qualification: "GNM",
      joiningDate: "02 Feb 2025",
      status: "On Duty",
    },
    {
      id: "N005",
      hospitalId: 2,
      name: "Kavita Kumari",
      department: "Emergency",
      shift: "Evening",
      phone: "9876543205",
      email: "kavita@example.com",
      qualification: "B.Sc Nursing",
      joiningDate: "18 May 2025",
      status: "On Duty",
    },
    {
      id: "N006",
      hospitalId: 2,
      name: "Rani Devi",
      department: "ICU",
      shift: "Night",
      phone: "9876543206",
      email: "rani@example.com",
      qualification: "GNM",
      joiningDate: "05 Jun 2025",
      status: "Off Duty",
    },
    {
      id: "N007",
      hospitalId: 3,
      name: "Shweta Kumari",
      department: "General Medicine",
      shift: "Morning",
      phone: "9876543207",
      email: "shweta@example.com",
      qualification: "B.Sc Nursing",
      joiningDate: "12 Jul 2025",
      status: "On Duty",
    },
    {
      id: "N008",
      hospitalId: 3,
      name: "Meena Singh",
      department: "Emergency",
      shift: "Evening",
      phone: "9876543208",
      email: "meena@example.com",
      qualification: "GNM",
      joiningDate: "22 Aug 2025",
      status: "Off Duty",
    },
  ])

  // =====================================================
  // PATIENTS
  // =====================================================

  const [patients] = useState([
    {
      id: "P001",
      hospitalId: 1,
      name: "Rahul Kumar",
      age: 42,
      gender: "Male",
      department: "General Medicine",
      doctor: "Dr. Sharma",
      ward: "Ward A",
      bed: "A-12",
      status: "Admitted",
    },
    {
      id: "P002",
      hospitalId: 1,
      name: "Priya Singh",
      age: 35,
      gender: "Female",
      department: "Cardiology",
      doctor: "Dr. Kumar",
      ward: "Ward B",
      bed: "B-08",
      status: "Admitted",
    },
    {
      id: "P003",
      hospitalId: 1,
      name: "Amit Kumar",
      age: 51,
      gender: "Male",
      department: "Emergency",
      doctor: "Dr. Singh",
      ward: "Emergency",
      bed: "E-04",
      status: "Critical",
    },
    {
      id: "P004",
      hospitalId: 2,
      name: "Ravi Kumar",
      age: 29,
      gender: "Male",
      department: "General Medicine",
      doctor: "Dr. Verma",
      ward: "Ward A",
      bed: "A-05",
      status: "Admitted",
    },
    {
      id: "P005",
      hospitalId: 2,
      name: "Neha Kumari",
      age: 46,
      gender: "Female",
      department: "ICU",
      doctor: "Dr. Gupta",
      ward: "ICU",
      bed: "ICU-02",
      status: "Critical",
    },
    {
      id: "P006",
      hospitalId: 3,
      name: "Sanjay Singh",
      age: 38,
      gender: "Male",
      department: "Orthopedics",
      doctor: "Dr. Patel",
      ward: "Ward C",
      bed: "C-11",
      status: "Admitted",
    },
  ])

  // =====================================================
  // VITALS
  // =====================================================

  const [vitals, setVitals] = useState([
    {
      id: "V001",
      hospitalId: 1,
      patientId: "P001",
      temperature: "98.6",
      bp: "120/80",
      pulse: "76",
      spo2: "98",
      respiratoryRate: "16",
      recordedBy: "Sunita Kumari",
      time: "10:20 AM",
    },
    {
      id: "V002",
      hospitalId: 1,
      patientId: "P002",
      temperature: "99.1",
      bp: "128/84",
      pulse: "82",
      spo2: "97",
      respiratoryRate: "18",
      recordedBy: "Pooja Singh",
      time: "10:35 AM",
    },
    {
      id: "V003",
      hospitalId: 1,
      patientId: "P003",
      temperature: "101.2",
      bp: "145/90",
      pulse: "104",
      spo2: "91",
      respiratoryRate: "22",
      recordedBy: "Sunita Kumari",
      time: "10:45 AM",
    },
  ])

  // =====================================================
  // ASSESSMENTS
  // =====================================================

  const [assessments, setAssessments] = useState([
    {
      id: "AS001",
      hospitalId: 1,
      patientId: "P001",
      assessment:
        "Patient stable. No acute distress.",
      nurse: "Sunita Kumari",
      date: "02 Sep 2026",
    },
    {
      id: "AS002",
      hospitalId: 1,
      patientId: "P002",
      assessment:
        "Patient reports mild chest discomfort.",
      nurse: "Pooja Singh",
      date: "02 Sep 2026",
    },
  ])

  // =====================================================
  // NOTES
  // =====================================================

  const [notes, setNotes] = useState([
    {
      id: "NOTE001",
      hospitalId: 1,
      patientId: "P001",
      text: "Patient resting comfortably.",
      createdBy: "Sunita Kumari",
      date: "02 Sep 2026",
    },
  ])

  // =====================================================
  // ORDERS
  // =====================================================

  const [orders] = useState([
    {
      id: "ORD001",
      hospitalId: 1,
      patientId: "P001",
      order: "CBC Blood Test",
      doctor: "Dr. Sharma",
      status: "Pending",
    },
    {
      id: "ORD002",
      hospitalId: 1,
      patientId: "P002",
      order: "ECG",
      doctor: "Dr. Kumar",
      status: "Completed",
    },
    {
      id: "ORD003",
      hospitalId: 1,
      patientId: "P003",
      order: "Emergency Blood Test",
      doctor: "Dr. Singh",
      status: "Pending",
    },
  ])

  // =====================================================
  // MAR - MEDICINE ADMINISTRATION
  // =====================================================

  const [mar, setMar] = useState([
    {
      id: "MAR001",
      hospitalId: 1,
      patientId: "P001",
      medicine: "Medicine A",
      dose: "500 mg",
      route: "Oral",
      frequency: "1-0-1",
      time: "08:00 AM",
      status: "Given",
      givenBy: "Sunita Kumari",
    },
    {
      id: "MAR002",
      hospitalId: 1,
      patientId: "P001",
      medicine: "Medicine B",
      dose: "10 mg",
      route: "Oral",
      frequency: "0-0-1",
      time: "08:00 PM",
      status: "Pending",
      givenBy: "",
    },
    {
      id: "MAR003",
      hospitalId: 1,
      patientId: "P003",
      medicine: "Emergency Medicine",
      dose: "1 dose",
      route: "IV",
      frequency: "STAT",
      time: "10:00 AM",
      status: "Pending",
      givenBy: "",
    },
  ])

  // =====================================================
  // BLOOD
  // =====================================================

  const [bloodRequests, setBloodRequests] =
    useState([
      {
        id: "BL001",
        hospitalId: 1,
        patientId: "P003",
        bloodGroup: "B+",
        units: 2,
        urgency: "Urgent",
        status: "Requested",
      },
      {
        id: "BL002",
        hospitalId: 1,
        patientId: "P002",
        bloodGroup: "O+",
        units: 1,
        urgency: "Normal",
        status: "Available",
      },
    ])

  // =====================================================
  // DISCHARGE
  // =====================================================

  const [discharges, setDischarges] = useState([])

  // =====================================================
  // BILLING
  // =====================================================

  const [billing] = useState([
    {
      id: "BILL001",
      hospitalId: 1,
      patientId: "P001",
      amount: 4500,
      status: "Pending",
    },
    {
      id: "BILL002",
      hospitalId: 1,
      patientId: "P002",
      amount: 7200,
      status: "Paid",
    },
  ])

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
      patients: patients.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      vitals: vitals.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      assessments: assessments.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      orders: orders.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      mar: mar.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      blood: bloodRequests.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,

      billing: billing.filter(
        (item) =>
          item.hospitalId ===
          selectedHospital.id
      ).length,
    }
  }, [
    selectedHospital,
    patients,
    vitals,
    assessments,
    orders,
    mar,
    bloodRequests,
    billing,
  ])

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

  const saveProfile = () => {
    setEditingProfile(false)
    alert("Profile updated successfully.")
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

  const handleAddNurse = (e) => {
    e.preventDefault()

    if (!isAdmin) {
      alert(
        "Only Admin can add a nurse."
      )
      return
    }

    if (!selectedHospital) {
      alert(
        "Please select a hospital first."
      )
      return
    }

    const count =
      nurses.filter(
        (nurse) =>
          nurse.hospitalId ===
          selectedHospital.id
      ).length + 1

    const nurse = {
      ...newNurse,
      id: `N${selectedHospital.id}${String(
        count
      ).padStart(2, "0")}`,
      hospitalId: selectedHospital.id,
    }

    setNurses((prev) => [
      ...prev,
      nurse,
    ])

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
  }

  // =====================================================
  // REMOVE NURSE
  // ADMIN ONLY
  // =====================================================

  const removeNurse = (nurse) => {
    if (!isAdmin) {
      alert(
        "Only Admin can remove a nurse."
      )
      return
    }

    if (
      !selectedHospital ||
      nurse.hospitalId !==
      selectedHospital.id
    ) {
      alert(
        "You can only remove nurses from the selected hospital."
      )
      return
    }

    const confirmRemove =
      window.confirm(
        `Remove ${nurse.name}?`
      )

    if (!confirmRemove) return

    setNurses((prev) =>
      prev.filter(
        (item) =>
          item.id !== nurse.id
      )
    )
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

  const saveVitals = (e) => {
    e.preventDefault()

    if (!selectedHospital) return

    const patient =
      hospitalPatients.find(
        (item) =>
          item.id ===
          vitalForm.patientId
      )

    if (!patient) {
      alert("Select a patient.")
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
  // ADD NOTE
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
  // ADD ASSESSMENT
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
      nurse: profile.name,
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
  // MAR - GIVE MEDICINE
  // =====================================================

  const administerMedicine = (item) => {
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

    setMar((prev) =>
      prev.map((medicine) =>
        medicine.id === item.id
          ? {
            ...medicine,
            status: "Given",
            givenBy: profile.name,
          }
          : medicine
      )
    )
  }

  // =====================================================
  // BLOOD REQUEST
  // =====================================================

  const requestBlood = (item) => {
    if (!selectedHospital) return

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
  // TAB BUTTON
  // =====================================================

  const tabs = [
    {
      id: "home",
      label: "Home",
      icon: "🏠",
    },
    {
      id: "profile",
      label: "My Profile",
      icon: "👤",
    },
    {
      id: "patients",
      label: "Patients",
      icon: "🧑‍🤝‍🧑",
    },
    {
      id: "assessment",
      label: "Assessment",
      icon: "🩺",
    },
    {
      id: "vitals",
      label: "Vitals",
      icon: "❤️",
    },
    {
      id: "notes",
      label: "Notes",
      icon: "📝",
    },
    {
      id: "orders",
      label: "Orders",
      icon: "📋",
    },
    {
      id: "mar",
      label: "MAR",
      icon: "💊",
    },
    {
      id: "blood",
      label: "Blood",
      icon: "🩸",
    },
    {
      id: "discharge",
      label: "Discharge",
      icon: "🏥",
    },
    {
      id: "billing",
      label: "Billing",
      icon: "💰",
    },
    {
      id: "reports",
      label: "Reports",
      icon: "📊",
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
            🏥
          </div>

          <h1 className="text-2xl font-bold text-gray-800">
            Nurse Portal
          </h1>

          <p className="text-gray-500 mt-2">
            Please select a hospital to continue.
          </p>

        </div>

      </div>
    )
  }

  // =====================================================
  // MAIN
  // =====================================================

  return (
    <div className="p-6">

      {/* =================================================
          HEADER
      ================================================= */}

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">

        <div>

          <h1 className="text-2xl font-bold text-gray-800">
            Nurse Portal
          </h1>

          <p className="text-gray-500 mt-1">
            {selectedHospital.name}
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

          {isAdmin && (
            <button
              onClick={() =>
                setShowAddNurse(true)
              }
              className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-3 rounded-xl font-medium"
            >
              + Add Nurse
            </button>
          )}

        </div>

      </div>


      {/* =================================================
          HOSPITAL BANNER
      ================================================= */}

      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 mb-6">

        <p className="text-sm text-gray-500">
          Selected Hospital
        </p>

        <p className="font-semibold text-blue-700 mt-1">
          🏥 {selectedHospital.name}
        </p>

      </div>


      {/* =================================================
          NAVIGATION
      ================================================= */}

      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-3 mb-6 overflow-x-auto">

        <div className="flex gap-2 min-w-max">

          {tabs.map((tab) => (

            <button
              key={tab.id}
              onClick={() =>
                setActiveTab(tab.id)
              }
              className={`px-4 py-2.5 rounded-xl text-sm font-medium transition ${activeTab === tab.id
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
              icon="🧑‍🤝‍🧑"
              subtitle="Hospital patients"
            />

            <DashboardCard
              title="Vitals Recorded"
              value={
                hospitalVitals.length
              }
              icon="❤️"
              subtitle="Today's records"
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
              icon="📋"
              subtitle="Orders waiting"
            />

            <DashboardCard
              title="Pending MAR"
              value={
                hospitalMAR.filter(
                  (item) =>
                    item.status ===
                    "Pending"
                ).length
              }
              icon="💊"
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
              👩‍⚕️
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
              className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
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
            icon="🧑‍🤝‍🧑"
          />

          <ReportCard
            title="Vitals"
            value={reports.vitals}
            icon="❤️"
          />

          <ReportCard
            title="Assessments"
            value={reports.assessments}
            icon="🩺"
          />

          <ReportCard
            title="Orders"
            value={reports.orders}
            icon="📋"
          />

          <ReportCard
            title="MAR Records"
            value={reports.mar}
            icon="💊"
          />

          <ReportCard
            title="Blood Records"
            value={reports.blood}
            icon="🩸"
          />

          <ReportCard
            title="Billing Records"
            value={reports.billing}
            icon="💰"
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
                className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
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
                className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
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
        className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
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
        className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
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

export default Nurses