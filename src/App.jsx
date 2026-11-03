import { lazy, Suspense } from "react"
import { LanguageProvider } from "./assets/context/LanguageContext.jsx"
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom"

import Layout from "./layouts/layout.jsx"
import PatientLayout from "./layouts/PatientLayout.jsx"

import Home from "./pages/Home.jsx"

import StaffLogin from "./pages/StaffLogin.jsx"
import PatientLogin from "./pages/PatientLogin.jsx"
import { SignInDialog } from "./components/auth/SignInDialog.jsx"
import { ProtectedRoute } from "./components/ProtectedRoute.jsx"
import AppBackground from "./components/AppBackground.jsx"
import { PageLoading } from "./components/LoadingSpinner.jsx"

import { AuthProvider } from "./assets/context/AuthContext.jsx"
import { PatientProvider } from "./assets/context/PatientContext.jsx"
import { PrescriptionProvider } from "./assets/context/PrescriptionContext.jsx"
import { PharmacyProvider } from "./assets/context/PharmacyContext.jsx"
import { HospitalsProvider } from "./assets/context/HospitalsContext.jsx"
import { SidebarProvider } from "./assets/context/SidebarContext.jsx"
import { RoleProvider } from "./assets/context/RoleContext.jsx"
import { RoleAuthBridge } from "./assets/context/RoleAuthBridge.jsx"

// Pages load on first visit; sign-in pages and Home stay in the main bundle.
const Patients = lazy(() => import("./pages/Patients.jsx"))
const Appointments = lazy(() => import("./pages/Appointments.jsx"))
const Queue = lazy(() => import("./pages/queue.jsx"))
const Doctors = lazy(() => import("./pages/doctors.jsx"))
const Nurses = lazy(() => import("./pages/Nurses.jsx"))
const Compounter = lazy(() => import("./pages/Compounter.jsx"))
const Consultation = lazy(() => import("./pages/Consultation.jsx"))
const Prescription = lazy(() => import("./pages/Prescription.jsx"))
const Pharmacy = lazy(() => import("./pages/pharmacy.jsx"))
const Laboratory = lazy(() => import("./pages/laboratory.jsx"))
const Radiology = lazy(() => import("./pages/Radiology.jsx"))
const Billing = lazy(() => import("./pages/billing.jsx"))
const Inventory = lazy(() => import("./pages/inventory.jsx"))
const Reports = lazy(() => import("./pages/reports.jsx"))
const Settings = lazy(() => import("./pages/settings.jsx"))
const Register = lazy(() => import("./pages/Register.jsx"))
const StaffInvite = lazy(() => import("./pages/StaffInvite.jsx"))
const HospitalSelection = lazy(() => import("./pages/HospitalSelection.jsx"))
const Emergency = lazy(() => import("./pages/Emergency.jsx"))
const BloodBank = lazy(() => import("./pages/BloodBank.jsx"))
const IPD = lazy(() => import("./pages/IPD.jsx"))
const AIScribe = lazy(() => import("./pages/AIScribe.jsx"))
const AdminDashboard = lazy(() => import("./pages/admin/AdminDashboard.jsx"))
const Users = lazy(() => import("./pages/admin/Users.jsx"))
const Roles = lazy(() => import("./pages/admin/Roles.jsx"))
const Hospitals = lazy(() => import("./pages/admin/Hospitals.jsx"))
const Departments = lazy(() => import("./pages/admin/Departments.jsx"))
const NurseDuty = lazy(() => import("./pages/admin/NurseDuty.jsx"))
const Permissions = lazy(() => import("./pages/admin/Permissions.jsx"))
const AuditLog = lazy(() => import("./pages/admin/AuditLog.jsx"))
const EmergencyAccess = lazy(() => import("./pages/EmergencyAccess.jsx"))
const SecuritySettings = lazy(() => import("./pages/admin/SecuritySettings.jsx"))
const HospitalSetup = lazy(() => import("./pages/admin/HospitalSetup.jsx"))
const PatientDashboard = lazy(() => import("./pages/patient/PatientDashboard.jsx"))
const PatientAppointments = lazy(() => import("./pages/patient/PatientAppointments.jsx"))
const PatientQueue = lazy(() => import("./pages/patient/PatientQueue.jsx"))
const PatientPrescriptions = lazy(() => import("./pages/patient/PatientPrescriptions.jsx"))
const PatientLabResults = lazy(() => import("./pages/patient/PatientLabResults.jsx"))
const PatientBills = lazy(() => import("./pages/patient/PatientBills.jsx"))
const PatientDocuments = lazy(() => import("./pages/patient/PatientDocuments.jsx"))
const PatientConsent = lazy(() => import("./pages/patient/PatientConsent.jsx"))

/*
 * A sign-in link opened from a page carries `backgroundLocation` (see
 * SignInDialog): that page keeps rendering underneath and the sign-in route
 * is drawn on top of it as a dialog. Without it, sign-in is a full page.
 */
function RoutesWithSignInDialog({ children }) {
  const location = useLocation()
  const background = location.state?.backgroundLocation

  return (
    <>
      <Routes location={background || location}>{children}</Routes>
      {background && (
        <Routes>
          <Route path="/staff-login" element={<SignInDialog title="Staff sign in"><StaffLogin /></SignInDialog>} />
          <Route path="/patient-login" element={<SignInDialog title="Sign in"><PatientLogin /></SignInDialog>} />
          <Route path="/login" element={<SignInDialog title="Sign in"><PatientLogin /></SignInDialog>} />
          <Route path="*" element={null} />
        </Routes>
      )}
    </>
  )
}

function App() {
  return (
    <LanguageProvider>
    <AuthProvider>
      <HospitalsProvider>
        <PatientProvider>
          <PrescriptionProvider>
            <PharmacyProvider>
              <RoleProvider>
                <RoleAuthBridge>
                <SidebarProvider>
                  <AppBackground />
                  <BrowserRouter>
                    <Suspense fallback={<PageLoading />}>
                    <RoutesWithSignInDialog>
                      <Route path="/staff-login" element={<StaffLogin />} />
                      <Route path="/patient-login" element={<PatientLogin />} />
                      <Route path="/login" element={<PatientLogin />} />
                      <Route path="/register" element={<Register />} />
                      <Route path="/staff-invite/:uid/:token" element={<StaffInvite />} />

                      <Route element={<ProtectedRoute audience="patient" />}>
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
                      </Route>

                      {/* "/" shows the public home to visitors (see ProtectedRoute); every other staff page needs a sign-in. */}
                        <Route element={<ProtectedRoute audience="staff" />}>
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
                          <Route path="/radiology" element={<Radiology />} />
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
                          <Route path="/admin/nurse-duty" element={<NurseDuty />} />
                          <Route path="/admin/permissions" element={<Permissions />} />
                          <Route path="/admin/audit" element={<AuditLog />} />
                          <Route path="/emergency-access" element={<EmergencyAccess />} />
                          <Route path="/admin/security" element={<SecuritySettings />} />
                          <Route path="/admin/setup" element={<HospitalSetup />} />
                          <Route path="/settings" element={<Settings />} />
                        </Route>
                        </Route>
                    </RoutesWithSignInDialog>
                    </Suspense>
                  </BrowserRouter>
                </SidebarProvider>
                </RoleAuthBridge>
              </RoleProvider>
            </PharmacyProvider>
          </PrescriptionProvider>
        </PatientProvider>
      </HospitalsProvider>
    </AuthProvider>
    </LanguageProvider>
  )
}

export default App
