import { useState, useEffect, useCallback } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api"
import { AmbulanceIcon, HourglassIcon, TriangleAlertIcon } from "lucide-react"

function Emergency() {
  const { selectedHospital } = usePatient()

  const [visits, setVisits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState("active")
  const [dashboardStats, setDashboardStats] = useState({})

  const [showRegistrationForm, setShowRegistrationForm] = useState(false)
  const [showTriageForm, setShowTriageForm] = useState(false)
  const [showVitalsForm, setShowVitalsForm] = useState(false)
  const [showOrderForm, setShowOrderForm] = useState(false)
  const [showMedicationForm, setShowMedicationForm] = useState(false)

  const [selectedVisit, setSelectedVisit] = useState(null)
  const [visitVitals, setVisitVitals] = useState([])
  const [visitOrders, setVisitOrders] = useState([])
  const [visitMedications, setVisitMedications] = useState([])

  const [registrationForm, setRegistrationForm] = useState({
    patient: "",
    triage_level: "Non-Urgent",
    remarks: "",
    attending_doctor: "",
  })
  const [triageForm, setTriageForm] = useState({
    chief_complaint: "",
    pain_score: "",
    glasgow_coma_scale: "",
    triage_notes: "",
    triage_level: "Non-Urgent",
  })
  const [vitalsForm, setVitalsForm] = useState({
    temperature: "",
    systolic_bp: "",
    diastolic_bp: "",
    heart_rate: "",
    respiratory_rate: "",
    spo2: "",
    blood_sugar: "",
  })
  const [orderForm, setOrderForm] = useState({
    order_type: "Lab",
    description: "",
  })
  const [medicationForm, setMedicationForm] = useState({
    name: "",
    dose: "",
    route: "IV",
    frequency: "",
    duration: "",
  })

  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])
  const [nurses, setNurses] = useState([])

  const fetchData = useCallback(async () => {
    if (!selectedHospital) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const [visitsRes, patientsRes, doctorsRes, nursesRes, dashboardRes] = await Promise.all([
        api.emergency.visits.list(selectedHospital.id),
        api.patients.list(selectedHospital.id),
        api.doctors.list(selectedHospital.id),
        api.nurses.nurses.list(selectedHospital.id),
        api.emergency.visits.dashboard(selectedHospital.id),
      ])

      setVisits(visitsRes.results || visitsRes)
      setPatients(patientsRes.results || patientsRes)
      setDoctors(doctorsRes.results || doctorsRes)
      setNurses(nursesRes.results || nursesRes)
      setDashboardStats(dashboardRes || {})
    } catch (err) {
      setError(err.message || "Failed to load emergency data")
    } finally {
      setLoading(false)
    }
  }, [selectedHospital])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const fetchVisitDetails = async (visitId) => {
    try {
      const [visitRes, vitalsRes, ordersRes, medicationsRes] = await Promise.all([
        api.emergency.visits.get(visitId),
        api.emergency.vitals.list(selectedHospital.id, visitId),
        api.emergency.orders.list(selectedHospital.id, visitId),
        api.emergency.medications.list(selectedHospital.id, visitId),
      ])
      setSelectedVisit(visitRes)
      setVisitVitals(vitalsRes.results || vitalsRes)
      setVisitOrders(ordersRes.results || ordersRes)
      setVisitMedications(medicationsRes.results || medicationsRes)
    } catch (err) {
      console.error("Failed to fetch visit details:", err)
    }
  }

  const resetForms = () => {
    setRegistrationForm({ patient: "", triage_level: "Non-Urgent", remarks: "", attending_doctor: "" })
    setTriageForm({ chief_complaint: "", pain_score: "", glasgow_coma_scale: "", triage_notes: "", triage_level: "Non-Urgent" })
    setVitalsForm({ temperature: "", systolic_bp: "", diastolic_bp: "", heart_rate: "", respiratory_rate: "", spo2: "", blood_sugar: "" })
    setOrderForm({ order_type: "Lab", description: "" })
    setMedicationForm({ name: "", dose: "", route: "IV", frequency: "", duration: "" })
    setSelectedVisit(null)
    setVisitVitals([])
    setVisitOrders([])
    setVisitMedications([])
    setShowRegistrationForm(false)
    setShowTriageForm(false)
    setShowVitalsForm(false)
    setShowOrderForm(false)
    setShowMedicationForm(false)
  }

  const handleRegistration = async (e) => {
    e.preventDefault()
    if (!selectedHospital) return alert("Please select a hospital first.")

    const patientId = patients.find(p => p.name === registrationForm.patient)?.id
    const doctorId = doctors.find(d => d.name === registrationForm.attending_doctor)?.id

    try {
      await api.emergency.visits.create({
        patient: patientId,
        hospital: selectedHospital.id,
        triage_level: registrationForm.triage_level,
        remarks: registrationForm.remarks,
        attending_doctor: doctorId,
      })
      alert("Emergency visit registered")
      fetchData()
      resetForms()
    } catch (err) {
      alert(err.message || "Failed to register visit")
    }
  }

  const handleStartTriage = async (visit) => {
    setSelectedVisit(visit)
    setTriageForm(prev => ({ ...prev, triage_level: visit.triage_level }))
    setShowTriageForm(true)
  }

  const handleCompleteTriage = async (e) => {
    e.preventDefault()
    if (!selectedVisit) return

    try {
      await api.emergency.visits.completeTriage(selectedVisit.id, {
        chief_complaint: triageForm.chief_complaint,
        pain_score: triageForm.pain_score ? parseInt(triageForm.pain_score) : null,
        glasgow_coma_scale: triageForm.glasgow_coma_scale ? parseInt(triageForm.glasgow_coma_scale) : null,
        triage_notes: triageForm.triage_notes,
        triage_level: triageForm.triage_level,
        triaged_by: triageForm.triaged_by,
      })
      alert("Triage completed")
      fetchData()
      resetForms()
    } catch (err) {
      alert(err.message || "Failed to complete triage")
    }
  }

  const handleStartConsultation = async (visit) => {
    try {
      await api.emergency.visits.startConsultation(visit.id, { doctor_id: visit.attending_doctor })
      fetchData()
    } catch (err) {
      alert(err.message || "Failed to start consultation")
    }
  }

  const handleAddVitals = async (e) => {
    e.preventDefault()
    if (!selectedVisit) return

    try {
      await api.emergency.visits.addVitals(selectedVisit.id, {
        temperature: vitalsForm.temperature ? parseFloat(vitalsForm.temperature) : null,
        systolic_bp: vitalsForm.systolic_bp ? parseInt(vitalsForm.systolic_bp) : null,
        diastolic_bp: vitalsForm.diastolic_bp ? parseInt(vitalsForm.diastolic_bp) : null,
        heart_rate: vitalsForm.heart_rate ? parseInt(vitalsForm.heart_rate) : null,
        respiratory_rate: vitalsForm.respiratory_rate ? parseInt(vitalsForm.respiratory_rate) : null,
        spo2: vitalsForm.spo2 ? parseInt(vitalsForm.spo2) : null,
        blood_sugar: vitalsForm.blood_sugar ? parseFloat(vitalsForm.blood_sugar) : null,
        recorded_by: vitalsForm.recorded_by,
      })
      alert("Vitals recorded")
      fetchVisitDetails(selectedVisit.id)
      setShowVitalsForm(false)
    } catch (err) {
      alert(err.message || "Failed to record vitals")
    }
  }

  const handleAddOrder = async (e) => {
    e.preventDefault()
    if (!selectedVisit) return

    try {
      await api.emergency.visits.addOrder(selectedVisit.id, {
        order_type: orderForm.order_type,
        description: orderForm.description,
        ordered_by: orderForm.ordered_by,
      })
      alert("Order added")
      fetchVisitDetails(selectedVisit.id)
      setShowOrderForm(false)
    } catch (err) {
      alert(err.message || "Failed to add order")
    }
  }

  const handleAddMedication = async (e) => {
    e.preventDefault()
    if (!selectedVisit) return

    try {
      await api.emergency.visits.addMedication(selectedVisit.id, {
        name: medicationForm.name,
        dose: medicationForm.dose,
        route: medicationForm.route,
        frequency: medicationForm.frequency,
        duration: medicationForm.duration,
        prescribed_by: medicationForm.prescribed_by,
      })
      alert("Medication prescribed")
      fetchVisitDetails(selectedVisit.id)
      setShowMedicationForm(false)
    } catch (err) {
      alert(err.message || "Failed to prescribe medication")
    }
  }

  const handleAdmitToIpd = async (visit) => {
    // This would need bed selection - simplified for now
    alert("IPD Admission requires bed selection. Use IPD module for bed allocation.")
  }

  const handleDischarge = async (visit) => {
    const diagnosis = prompt("Discharge Diagnosis:")
    if (diagnosis === null) return

    const followup = prompt("Follow-up Instructions:")

    try {
      await api.emergency.visits.discharge(visit.id, {
        discharge_diagnosis: diagnosis,
        follow_up_instructions: followup || "",
      })
      alert("Patient discharged")
      fetchData()
    } catch (err) {
      alert(err.message || "Failed to discharge")
    }
  }

  const handleRefer = async (visit) => {
    const facility = prompt("Referred to facility:")
    if (facility === null) return

    const diagnosis = prompt("Discharge Diagnosis:")

    try {
      await api.emergency.visits.refer(visit.id, {
        referred_to: facility,
        discharge_diagnosis: diagnosis || "",
      })
      alert("Patient referred")
      fetchData()
    } catch (err) {
      alert(err.message || "Failed to refer")
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      "Registered": "bg-gray-100 text-gray-700",
      "Triage": "bg-purple-100 text-purple-700",
      "Waiting": "bg-yellow-100 text-yellow-700",
      "Under Consultation": "bg-blue-100 text-blue-700",
      "Investigations": "bg-indigo-100 text-indigo-700",
      "Treatment": "bg-green-100 text-green-700",
      "Observation": "bg-orange-100 text-orange-700",
      "Admitted": "bg-teal-100 text-teal-700",
      "Discharged": "bg-gray-100 text-gray-700",
      "Referred": "bg-pink-100 text-pink-700",
      "Left Against Advice": "bg-red-100 text-red-700",
      "Expired": "bg-black text-white",
    }
    return colors[status] || "bg-gray-100 text-gray-700"
  }

  const getTriageColor = (level) => {
    const colors = {
      "Critical": "bg-red-100 text-red-700",
      "Emergency": "bg-orange-100 text-orange-700",
      "Urgent": "bg-yellow-100 text-yellow-700",
      "Semi-Urgent": "bg-blue-100 text-blue-700",
      "Non-Urgent": "bg-green-100 text-green-700",
    }
    return colors[level] || "bg-gray-100 text-gray-700"
  }

  if (!selectedHospital) {
    return (
      <div className="p-6">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 text-center">
          <div className="text-5xl mb-4"><AmbulanceIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <h1 className="text-2xl font-bold text-gray-800">Emergency / ER</h1>
          <p className="text-gray-500 mt-2">Please select a hospital to continue.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 text-center">
          <div className="text-5xl mb-4"><HourglassIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <h1 className="text-2xl font-bold text-gray-800">Loading...</h1>
          <p className="text-gray-500 mt-2">Fetching emergency data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-2xl p-8 text-center">
          <div className="text-5xl mb-4"><TriangleAlertIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <h1 className="text-2xl font-bold text-red-800">Error</h1>
          <p className="text-red-600 mt-2">{error}</p>
          <button onClick={fetchData} className="mt-4 px-5 py-2.5 rounded-xl bg-red-600 text-white font-medium">Retry</button>
        </div>
      </div>
    )
  }

  const activeVisits = visits.filter(v => !["Discharged", "Admitted", "Referred", "Expired", "Left Against Advice"].includes(v.status))
  const completedVisits = visits.filter(v => ["Discharged", "Admitted", "Referred", "Expired", "Left Against Advice"].includes(v.status))

  return (
    <div className="p-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Emergency / ER</h1>
          <p className="text-gray-500 mt-1">Manage emergency visits, triage, and patient flow</p>
        </div>
        <button onClick={() => { resetForms(); setShowRegistrationForm(true); }} className="bg-red-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-red-700 transition">
          + New Emergency Visit
        </button>
      </div>

      {/* Dashboard Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <p className="text-sm text-gray-500">Active Patients</p>
          <h2 className="text-3xl font-bold text-red-600 mt-1">{activeVisits.length}</h2>
        </div>
        {Object.entries(dashboardStats.triage_counts || {}).slice(0, 4).map(([level, count]) => (
          <div key={level} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <p className="text-sm text-gray-500">{level}</p>
            <h2 className="text-3xl font-bold text-blue-600 mt-1">{count}</h2>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-6">
        <div className="flex gap-4 overflow-x-auto">
          {["active", "completed", "triage"].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition whitespace-nowrap ${activeTab === tab ? "bg-red-600 text-white" : "text-gray-600 hover:bg-gray-100"}`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "active" && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Visit #</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Patient</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Triage</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Status</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Arrival</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Doctor</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeVisits.length === 0 ? (
                  <tr><td colSpan="7" className="text-center py-12 text-gray-500">No active emergency visits</td></tr>
                ) : (
                  activeVisits.map(visit => (
                    <tr key={visit.id} className="border-t hover:bg-gray-50">
                      <td className="px-6 py-4 font-semibold text-red-600">{visit.visit_number}</td>
                      <td className="px-6 py-4">
                        <p className="font-semibold text-gray-800">{visit.patient_name}</p>
                        <p className="text-xs text-gray-500">{visit.patient?.age} yrs • {visit.patient?.gender}</p>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getTriageColor(visit.triage_level)}`}>{visit.triage_level}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(visit.status)}`}>{visit.status}</span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{new Date(visit.arrival_time).toLocaleTimeString()}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{visit.attending_doctor_name || "-"}</td>
                      <td className="px-6 py-4">
                        <div className="flex gap-1 flex-wrap">
                          {visit.status === "Registered" && <button onClick={() => handleStartTriage(visit)} className="px-2 py-1 text-xs bg-purple-50 text-purple-700 rounded">Triage</button>}
                          {visit.status === "Triage" && <button onClick={() => handleCompleteTriage} disabled className="px-2 py-1 text-xs bg-yellow-50 text-yellow-700 rounded">Complete Triage</button>}
                          {visit.status === "Waiting" && <button onClick={() => handleStartConsultation(visit)} className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded">Consult</button>}
                          {(["Under Consultation", "Investigations", "Treatment", "Observation"].includes(visit.status)) && (
                            <>
                              <button onClick={() => { fetchVisitDetails(visit.id); setShowVitalsForm(true); }} className="px-2 py-1 text-xs bg-green-50 text-green-700 rounded">Vitals</button>
                              <button onClick={() => { fetchVisitDetails(visit.id); setShowOrderForm(true); }} className="px-2 py-1 text-xs bg-indigo-50 text-indigo-700 rounded">Orders</button>
                              <button onClick={() => { fetchVisitDetails(visit.id); setShowMedicationForm(true); }} className="px-2 py-1 text-xs bg-pink-50 text-pink-700 rounded">Meds</button>
                            </>
                          )}
                          {["Under Consultation", "Investigations", "Treatment", "Observation"].includes(visit.status) && (
                            <button onClick={() => handleDischarge(visit)} className="px-2 py-1 text-xs bg-gray-50 text-gray-700 rounded">Discharge</button>
                          )}
                          {["Under Consultation", "Investigations", "Treatment", "Observation"].includes(visit.status) && (
                            <button onClick={() => handleRefer(visit)} className="px-2 py-1 text-xs bg-pink-50 text-pink-700 rounded">Refer</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "completed" && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Visit #</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Patient</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Final Status</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Disposition</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Arrival</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Discharge</th>
                </tr>
              </thead>
              <tbody>
                {completedVisits.map(visit => (
                  <tr key={visit.id} className="border-t hover:bg-gray-50">
                    <td className="px-6 py-4 font-semibold text-red-600">{visit.visit_number}</td>
                    <td className="px-6 py-4">{visit.patient_name}</td>
                    <td className="px-6 py-4"><span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(visit.status)}`}>{visit.status}</span></td>
                    <td className="px-6 py-4 text-sm text-gray-600">{visit.disposition || "-"}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{new Date(visit.arrival_time).toLocaleString()}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{visit.discharge_time ? new Date(visit.discharge_time).toLocaleString() : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "triage" && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Visit #</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Patient</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Triage Level</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Chief Complaint</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Triage Time</th>
                </tr>
              </thead>
              <tbody>
                {visits.filter(v => v.triage).map(visit => (
                  <tr key={visit.id} className="border-t hover:bg-gray-50">
                    <td className="px-6 py-4 font-semibold text-red-600">{visit.visit_number}</td>
                    <td className="px-6 py-4">{visit.patient_name}</td>
                    <td className="px-6 py-4"><span className={`px-3 py-1 rounded-full text-xs font-medium ${getTriageColor(visit.triage_level)}`}>{visit.triage_level}</span></td>
                    <td className="px-6 py-4 text-sm text-gray-600">{visit.triage?.chief_complaint || "-"}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{visit.triage_time ? new Date(visit.triage_time).toLocaleString() : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Registration Modal */}
      {showRegistrationForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">New Emergency Visit</h2>
              <button onClick={resetForms} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleRegistration} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Patient *</label>
                <select name="patient" value={registrationForm.patient} onChange={e => setRegistrationForm({...registrationForm, patient: e.target.value})} required className="hms-input w-full">
                  <option value="">Select Patient</option>
                  {patients.map(p => <option key={p.id} value={p.name}>{p.name} ({p.age} yrs, {p.gender})</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Triage Level *</label>
                <select name="triage_level" value={registrationForm.triage_level} onChange={e => setRegistrationForm({...registrationForm, triage_level: e.target.value})} className="hms-input w-full">
                  <option value="Critical">Critical - Immediate</option>
                  <option value="Emergency">Emergency - &lt; 15 min</option>
                  <option value="Urgent">Urgent - &lt; 30 min</option>
                  <option value="Semi-Urgent">Semi-Urgent - &lt; 60 min</option>
                  <option value="Non-Urgent">Non-Urgent - &lt; 120 min</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Attending Doctor</label>
                <select name="attending_doctor" value={registrationForm.attending_doctor} onChange={e => setRegistrationForm({...registrationForm, attending_doctor: e.target.value})} className="hms-input w-full">
                  <option value="">Select Doctor</option>
                  {doctors.map(d => <option key={d.id} value={d.name}>{d.name} - {d.specialization}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Remarks</label>
                <textarea name="remarks" value={registrationForm.remarks} onChange={e => setRegistrationForm({...registrationForm, remarks: e.target.value})} rows={2} className="hms-input w-full" placeholder="Additional notes..." />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={resetForms} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-red-600 text-white rounded-xl hover:bg-red-700">Register Visit</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Triage Modal */}
      {showTriageForm && selectedVisit && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">Complete Triage - {selectedVisit.visit_number}</h2>
              <button onClick={resetForms} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleCompleteTriage} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Chief Complaint *</label>
                <textarea name="chief_complaint" value={triageForm.chief_complaint} onChange={e => setTriageForm({...triageForm, chief_complaint: e.target.value})} rows={3} required className="hms-input w-full" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Pain Score (0-10)</label>
                  <input type="number" name="pain_score" value={triageForm.pain_score} onChange={e => setTriageForm({...triageForm, pain_score: e.target.value})} min="0" max="10" className="hms-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Glasgow Coma Scale</label>
                  <input type="number" name="glasgow_coma_scale" value={triageForm.glasgow_coma_scale} onChange={e => setTriageForm({...triageForm, glasgow_coma_scale: e.target.value})} min="3" max="15" className="hms-input w-full" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Triage Level *</label>
                <select name="triage_level" value={triageForm.triage_level} onChange={e => setTriageForm({...triageForm, triage_level: e.target.value})} className="hms-input w-full">
                  <option value="Critical">Critical - Immediate</option>
                  <option value="Emergency">Emergency - &lt; 15 min</option>
                  <option value="Urgent">Urgent - &lt; 30 min</option>
                  <option value="Semi-Urgent">Semi-Urgent - &lt; 60 min</option>
                  <option value="Non-Urgent">Non-Urgent - &lt; 120 min</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Triage Notes</label>
                <textarea name="triage_notes" value={triageForm.triage_notes} onChange={e => setTriageForm({...triageForm, triage_notes: e.target.value})} rows={3} className="hms-input w-full" />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={resetForms} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700">Complete Triage</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Vitals Modal */}
      {showVitalsForm && selectedVisit && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">Record Vitals - {selectedVisit.visit_number}</h2>
              <button onClick={() => setShowVitalsForm(false)} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleAddVitals} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Temperature (°C)</label>
                  <input type="number" step="0.1" name="temperature" value={vitalsForm.temperature} onChange={e => setVitalsForm({...vitalsForm, temperature: e.target.value})} className="hms-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">BP Systolic</label>
                  <input type="number" name="systolic_bp" value={vitalsForm.systolic_bp} onChange={e => setVitalsForm({...vitalsForm, systolic_bp: e.target.value})} className="hms-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">BP Diastolic</label>
                  <input type="number" name="diastolic_bp" value={vitalsForm.diastolic_bp} onChange={e => setVitalsForm({...vitalsForm, diastolic_bp: e.target.value})} className="hms-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Heart Rate</label>
                  <input type="number" name="heart_rate" value={vitalsForm.heart_rate} onChange={e => setVitalsForm({...vitalsForm, heart_rate: e.target.value})} className="hms-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Resp. Rate</label>
                  <input type="number" name="respiratory_rate" value={vitalsForm.respiratory_rate} onChange={e => setVitalsForm({...vitalsForm, respiratory_rate: e.target.value})} className="hms-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SpO₂ %</label>
                  <input type="number" name="spo2" value={vitalsForm.spo2} onChange={e => setVitalsForm({...vitalsForm, spo2: e.target.value})} min="0" max="100" className="hms-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Blood Sugar</label>
                  <input type="number" step="0.1" name="blood_sugar" value={vitalsForm.blood_sugar} onChange={e => setVitalsForm({...vitalsForm, blood_sugar: e.target.value})} className="hms-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Recorded By (Nurse ID)</label>
                  <input type="text" name="recorded_by" value={vitalsForm.recorded_by} onChange={e => setVitalsForm({...vitalsForm, recorded_by: e.target.value})} className="hms-input w-full" />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => setShowVitalsForm(false)} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700">Save Vitals</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Order Modal */}
      {showOrderForm && selectedVisit && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">Add Order - {selectedVisit.visit_number}</h2>
              <button onClick={() => setShowOrderForm(false)} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleAddOrder} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Order Type *</label>
                <select name="order_type" value={orderForm.order_type} onChange={e => setOrderForm({...orderForm, order_type: e.target.value})} required className="hms-input w-full">
                  <option value="Lab">Lab Investigation</option>
                  <option value="Imaging">Imaging</option>
                  <option value="Medication">Medication</option>
                  <option value="Procedure">Procedure</option>
                  <option value="Consultation">Specialist Consultation</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
                <textarea name="description" value={orderForm.description} onChange={e => setOrderForm({...orderForm, description: e.target.value})} rows={3} required className="hms-input w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ordered By (Doctor ID)</label>
                <input type="text" name="ordered_by" value={orderForm.ordered_by} onChange={e => setOrderForm({...orderForm, ordered_by: e.target.value})} className="hms-input w-full" />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => setShowOrderForm(false)} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700">Add Order</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Medication Modal */}
      {showMedicationForm && selectedVisit && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">Prescribe Medication - {selectedVisit.visit_number}</h2>
              <button onClick={() => setShowMedicationForm(false)} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleAddMedication} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Medication Name *</label>
                <input type="text" name="name" value={medicationForm.name} onChange={e => setMedicationForm({...medicationForm, name: e.target.value})} required className="hms-input w-full" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Dose *</label>
                  <input type="text" name="dose" value={medicationForm.dose} onChange={e => setMedicationForm({...medicationForm, dose: e.target.value})} required className="hms-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Route *</label>
                  <select name="route" value={medicationForm.route} onChange={e => setMedicationForm({...medicationForm, route: e.target.value})} className="hms-input w-full">
                    <option value="IV">IV</option>
                    <option value="IM">IM</option>
                    <option value="PO">PO</option>
                    <option value="SC">SC</option>
                    <option value="PR">PR</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Frequency *</label>
                  <input type="text" name="frequency" value={medicationForm.frequency} onChange={e => setMedicationForm({...medicationForm, frequency: e.target.value})} required className="hms-input w-full" placeholder="e.g., Q8H, BID" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Duration</label>
                  <input type="text" name="duration" value={medicationForm.duration} onChange={e => setMedicationForm({...medicationForm, duration: e.target.value})} className="hms-input w-full" placeholder="e.g., 5 days" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Prescribed By (Doctor ID)</label>
                <input type="text" name="prescribed_by" value={medicationForm.prescribed_by} onChange={e => setMedicationForm({...medicationForm, prescribed_by: e.target.value})} className="hms-input w-full" />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => setShowMedicationForm(false)} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-pink-600 text-white rounded-xl hover:bg-pink-700">Prescribe</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Emergency