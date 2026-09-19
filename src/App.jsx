import { BrowserRouter, Route, Routes } from "react-router-dom"

// =========================
// Layout
// =========================

import Layout from "./layouts/layout.jsx"

// =========================
// Main Pages
// =========================

import Home from "./pages/Home.jsx"
import Dashboard from "./pages/Dashboard.jsx"
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

// =========================
// Patient
// =========================

import PatientLogin from "./pages/PatientLogin.jsx"
import HospitalSelection from "./pages/HospitalSelection.jsx"

// =========================
// Contexts
// =========================

import {
  AuthProvider,
} from "./assets/context/AuthContext.jsx"

import {
  PatientProvider,
} from "./assets/context/PatientContext.jsx"

import {
  PrescriptionProvider,
} from "./assets/context/PrescriptionContext.jsx"

import {
  PharmacyProvider,
} from "./assets/context/PharmacyContext.jsx"

import {
  HospitalsProvider,
} from "./assets/context/HospitalsContext.jsx"

import {
  SidebarProvider,
} from "./assets/context/SidebarContext.jsx"

import {
  RoleProvider,
} from "./assets/context/RoleContext.jsx"

// =========================
// Admin Pages
// =========================

import AdminDashboard from "./pages/admin/AdminDashboard.jsx"
import Users from "./pages/admin/Users.jsx"
import Roles from "./pages/admin/Roles.jsx"
import Hospitals from "./pages/admin/Hospitals.jsx"
import Departments from "./pages/admin/Departments.jsx"
import Permissions from "./pages/admin/Permissions.jsx"

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

                      {/* =================================================
                      PATIENT LOGIN
                  ================================================= */}

                      <Route
                        path="/patient-login"
                        element={<PatientLogin />}
                      />


                      {/* =================================================
                      HOSPITAL SOFTWARE
                  ================================================= */}

                      <Route element={<Layout />}>

                        {/* =========================
                        Main
                    ========================= */}

                        <Route
                          path="/"
                          element={<Home />}
                        />

                        <Route
                          path="/dashboard"
                          element={<Dashboard />}
                        />

                        <Route
                          path="/patients"
                          element={<Patients />}
                        />

                        <Route
                          path="/appointments"
                          element={<Appointments />}
                        />

                        <Route
                          path="/queue"
                          element={<Queue />}
                        />

                        {/* =========================
                        Clinical
                    ========================= */}

                        <Route
                          path="/consultation"
                          element={<Consultation />}
                        />

                        <Route
                          path="/prescription"
                          element={<Prescription />}
                        />

                        {/* =========================
                        Staff
                    ========================= */}

                        <Route
                          path="/doctors"
                          element={<Doctors />}
                        />

                        <Route
                          path="/nurses"
                          element={<Nurses />}
                        />

                        <Route
                          path="/compounter"
                          element={<Compounter />}
                        />

                        {/* =========================
                        Hospital Modules
                    ========================= */}

                        <Route
                          path="/pharmacy"
                          element={<Pharmacy />}
                        />

                        <Route
                          path="/laboratory"
                          element={<Laboratory />}
                        />

                        <Route
                          path="/billing"
                          element={<Billing />}
                        />

                        <Route
                          path="/inventory"
                          element={<Inventory />}
                        />

                        <Route
                          path="/reports"
                          element={<Reports />}
                        />

                        {/* =========================
                        Hospital Selection
                    ========================= */}

                        <Route
                          path="/hospital-selection"
                          element={<HospitalSelection />}
                        />


                        {/* =================================================
                        ADMIN
                    ================================================= */}

                        <Route
                          path="/admin"
                          element={<AdminDashboard />}
                        />

                        <Route
                          path="/admin/users"
                          element={<Users />}
                        />

                        <Route
                          path="/admin/roles"
                          element={<Roles />}
                        />

                        <Route
                          path="/admin/hospitals"
                          element={<Hospitals />}
                        />

                        <Route
                          path="/admin/departments"
                          element={<Departments />}
                        />

                        <Route
                          path="/admin/permissions"
                          element={<Permissions />}
                        />


                        {/* =========================
                        Settings
                    ========================= */}

                        <Route
                          path="/settings"
                          element={<Settings />}
                        />

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