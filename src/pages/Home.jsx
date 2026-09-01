import { Link } from "react-router-dom"
import StatCard from "../components/StatCard"

function Home() {
  return (
    <div>

      {/* Welcome */}
      <div className="mb-8">

        <p className="text-blue-600 font-semibold">
          SMART HOSPITAL PLATFORM
        </p>

        <h1 className="text-4xl font-bold text-gray-800 mt-2">
          Welcome to Hospital Management System
        </h1>

        <p className="text-gray-500 mt-3 max-w-3xl">
          Manage patients, doctors, appointments, pharmacy,
          laboratory, billing and other hospital operations
          from one unified platform.
        </p>

      </div>


      {/* Open Dashboard */}
      <div className="mb-8">

        <Link
          to="/dashboard"
          className="inline-block bg-blue-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-700"
        >
          Open Dashboard
        </Link>

      </div>


      {/* Statistics */}
      <div className="mb-8 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">

        <StatCard
          title="Total Patients"
          value="1,245"
          icon="👥"
          color="bg-blue-100"
          subtitle="Total registered patients"
        />

        <StatCard
          title="Doctors"
          value="68"
          icon="👨‍⚕️"
          color="bg-green-100"
          subtitle="Active doctors"
        />

        <StatCard
          title="Today's Appointments"
          value="86"
          icon="📅"
          color="bg-orange-100"
          subtitle="Appointments scheduled today"
        />

        <StatCard
          title="Available Beds"
          value="46"
          icon="🛏️"
          color="bg-purple-100"
          subtitle="Beds currently available"
        />

      </div>


      {/* Patient Services */}
      <div className="mb-8">

        <h2 className="text-2xl font-bold text-gray-800 mb-5">
          Patient Services
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">

          {/* Book Appointment */}
          <Link
            to="/patient-login"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >
            <div className="text-3xl mb-3">
              📅
            </div>

            <h3 className="font-semibold text-gray-800">
              Book Appointment
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Book an appointment with a doctor
            </p>
          </Link>


          {/* Check Queue */}
          <Link
            to="/queue"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >
            <div className="text-3xl mb-3">
              🎫
            </div>

            <h3 className="font-semibold text-gray-800">
              Check Token
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Check token and queue status
            </p>
          </Link>


          {/* My Appointments */}
          <Link
            to="/appointments"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >
            <div className="text-3xl mb-3">
              📋
            </div>

            <h3 className="font-semibold text-gray-800">
              My Appointments
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              View your appointments
            </p>
          </Link>


          {/* Medical Records */}
          <Link
            to="/patients"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >
            <div className="text-3xl mb-3">
              🏥
            </div>

            <h3 className="font-semibold text-gray-800">
              Medical Records
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              View medical history
            </p>
          </Link>


          {/* Lab Reports */}
          <Link
            to="/laboratory"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >
            <div className="text-3xl mb-3">
              🧪
            </div>

            <h3 className="font-semibold text-gray-800">
              Lab Reports
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              View laboratory reports
            </p>
          </Link>


          {/* Prescription */}
          <Link
            to="/prescription"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >
            <div className="text-3xl mb-3">
              💊
            </div>

            <h3 className="font-semibold text-gray-800">
              Prescription
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              View prescriptions
            </p>
          </Link>


          {/* Follow Up */}
          <Link
            to="/follow-up"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >
            <div className="text-3xl mb-3">
              🔄
            </div>

            <h3 className="font-semibold text-gray-800">
              Follow-up
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Manage follow-up visits
            </p>
          </Link>


          {/* Find Doctors */}
          <Link
            to="/doctors"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >
            <div className="text-3xl mb-3">
              👨‍⚕️
            </div>

            <h3 className="font-semibold text-gray-800">
              Find Doctors
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Find available doctors
            </p>
          </Link>

        </div>

      </div>


      {/* Hospital Modules */}
      <div>

        <h2 className="text-2xl font-bold text-gray-800 mb-5">
          Hospital Modules
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">

          <Link
            to="/patients"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >
            <div className="text-3xl mb-3">👤</div>

            <h3 className="font-semibold text-gray-800">
              Patients
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Patient management
            </p>
          </Link>


          <Link
            to="/appointments"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >
            <div className="text-3xl mb-3">📅</div>

            <h3 className="font-semibold text-gray-800">
              Appointments
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Schedule appointments
            </p>
          </Link>


          <Link
            to="/doctors"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >
            <div className="text-3xl mb-3">👨‍⚕️</div>

            <h3 className="font-semibold text-gray-800">
              Doctors
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Doctor management
            </p>
          </Link>


          <Link
            to="/queue"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >
            <div className="text-3xl mb-3">🎫</div>

            <h3 className="font-semibold text-gray-800">
              Queue
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Live patient queue
            </p>
          </Link>


          <Link
            to="/pharmacy"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >
            <div className="text-3xl mb-3">💊</div>

            <h3 className="font-semibold text-gray-800">
              Pharmacy
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Medicine management
            </p>
          </Link>


          <Link
            to="/laboratory"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >
            <div className="text-3xl mb-3">🧪</div>

            <h3 className="font-semibold text-gray-800">
              Laboratory
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Lab tests and reports
            </p>
          </Link>


          <Link
            to="/billing"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >
            <div className="text-3xl mb-3">💳</div>

            <h3 className="font-semibold text-gray-800">
              Billing
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Billing management
            </p>
          </Link>


          <Link
            to="/inventory"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >
            <div className="text-3xl mb-3">📦</div>

            <h3 className="font-semibold text-gray-800">
              Inventory
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Stock management
            </p>
          </Link>


          <Link
            to="/reports"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >
            <div className="text-3xl mb-3">📊</div>

            <h3 className="font-semibold text-gray-800">
              Reports
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Hospital reports
            </p>
          </Link>

        </div>

      </div>


      {/* Quick Actions */}
      <div className="mt-8 bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

        <div className="mb-5">

          <h2 className="text-lg font-semibold text-gray-800">
            Quick Actions
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Frequently used hospital operations
          </p>

        </div>


        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

          <Link
            to="/patients"
            className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition"
          >
            <span className="text-2xl">👤</span>

            <div className="text-left">

              <p className="font-medium text-gray-800">
                Add Patient
              </p>

              <p className="text-xs text-gray-500">
                Register new patient
              </p>

            </div>
          </Link>


          <Link
            to="/patient-login"
            className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition"
          >
            <span className="text-2xl">📅</span>

            <div className="text-left">

              <p className="font-medium text-gray-800">
                Book Appointment
              </p>

              <p className="text-xs text-gray-500">
                Schedule appointment
              </p>

            </div>
          </Link>


          <Link
            to="/patients"
            className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition"
          >
            <span className="text-2xl">🛏️</span>

            <div className="text-left">

              <p className="font-medium text-gray-800">
                Admit Patient
              </p>

              <p className="text-xs text-gray-500">
                Start patient admission
              </p>

            </div>
          </Link>


          <Link
            to="/queue"
            className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition"
          >
            <span className="text-2xl">🎫</span>

            <div className="text-left">

              <p className="font-medium text-gray-800">
                View Queue
              </p>

              <p className="text-xs text-gray-500">
                Check live queue
              </p>

            </div>
          </Link>

        </div>

      </div>

    </div>
  )
}

export default Home