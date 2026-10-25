import { useState, useEffect, useCallback } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api"
import { HospitalIcon, HourglassIcon, TriangleAlertIcon } from "lucide-react"

function IPD() {
  const { selectedHospital } = usePatient()

  const [admissions, setAdmissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState("admissions")
  const [beds, setBeds] = useState([])
  const [availableBeds, setAvailableBeds] = useState([])

  const [showAdmissionForm, setShowAdmissionForm] = useState(false)
  const [showBedAllocationForm, setShowBedAllocationForm] = useState(false)
  const [showDischargeForm, setShowDischargeForm] = useState(false)
  const [showDischargePlanForm, setShowDischargePlanForm] = useState(false)
  const [showDischargeSummaryForm, setShowDischargeSummaryForm] = useState(false)

  const [selectedAdmission, setSelectedAdmission] = useState(null)
  const [admissionForm, setAdmissionForm] = useState({
    patient: "",
    reason: "",
    admitting_doctor: "",
  })
  const [bedAllocationForm, setBedAllocationForm] = useState({
    admission_id: "",
    bed_id: "",
  })
  const [dischargeForm, setDischargeForm] = useState({
    admission_id: "",
    summary: "",
    authorized_doctor: "",
    instructions: "",
    pending_tasks: "",
  })

  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])

  const fetchData = useCallback(async () => {
    if (!selectedHospital) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const [admissionsRes, patientsRes, doctorsRes] = await Promise.all([
        api.ipd.admissions.list(selectedHospital.id),
        api.patients.list(selectedHospital.id),
        api.doctors.list(selectedHospital.id),
      ])

      setAdmissions(admissionsRes.results || admissionsRes)
      setPatients(patientsRes.results || patientsRes)
      setDoctors(doctorsRes.results || doctorsRes)

      // Fetch available beds
      const bedsRes = await api.ipd.bedAllocations.availableBeds(selectedHospital.id)
      setAvailableBeds(bedsRes || [])
    } catch (err) {
      setError(err.message || "Failed to load IPD data")
    } finally {
      setLoading(false)
    }
  }, [selectedHospital])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const resetForms = () => {
    setAdmissionForm({ patient: "", reason: "", admitting_doctor: "" })
    setBedAllocationForm({ admission_id: "", bed_id: "" })
    setDischargeForm({ admission_id: "", summary: "", authorized_doctor: "", instructions: "", pending_tasks: "" })
    setSelectedAdmission(null)
    setShowAdmissionForm(false)
    setShowBedAllocationForm(false)
    setShowDischargeForm(false)
    setShowDischargePlanForm(false)
    setShowDischargeSummaryForm(false)
  }

  const handleAdmissionSubmit = async (e) => {
    e.preventDefault()
    if (!selectedHospital) return alert("Please select a hospital first.")

    const patientId = patients.find(p => p.name === admissionForm.patient)?.id
    const doctorId = doctors.find(d => d.name === admissionForm.admitting_doctor)?.id

    try {
      const data = await api.ipd.admissions.create({
        patient: patientId,
        hospital: selectedHospital.id,
        reason: admissionForm.reason,
        admitting_doctor: doctorId,
      })
      setAdmissions(prev => [data, ...prev])
      resetForms()
      alert("Admission created successfully")
    } catch (err) {
      alert(err.message || "Failed to create admission")
    }
  }

  const handleBedAllocation = async (e) => {
    e.preventDefault()
    if (!selectedAdmission) return

    try {
      await api.ipd.admissions.allocateBed(selectedAdmission.id, bedAllocationForm.bed_id)
      alert("Bed allocated successfully")
      fetchData()
      resetForms()
    } catch (err) {
      alert(err.message || "Failed to allocate bed")
    }
  }

  const handleReleaseBed = async (admission) => {
    if (!window.confirm(`Release bed for ${admission.patient_name}?`)) return

    try {
      await api.ipd.admissions.releaseBed(admission.id)
      alert("Bed released successfully")
      fetchData()
    } catch (err) {
      alert(err.message || "Failed to release bed")
    }
  }

  const handleInitiateDischarge = async (admission) => {
    setSelectedAdmission(admission)
    setDischargeForm(prev => ({ ...prev, admission_id: admission.id }))
    setShowDischargePlanForm(true)
  }

  const handleDischargePlanSubmit = async (e) => {
    e.preventDefault()

    try {
      await api.ipd.dischargePlans.create({
        admission: dischargeForm.admission_id,
        instructions: dischargeForm.instructions,
        pending_tasks: dischargeForm.pending_tasks,
      })
      await api.ipd.admissions.initiateDischarge(dischargeForm.admission_id)
      alert("Discharge initiated")
      fetchData()
      resetForms()
    } catch (err) {
      alert(err.message || "Failed to initiate discharge")
    }
  }

  const handleCompleteDischarge = async (admission) => {
    if (!window.confirm(`Complete discharge for ${admission.patient_name}? This will release the bed.`)) return

    try {
      await api.ipd.admissions.completeDischarge(admission.id)
      alert("Discharge completed, bed released")
      fetchData()
    } catch (err) {
      alert(err.message || "Failed to complete discharge")
    }
  }

  const handleDischargeSummarySubmit = async (e) => {
    e.preventDefault()

    try {
      await api.ipd.dischargeSummaries.create({
        admission: dischargeForm.admission_id,
        summary: dischargeForm.summary,
        authorized_doctor: doctors.find(d => d.name === dischargeForm.authorized_doctor)?.id,
      })
      alert("Discharge summary created")
      resetForms()
    } catch (err) {
      alert(err.message || "Failed to create discharge summary")
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      "Admitted": "bg-green-100 text-green-700",
      "Discharge Initiated": "bg-yellow-100 text-yellow-700",
      "Discharged": "bg-gray-100 text-gray-700",
      "Transferred": "bg-blue-100 text-blue-700",
      "Cancelled": "bg-red-100 text-red-700",
    }
    return colors[status] || "bg-gray-100 text-gray-700"
  }

  if (!selectedHospital) {
    return (
      <div className="p-6">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 text-center">
          <div className="text-5xl mb-4"><HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <h1 className="text-2xl font-bold text-gray-800">IPD Management</h1>
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
          <p className="text-gray-500 mt-2">Fetching IPD data...</p>
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
          <button onClick={fetchData} className="mt-4 px-5 py-2.5 rounded-xl bg-red-600 text-white font-medium">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">IPD Management</h1>
          <p className="text-gray-500 mt-1">Manage admissions, bed allocations, and discharges</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => { setShowAdmissionForm(true); resetForms(); setSelectedAdmission(null); }} className="bg-blue-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-blue-700 transition">
            + New Admission
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-4 mb-6">
        <div className="flex gap-4">
          {["admissions", "beds", "discharges"].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition ${activeTab === tab ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"}`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "admissions" && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b">
            <h2 className="text-xl font-bold text-gray-800">Admissions</h2>
            <p className="text-sm text-gray-500 mt-1">{admissions.length} admission(s)</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Patient</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Admission Date</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Doctor</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Reason</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Status</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Bed</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody>
                {admissions.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="text-center py-12 text-gray-500">No admissions found</td>
                  </tr>
                ) : (
                  admissions.map(admission => (
                    <tr key={admission.id} className="border-t hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <p className="font-semibold text-gray-800">{admission.patient_name}</p>
                        <p className="text-xs text-gray-500">{admission.id}</p>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {new Date(admission.admission_date).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {admission.admitting_doctor_name || "-"}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">
                        {admission.reason || "-"}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(admission.status)}`}>
                          {admission.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {admission.current_bed ? `${admission.current_bed.ward_name} - ${admission.current_bed.room_number} - ${admission.current_bed.bed_number}` : "Not allocated"}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2 flex-wrap">
                          {!admission.current_bed && admission.status === "Admitted" && (
                            <button onClick={() => { setSelectedAdmission(admission); setBedAllocationForm({ admission_id: admission.id, bed_id: "" }); setShowBedAllocationForm(true); }} className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg">Allocate Bed</button>
                          )}
                          {admission.current_bed && (
                            <button onClick={() => handleReleaseBed(admission)} className="px-3 py-2 text-sm bg-orange-50 text-orange-700 rounded-lg">Release Bed</button>
                          )}
                          {admission.status === "Admitted" && (
                            <button onClick={() => handleInitiateDischarge(admission)} className="px-3 py-2 text-sm bg-yellow-50 text-yellow-700 rounded-lg">Initiate Discharge</button>
                          )}
                          {admission.status === "Discharge Initiated" && (
                            <button onClick={() => handleCompleteDischarge(admission)} className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg">Complete Discharge</button>
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

      {activeTab === "beds" && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b">
            <h2 className="text-xl font-bold text-gray-800">Bed Management</h2>
            <p className="text-sm text-gray-500 mt-1">{availableBeds.length} available bed(s)</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Ward</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Room</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Bed Number</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Room Type</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody>
                {availableBeds.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="text-center py-12 text-gray-500">No available beds</td>
                  </tr>
                ) : (
                  availableBeds.map(bed => (
                    <tr key={bed.id} className="border-t hover:bg-gray-50">
                      <td className="px-6 py-4">{bed.ward}</td>
                      <td className="px-6 py-4">{bed.room}</td>
                      <td className="px-6 py-4 font-semibold text-blue-600">{bed.bed_number}</td>
                      <td className="px-6 py-4 text-gray-600">{bed.room_type || "-"}</td>
                      <td className="px-6 py-4"><span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">Available</span></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "discharges" && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b">
            <h2 className="text-xl font-bold text-gray-800">Pending Discharges</h2>
            <p className="text-sm text-gray-500 mt-1">
              {admissions.filter(a => a.status === "Discharge Initiated").length} discharge(s) in progress
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Patient</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Admission Date</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Bed</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody>
                {admissions.filter(a => a.status === "Discharge Initiated").length === 0 ? (
                  <tr>
                    <td colSpan="4" className="text-center py-12 text-gray-500">No pending discharges</td>
                  </tr>
                ) : (
                  admissions.filter(a => a.status === "Discharge Initiated").map(admission => (
                    <tr key={admission.id} className="border-t hover:bg-gray-50">
                      <td className="px-6 py-4 font-semibold text-gray-800">{admission.patient_name}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{new Date(admission.admission_date).toLocaleDateString()}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {admission.current_bed ? `${admission.current_bed.ward_name} - ${admission.current_bed.bed_number}` : "Not allocated"}
                      </td>
                      <td className="px-6 py-4">
                        <button onClick={() => handleCompleteDischarge(admission)} className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg">Complete</button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Admission Modal */}
      {showAdmissionForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">New Admission</h2>
              <button onClick={resetForms} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleAdmissionSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Patient *</label>
                <select name="patient" value={admissionForm.patient} onChange={e => setAdmissionForm({...admissionForm, patient: e.target.value})} required className="hms-input w-full">
                  <option value="">Select Patient</option>
                  {patients.map(p => <option key={p.id} value={p.name}>{p.name} ({p.age} yrs)</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Admitting Doctor</label>
                <select name="admitting_doctor" value={admissionForm.admitting_doctor} onChange={e => setAdmissionForm({...admissionForm, admitting_doctor: e.target.value})} className="hms-input w-full">
                  <option value="">Select Doctor</option>
                  {doctors.map(d => <option key={d.id} value={d.name}>{d.name} - {d.specialization}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason for Admission</label>
                <textarea name="reason" value={admissionForm.reason} onChange={e => setAdmissionForm({...admissionForm, reason: e.target.value})} rows={3} className="hms-input w-full" placeholder="Enter reason..." />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={resetForms} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700">Create Admission</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bed Allocation Modal */}
      {showBedAllocationForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">Allocate Bed</h2>
              <button onClick={resetForms} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleBedAllocation} className="p-6 space-y-4">
              <p className="text-gray-600">Allocating bed for <strong>{selectedAdmission?.patient_name}</strong></p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Available Bed *</label>
                <select name="bed_id" value={bedAllocationForm.bed_id} onChange={e => setBedAllocationForm({...bedAllocationForm, bed_id: e.target.value})} required className="hms-input w-full">
                  <option value="">Select Bed</option>
                  {availableBeds.map(bed => <option key={bed.id} value={bed.id}>{bed.ward} - {bed.room} - {bed.bed_number} ({bed.room_type})</option>)}
                </select>
                {availableBeds.length === 0 && <p className="text-sm text-red-500 mt-1">No available beds</p>}
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={resetForms} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700">Allocate</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Discharge Plan Modal */}
      {showDischargePlanForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">Initiate Discharge</h2>
              <button onClick={resetForms} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleDischargePlanSubmit} className="p-6 space-y-4">
              <p className="text-gray-600">Initiating discharge for <strong>{selectedAdmission?.patient_name}</strong></p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Instructions</label>
                <textarea name="instructions" value={dischargeForm.instructions} onChange={e => setDischargeForm({...dischargeForm, instructions: e.target.value})} rows={3} className="hms-input w-full" placeholder="Discharge instructions..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Pending Tasks</label>
                <textarea name="pending_tasks" value={dischargeForm.pending_tasks} onChange={e => setDischargeForm({...dischargeForm, pending_tasks: e.target.value})} rows={3} className="hms-input w-full" placeholder="Pending tasks before discharge..." />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={resetForms} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-yellow-600 text-white rounded-xl hover:bg-yellow-700">Initiate Discharge</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Discharge Summary Modal */}
      {showDischargeSummaryForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">Discharge Summary</h2>
              <button onClick={resetForms} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleDischargeSummarySubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Summary *</label>
                <textarea name="summary" value={dischargeForm.summary} onChange={e => setDischargeForm({...dischargeForm, summary: e.target.value})} rows={4} required className="hms-input w-full" placeholder="Clinical summary..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Authorized Doctor</label>
                <select name="authorized_doctor" value={dischargeForm.authorized_doctor} onChange={e => setDischargeForm({...dischargeForm, authorized_doctor: e.target.value})} required className="hms-input w-full">
                  <option value="">Select Doctor</option>
                  {doctors.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={resetForms} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700">Save Summary</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default IPD