import { BrowserRouter, Route, Routes } from "react-router-dom"

import Layout from "./layouts/layout.jsx"

import Home from "./pages/Home.jsx"
import Dashboard from "./pages/Dashboard.jsx"
import Patients from "./pages/Patients.jsx"
import Appointments from "./pages/Appointments.jsx"
import Queue from "./pages/queue.jsx"
import Doctors from "./pages/doctors.jsx"
import Pharmacy from "./pages/pharmacy.jsx"
import Laboratory from "./pages/laboratory.jsx"
import Billing from "./pages/billing.jsx"
import Inventory from "./pages/inventory.jsx"
import Reports from "./pages/reports.jsx"
import Settings from "./pages/settings.jsx"

import PatientLogin from "./pages/PatientLogin.jsx"

import { AuthProvider } from "./assets/context/AuthContext.jsx"
import { PatientProvider } from "./assets/context/PatientContext.jsx"
import HospitalSelection from "./pages/HospitalSelection.jsx"


function App() {
  return (

    <AuthProvider>

      <PatientProvider>

        <BrowserRouter>

          <Routes>

            {/* Patient Login */}

            <Route
              path="/patient-login"
              element={<PatientLogin />}
            />


            {/* Hospital Software */}

            <Route element={<Layout />}>

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

              <Route
                path="/doctors"
                element={<Doctors />}
              />

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

              <Route
                path="/settings"
                element={<Settings />}
              />

              <Route
                path="/hospital-selection"
                element={<HospitalSelection />}
              />

            </Route>

          </Routes>

        </BrowserRouter>

      </PatientProvider>

    </AuthProvider>

  )
}


export default App