import { BrowserRouter, Route, Routes } from "react-router-dom"

import Layout from "./layouts/layout.jsx"
import PatientLayout from "./layouts/PatientLayout.jsx"

import Home from "./pages/Home.jsx"
import Patients from "./pages/Patients.jsx"
import Appointments from "./pages/Appointments.jsx"
import Queue from "./pages/queue.jsx"
import Doctors from "./pages/doctors.jsx"
import Nurses from "./pages/Nurses.jsx"
import Compounter from "./pages/Compounter.jsx"
import Consultation from "./pages/Consultation.jsx"
import Prescription from "./pages/Prescription.jsx"
import Pharmacy from "./pages/pharmacy.jsx"
import Laboratory from "./pages/laboratory.jsx"
import Billing from "./pages/billing.jsx"
import Inventory from "./pages/inventory.jsx"
import Reports from "./pages/reports.jsx"
import Settings from "./pages/settings.jsx"

import StaffLogin from "./pages/StaffLogin.jsx"
import PatientLogin from "./pages/PatientLogin.jsx"
import HospitalSelection from "./pages/HospitalSelection.jsx"

import { AuthProvider } from "./assets/context/AuthContext.jsx"
import { PatientProvider } from "./assets/context/PatientContext.jsx"
import { PrescriptionProvider } from "./assets/context/PrescriptionContext.jsx"
import { PharmacyProvider } from "./assets/context/PharmacyContext.jsx"
import { HospitalsProvider } from "./assets/context/HospitalsContext.jsx"
import { SidebarProvider } from "./assets/context/SidebarContext.jsx"
import { RoleProvider } from "./assets/context/RoleContext.jsx"

import Emergency from "./pages/Emergency.jsx"
import BloodBank from "./pages/BloodBank.jsx"
import IPD from "./pages/IPD.jsx"
import AIScribe from "./pages/AIScribe.jsx"

import AdminDashboard from "./pages/admin/AdminDashboard.jsx"
import Users from "./pages/admin/Users.jsx"
import Roles from "./pages/admin/Roles.jsx"
import Hospitals from "./pages/admin/Hospitals.jsx"
import Departments from "./pages/admin/Departments.jsx"
import Permissions from "./pages/admin/Permissions.jsx"

import PatientDashboard from "./pages/patient/PatientDashboard.jsx"
import PatientAppointments from "./pages/patient/PatientAppointments.jsx"
import PatientQueue from "./pages/patient/PatientQueue.jsx"
import PatientPrescriptions from "./pages/patient/PatientPrescriptions.jsx"
import PatientLabResults from "./pages/patient/PatientLabResults.jsx"
import PatientBills from "./pages/patient/PatientBills.jsx"
import PatientDocuments from "./pages/patient/PatientDocuments.jsx"
import PatientConsent from "./pages/patient/PatientConsent.jsx"

function App() {
  return (
    <AuthProvider>
      <HospitalsProvider>
        <PatientProvider>
          <PrescriptionProvider>
            <PharmacyProvider>
              <RoleProvider>
                <SidebarProvider>
                  <BrowserRouter>
                    <Routes>
                      <Route path="/staff-login" element={<StaffLogin />} />
                      <Route path="/patient-login" element={<PatientLogin />} />

                      <Route element={<PatientLayout />}>
                        <Route path="/patient" element={<PatientDashboard />} />
                        <Route path="/patient/appointments" element={<PatientAppointments />} />
                        <Route path="/patient/queue" element={<PatientQueue />} />
                        <Route path="/patient/prescriptions" element={<PatientPrescriptions />} />
                        <Route path="/patient/lab-results" element={<PatientLabResults />} />
                        <Route path="/patient/bills" element={<PatientBills />} />
                        <Route path="/patient/documents" element={<PatientDocuments />} />
                        <Route path="/patient/consent" element={<PatientConsent />} />
                      </Route>

                      <Route element={<Layout />}>
                        <Route path="/" element={<Home />} />
                        <Route path="/patients" element={<Patients />} />
                        <Route path="/appointments" element={<Appointments />} />
                        <Route path="/queue" element={<Queue />} />
                        <Route path="/consultation" element={<Consultation />} />
                        <Route path="/prescription" element={<Prescription />} />
                        <Route path="/doctors" element={<Doctors />} />
                        <Route path="/nurses" element={<Nurses />} />
                        <Route path="/compounter" element={<Compounter />} />
                        <Route path="/pharmacy" element={<Pharmacy />} />
                        <Route path="/laboratory" element={<Laboratory />} />
                        <Route path="/billing" element={<Billing />} />
                        <Route path="/inventory" element={<Inventory />} />
                        <Route path="/reports" element={<Reports />} />
                        <Route path="/emergency" element={<Emergency />} />
                        <Route path="/blood-bank" element={<BloodBank />} />
                        <Route path="/ipd" element={<IPD />} />
                        <Route path="/ai-scribe" element={<AIScribe />} />
                        <Route path="/hospital-selection" element={<HospitalSelection />} />
                        <Route path="/admin" element={<AdminDashboard />} />
                        <Route path="/admin/users" element={<Users />} />
                        <Route path="/admin/roles" element={<Roles />} />
                        <Route path="/admin/hospitals" element={<Hospitals />} />
                        <Route path="/admin/departments" element={<Departments />} />
                        <Route path="/admin/permissions" element={<Permissions />} />
                        <Route path="/settings" element={<Settings />} />
                      </Route>
                    </Routes>
                  </BrowserRouter>
                </SidebarProvider>
              </RoleProvider>
            </PharmacyProvider>
          </PrescriptionProvider>
        </PatientProvider>
      </HospitalsProvider>
    </AuthProvider>
  )
}

export default App
