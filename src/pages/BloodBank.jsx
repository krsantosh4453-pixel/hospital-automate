import React, { useState, useEffect } from 'react';
import { usePatient } from '../assets/context/PatientContext.jsx';
import api from '../services/api';

const BloodBank = () => {
  const { selectedHospital } = usePatient();
  const [inventory, setInventory] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [editingRequest, setEditingRequest] = useState(null);
  const [requestForm, setRequestForm] = useState({
    patientId: '',
    bloodGroup: '',
    component: 'Whole Blood',
    units: 1,
    urgency: 'Routine',
    reason: '',
  });

  const fetchData = async () => {
    if (!selectedHospital) {
      setInventory([]);
      setRequests([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError("");
    try {
      const [invRes, reqRes] = await Promise.all([
        api.get(`/bloodbank/inventory/?hospital=${selectedHospital.id}`),
        api.get(`/bloodbank/requests/?hospital=${selectedHospital.id}`),
      ]);
      setInventory(invRes.data.results || invRes.data);
      setRequests(reqRes.data.results || reqRes.data);
    } catch (err) {
      setLoadError("Failed to load blood bank data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedHospital]);

  const handleRequestSubmit = async (e) => {
    e.preventDefault();
    if (!selectedHospital) return;
    try {
      const url = editingRequest
        ? `/bloodbank/requests/${editingRequest.id}/?hospital=${selectedHospital.id}`
        : `/bloodbank/requests/?hospital=${selectedHospital.id}`;
      const method = editingRequest ? 'put' : 'post';
      await api[method](url, requestForm);
      setShowRequestModal(false);
      setEditingRequest(null);
      setRequestForm({
        patientId: '',
        bloodGroup: '',
        component: 'Whole Blood',
        units: 1,
        urgency: 'Routine',
        reason: '',
      });
      fetchData();
    } catch (error) {
      // Error handling
    }
  };

  const handleEdit = (req) => {
    setEditingRequest(req);
    setRequestForm({
      patientId: req.patient || '',
      bloodGroup: req.bloodGroup || '',
      component: req.component || 'Whole Blood',
      units: req.unitsRequested || 1,
      urgency: req.urgency || 'Routine',
      reason: req.reason || '',
    });
    setShowRequestModal(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this request?")) return;
    if (!selectedHospital) return;
    try {
      await api.delete(`/bloodbank/requests/${id}/?hospital=${selectedHospital.id}`);
      fetchData();
    } catch (error) {
      // Error handling
    }
  };

  const resetForms = () => {
    setEditingRequest(null);
    setRequestForm({
      patientId: '',
      bloodGroup: '',
      component: 'Whole Blood',
      units: 1,
      urgency: 'Routine',
      reason: '',
    });
    setShowRequestModal(false);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Blood Bank</h1>
        <button
          onClick={() => { setEditingRequest(null); setShowRequestModal(true); }}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        >
          New Request
        </button>
      </div>

      {loadError && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 rounded">{loadError}</div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-3">Inventory</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th className="pb-2">Blood Group</th>
                  <th className="pb-2">Component</th>
                  <th className="pb-2">Units</th>
                  <th className="pb-2">Expiry</th>
                </tr>
              </thead>
              <tbody>
                {inventory.map((item) => (
                  <tr key={item.id} className="border-t">
                    <td className="py-2">{item.bloodGroup}</td>
                    <td className="py-2">{item.component}</td>
                    <td className="py-2">{item.unitsAvailable}</td>
                    <td className="py-2">{item.expiryDate ? item.expiryDate.split('T')[0] : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-3">Requests</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th className="pb-2">Patient</th>
                  <th className="pb-2">Blood Group</th>
                  <th className="pb-2">Component</th>
                  <th className="pb-2">Units</th>
                  <th className="pb-2">Urgency</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((req) => (
                  <tr key={req.id} className="border-t">
                    <td className="py-2">{req.patientName || req.patient || '-'}</td>
                    <td className="py-2">{req.bloodGroup}</td>
                    <td className="py-2">{req.component}</td>
                    <td className="py-2">{req.unitsRequested}</td>
                    <td className="py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        req.urgency === 'Stat' ? 'bg-red-100 text-red-700' :
                        req.urgency === 'Urgent' ? 'bg-orange-100 text-orange-700' :
                        'bg-green-100 text-green-700'
                      }`}>{req.urgency}</span>
                    </td>
                    <td className="py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        req.status === 'Approved' ? 'bg-green-100 text-green-700' :
                        req.status === 'Pending' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>{req.status}</span>
                    </td>
                    <td className="py-2">
                      <button onClick={() => handleEdit(req)} className="text-blue-600 hover:underline mr-2">Edit</button>
                      <button onClick={() => handleDelete(req.id)} className="text-red-600 hover:underline">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showRequestModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">{editingRequest ? 'Edit' : 'New'} Blood Request</h2>
            <form onSubmit={handleRequestSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Patient ID</label>
                <input
                  type="text"
                  value={requestForm.patientId}
                  onChange={(e) => setRequestForm({...requestForm, patientId: e.target.value})}
                  className="hms-input w-full"
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Blood Group</label>
                <select
                  value={requestForm.bloodGroup}
                  onChange={(e) => setRequestForm({...requestForm, bloodGroup: e.target.value})}
                  className="hms-input w-full"
                  required
                >
                  <option value="">Select</option>
                  <option value="A+">A+</option>
                  <option value="A-">A-</option>
                  <option value="B+">B+</option>
                  <option value="B-">B-</option>
                  <option value="AB+">AB+</option>
                  <option value="AB-">AB-</option>
                  <option value="O+">O+</option>
                  <option value="O-">O-</option>
                </select>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Component</label>
                <select
                  value={requestForm.component}
                  onChange={(e) => setRequestForm({...requestForm, component: e.target.value})}
                  className="hms-input w-full"
                >
                  <option value="Whole Blood">Whole Blood</option>
                  <option value="Packed Red Cells">Packed Red Cells</option>
                  <option value="Platelets">Platelets</option>
                  <option value="Plasma">Plasma</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Units</label>
                  <input
                    type="number"
                    min="1"
                    value={requestForm.units}
                    onChange={(e) => setRequestForm({...requestForm, units: parseInt(e.target.value) || 1})}
                    className="hms-input w-full"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Urgency</label>
                  <select
                    value={requestForm.urgency}
                    onChange={(e) => setRequestForm({...requestForm, urgency: e.target.value})}
                    className="hms-input w-full"
                  >
                    <option value="Routine">Routine</option>
                    <option value="Urgent">Urgent</option>
                    <option value="Stat">Stat</option>
                  </select>
                </div>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Reason</label>
                <textarea
                  value={requestForm.reason}
                  onChange={(e) => setRequestForm({...requestForm, reason: e.target.value})}
                  className="hms-input w-full"
                  rows={2}
                />
              </div>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={resetForms} className="px-4 py-2 border rounded">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default BloodBank;
