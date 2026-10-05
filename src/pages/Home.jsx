import { Link } from "react-router-dom"
import { useMemo } from "react"

import StatCard from "../components/StatCard"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { usePharmacy } from "../assets/context/PharmacyContext.jsx"
import { usePrescription } from "../assets/context/PrescriptionContext.jsx"
import { useAuth } from "../assets/context/AuthContext.jsx"


function Home() {

  // =====================================
  // AUTHENTICATION
  // =====================================

  const {
    isLoggedIn,
    patient,
  } = useAuth()


  // =====================================
  // SELECTED HOSPITAL
  // =====================================

  const { selectedHospital } = usePatient()


  // =====================================
  // PHARMACY DATA
  // =====================================

  const {
    getHospitalSales,
  } = usePharmacy()


  // =====================================
  // PRESCRIPTION DATA
  // =====================================

  const {
    getHospitalPrescriptions,
  } = usePrescription()


  // =====================================
  // DEMO DATA
  // Later Django API se aayega
  // =====================================

  const patients = [

    {
      id: "P001",
      name: "Rahul Kumar",
      hospitalId: 1,
    },

    {
      id: "P002",
      name: "Priya Singh",
      hospitalId: 1,
    },

    {
      id: "P003",
      name: "Amit Kumar",
      hospitalId: 2,
    },

    {
      id: "P004",
      name: "Neha Kumari",
      hospitalId: 2,
    },

    {
      id: "P005",
      name: "Ravi Sharma",
      hospitalId: 3,
    },

  ]


  const doctors = [

    {
      id: "D001",
      name: "Dr. Sharma",
      hospitalId: 1,
      status: "Active",
    },

    {
      id: "D002",
      name: "Dr. Kumar",
      hospitalId: 1,
      status: "Active",
    },

    {
      id: "D003",
      name: "Dr. Singh",
      hospitalId: 2,
      status: "Active",
    },

    {
      id: "D004",
      name: "Dr. Verma",
      hospitalId: 3,
      status: "Active",
    },

  ]


  const appointments = [

    {
      id: "A001",
      patient: "Rahul Kumar",
      hospitalId: 1,
      status: "Confirmed",
    },

    {
      id: "A002",
      patient: "Priya Singh",
      hospitalId: 1,
      status: "Waiting",
    },

    {
      id: "A003",
      patient: "Amit Kumar",
      hospitalId: 2,
      status: "Completed",
    },

    {
      id: "A004",
      patient: "Neha Kumari",
      hospitalId: 3,
      status: "Confirmed",
    },

  ]


  const beds = [

    {
      id: "B001",
      hospitalId: 1,
      status: "Available",
    },

    {
      id: "B002",
      hospitalId: 1,
      status: "Occupied",
    },

    {
      id: "B003",
      hospitalId: 1,
      status: "Available",
    },

    {
      id: "B004",
      hospitalId: 2,
      status: "Occupied",
    },

    {
      id: "B005",
      hospitalId: 3,
      status: "Available",
    },

  ]


  // =====================================
  // GUEST HOME
  // =====================================
  // Login ke bina user app explore kar sakta hai.
  // Existing logged-in Home neeche exactly maintained hai.
  // =====================================

  if (!isLoggedIn) {

    return (

      <div className="space-y-8">


        {/* =====================================
            GUEST HERO
        ===================================== */}

        <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-3xl p-8 md:p-12 text-white">

          <div className="max-w-4xl">

            <p className="text-blue-100 font-semibold text-sm tracking-wide">
              SMART HOSPITAL PLATFORM
            </p>

            <h1 className="text-4xl md:text-5xl font-bold mt-3 leading-tight">
              Your Healthcare,
              <br />
              Simple & Connected
            </h1>

            <p className="text-blue-100 text-lg mt-5 max-w-2xl">
              Find doctors, explore hospitals, book appointments,
              check healthcare services and manage your healthcare
              journey from one place.
            </p>


            <div className="flex flex-wrap gap-4 mt-8">

              <Link
                to="/appointments"
                className="bg-white text-blue-600 px-6 py-3 rounded-xl font-semibold hover:bg-blue-50 transition"
              >
                📅 Book Appointment
              </Link>


              <Link
                to="/doctors"
                className="border border-white/50 text-white px-6 py-3 rounded-xl font-semibold hover:bg-white/10 transition"
              >
                👨‍⚕️ Find Doctors
              </Link>

            </div>

          </div>

        </div>


        {/* =====================================
            GUEST WELCOME
        ===================================== */}

        <div>

          <p className="text-blue-600 font-semibold">
            EXPLORE WITHOUT LOGIN
          </p>

          <h1 className="text-3xl font-bold text-gray-800 mt-2">
            Explore Healthcare Services
          </h1>

          <p className="text-gray-500 mt-2">
            You can explore the available services first.
            Login will only be suggested when an action needs
            your personal information to be saved.
          </p>

        </div>


        {/* =====================================
            GUEST SERVICES
        ===================================== */}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">


          <Link
            to="/appointments"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >

            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">
              📅
            </div>

            <h3 className="font-semibold text-gray-800 mt-4">
              Book Appointment
            </h3>

            <p className="text-sm text-gray-500 mt-2">
              Select hospital, doctor, date and available slot.
            </p>

          </Link>


          <Link
            to="/doctors"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-green-200 transition"
          >

            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center text-2xl">
              👨‍⚕️
            </div>

            <h3 className="font-semibold text-gray-800 mt-4">
              Find Doctors
            </h3>

            <p className="text-sm text-gray-500 mt-2">
              Explore doctors and their departments.
            </p>

          </Link>


          <Link
            to="/laboratory"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-purple-200 transition"
          >

            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center text-2xl">
              🧪
            </div>

            <h3 className="font-semibold text-gray-800 mt-4">
              Laboratory
            </h3>

            <p className="text-sm text-gray-500 mt-2">
              Explore laboratory tests and services.
            </p>

          </Link>


          <Link
            to="/pharmacy"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-orange-200 transition"
          >

            <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center text-2xl">
              💊
            </div>

            <h3 className="font-semibold text-gray-800 mt-4">
              Pharmacy
            </h3>

            <p className="text-sm text-gray-500 mt-2">
              Explore pharmacy and medicine services.
            </p>

          </Link>

        </div>


        {/* =====================================
            HOW IT WORKS
        ===================================== */}

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 md:p-8">

          <h2 className="text-2xl font-bold text-gray-800">
            How Appointment Booking Works
          </h2>

          <p className="text-gray-500 mt-2">
            No login is required just to explore the appointment process.
          </p>


          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-8">

            <GuestStep
              number="1"
              icon="🏥"
              title="Select Hospital"
              text="Choose the hospital where you want to visit."
            />

            <GuestStep
              number="2"
              icon="👨‍⚕️"
              title="Select Doctor"
              text="Choose a department and available doctor."
            />

            <GuestStep
              number="3"
              icon="🕐"
              title="Choose Slot"
              text="Select your preferred date and available time."
            />

            <GuestStep
              number="4"
              icon="🔐"
              title="Confirm"
              text="Login is suggested only when you confirm the booking."
            />

          </div>

        </div>


        {/* =====================================
            LOGIN SUGGESTION
        ===================================== */}

        <div className="bg-blue-50 border border-blue-100 rounded-2xl p-6">

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5">

            <div>

              <h2 className="text-xl font-bold text-blue-900">
                Ready to manage your healthcare?
              </h2>

              <p className="text-sm text-blue-700 mt-2 max-w-2xl">
                Login to save appointments, access prescriptions,
                laboratory reports, medical records and your profile.
              </p>

            </div>


            <Link
              to="/patient-login"
              className="bg-blue-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-blue-700 whitespace-nowrap"
            >
              Login / Register
            </Link>

          </div>

        </div>


        {/* =====================================
            GUEST INFORMATION
        ===================================== */}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">

          <div className="bg-white rounded-2xl border border-gray-100 p-6">

            <div className="text-3xl">
              🔎
            </div>

            <h3 className="font-semibold text-gray-800 mt-4">
              Explore First
            </h3>

            <p className="text-sm text-gray-500 mt-2">
              Browse hospitals, doctors and services before
              deciding to login.
            </p>

          </div>


          <div className="bg-white rounded-2xl border border-gray-100 p-6">

            <div className="text-3xl">
              🔐
            </div>

            <h3 className="font-semibold text-gray-800 mt-4">
              Login When Needed
            </h3>

            <p className="text-sm text-gray-500 mt-2">
              Login is requested when your personal information
              needs to be saved.
            </p>

          </div>


          <div className="bg-white rounded-2xl border border-gray-100 p-6">

            <div className="text-3xl">
              📋
            </div>

            <h3 className="font-semibold text-gray-800 mt-4">
              Keep Your Records
            </h3>

            <p className="text-sm text-gray-500 mt-2">
              After login, your appointments and healthcare
              information can be connected to your account.
            </p>

          </div>

        </div>


      </div>

    )
  }


  // =====================================
  // NO HOSPITAL SELECTED
  // =====================================

  if (!selectedHospital) {

    return (

      <div className="space-y-8">

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-10 text-center">

          <div className="text-6xl mb-4">
            👋
          </div>

          <h1 className="text-3xl font-bold text-gray-800">
            Welcome {patient?.name || "Patient"}
          </h1>

          <p className="text-gray-500 mt-2">
            Please select a hospital from the header to continue.
          </p>

          <Link
            to="/hospital-selection"
            className="inline-block mt-6 bg-blue-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-blue-700"
          >
            Select Hospital
          </Link>

        </div>

      </div>

    )
  }


  // =====================================
  // HOSPITAL-WISE DATA
  // =====================================

  const hospitalPatients =
    patients.filter(
      (patient) =>
        patient.hospitalId ===
        selectedHospital.id
    )


  const hospitalDoctors =
    doctors.filter(
      (doctor) =>
        doctor.hospitalId ===
        selectedHospital.id
    )


  const hospitalAppointments =
    appointments.filter(
      (appointment) =>
        appointment.hospitalId ===
        selectedHospital.id
    )


  const hospitalBeds =
    beds.filter(
      (bed) =>
        bed.hospitalId ===
        selectedHospital.id
    )


  const hospitalSales =
    getHospitalSales(
      selectedHospital.id
    )


  const hospitalPrescriptions =
    getHospitalPrescriptions(
      selectedHospital.id
    )


  // =====================================
  // BED COUNT
  // =====================================

  const availableBeds =
    hospitalBeds.filter(
      (bed) =>
        bed.status ===
        "Available"
    ).length


  // =====================================
  // TODAY APPOINTMENTS
  // =====================================

  const todayAppointments =
    hospitalAppointments.length


  // =====================================
  // RECENT PATIENT
  // =====================================

  const recentPatients =
    useMemo(
      () =>
        hospitalPatients.slice(
          0,
          3
        ),
      [hospitalPatients]
    )


  return (

    <div className="space-y-8">


      {/* =====================================
          HOSPITAL HEADER
      ===================================== */}

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5">

          <div className="flex items-center gap-4">

            <div className="w-14 h-14 bg-blue-100 rounded-2xl flex items-center justify-center text-3xl">
              🏥
            </div>

            <div>

              <p className="text-blue-600 font-semibold text-sm">
                SELECTED HOSPITAL
              </p>

              <h1 className="text-2xl font-bold text-gray-800 mt-1">
                {selectedHospital.name}
              </h1>

              <p className="text-sm text-gray-500 mt-1">
                📍 {selectedHospital.address}
              </p>

            </div>

          </div>


          <div className="px-4 py-2 bg-green-50 text-green-700 rounded-xl text-sm font-semibold">

            ✓ Hospital Active

          </div>

        </div>

      </div>


      {/* =====================================
          WELCOME
      ===================================== */}

      <div>

        <p className="text-blue-600 font-semibold">
          SMART HOSPITAL PLATFORM
        </p>

        <h1 className="text-4xl font-bold text-gray-800 mt-2">
          {selectedHospital.name}
        </h1>

        <p className="text-gray-500 mt-3 max-w-3xl">
          Manage patients, doctors, appointments, pharmacy,
          laboratory, billing and other operations of{" "}
          <span className="font-semibold text-gray-700">
            {selectedHospital.name}
          </span>{" "}
          from one unified platform.
        </p>

      </div>


      {/* =====================================
          HOSPITAL STATISTICS
      ===================================== */}

      <div>

        <h2 className="text-2xl font-bold text-gray-800 mb-5">
          {selectedHospital.name} Overview
        </h2>


        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">


          <StatCard
            title="Total Patients"
            value={
              hospitalPatients.length
            }
            icon="👥"
            color="bg-blue-100"
            subtitle="Registered patients"
          />


          <StatCard
            title="Doctors"
            value={
              hospitalDoctors.length
            }
            icon="👨‍⚕️"
            color="bg-green-100"
            subtitle="Active doctors"
          />


          <StatCard
            title="Today's Appointments"
            value={
              todayAppointments
            }
            icon="📅"
            color="bg-orange-100"
            subtitle="Scheduled appointments"
          />


          <StatCard
            title="Available Beds"
            value={
              availableBeds
            }
            icon="🛏️"
            color="bg-purple-100"
            subtitle="Currently available"
          />

        </div>

      </div>


      {/* =====================================
          PATIENT SERVICES
      ===================================== */}

      <div>

        <h2 className="text-2xl font-bold text-gray-800 mb-5">
          Patient Services
        </h2>


        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">


          <Link
            to="/appointments"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:border-blue-200 transition"
          >

            <div className="text-3xl mb-3">
              📅
            </div>

            <h3 className="font-semibold text-gray-800">
              Book Appointment
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Book an appointment at {selectedHospital.name}
            </p>

          </Link>


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
              Check queue for this hospital
            </p>

          </Link>


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
              View hospital appointments
            </p>

          </Link>

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
              View patient medical history
            </p>

          </Link>


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
              Find doctors at this hospital
            </p>

          </Link>

        </div>

      </div>


      {/* =====================================
          HOSPITAL MODULES
      ===================================== */}

      <div>

        <h2 className="text-2xl font-bold text-gray-800 mb-5">
          Hospital Modules
        </h2>


        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">


          <Link
            to="/patients"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >

            <div className="text-3xl mb-3">
              👤
            </div>

            <h3 className="font-semibold text-gray-800">
              Patients
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              {hospitalPatients.length} patients
            </p>

          </Link>


          <Link
            to="/appointments"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >

            <div className="text-3xl mb-3">
              📅
            </div>

            <h3 className="font-semibold text-gray-800">
              Appointments
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              {hospitalAppointments.length} appointments
            </p>

          </Link>


          <Link
            to="/doctors"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >

            <div className="text-3xl mb-3">
              👨‍⚕️
            </div>

            <h3 className="font-semibold text-gray-800">
              Doctors
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              {hospitalDoctors.length} active doctors
            </p>

          </Link>


          <Link
            to="/queue"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >

            <div className="text-3xl mb-3">
              🎫
            </div>

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

            <div className="text-3xl mb-3">
              💊
            </div>

            <h3 className="font-semibold text-gray-800">
              Pharmacy
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              {hospitalSales.length} medicine sales
            </p>

          </Link>


          <Link
            to="/laboratory"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >

            <div className="text-3xl mb-3">
              🧪
            </div>

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

            <div className="text-3xl mb-3">
              💳
            </div>

            <h3 className="font-semibold text-gray-800">
              Billing
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Hospital billing
            </p>

          </Link>


          <Link
            to="/inventory"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >

            <div className="text-3xl mb-3">
              📦
            </div>

            <h3 className="font-semibold text-gray-800">
              Inventory
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              Hospital stock
            </p>

          </Link>


          <Link
            to="/reports"
            className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition"
          >

            <div className="text-3xl mb-3">
              📊
            </div>

            <h3 className="font-semibold text-gray-800">
              Reports
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              {selectedHospital.name} reports
            </p>

          </Link>

        </div>

      </div>


      {/* =====================================
          RECENT PATIENTS
      ===================================== */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100">

        <div className="flex items-center justify-between p-6 border-b">

          <div>

            <h2 className="text-lg font-semibold text-gray-800">
              Recent Patients
            </h2>

            <p className="text-sm text-gray-500 mt-1">
              Patients of {selectedHospital.name}
            </p>

          </div>


          <Link
            to="/patients"
            className="text-sm text-blue-600 font-medium hover:text-blue-700"
          >
            View All
          </Link>

        </div>


        <div className="divide-y">

          {recentPatients.length > 0 ? (

            recentPatients.map(
              (patient) => (

                <div
                  key={patient.id}
                  className="p-5 flex items-center justify-between"
                >

                  <div className="flex items-center gap-4">

                    <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                      👤
                    </div>

                    <div>

                      <p className="font-medium text-gray-800">
                        {patient.name}
                      </p>

                      <p className="text-sm text-gray-500">
                        {patient.id}
                      </p>

                    </div>

                  </div>

                  <span className="text-sm text-gray-500">
                    {selectedHospital.name}
                  </span>

                </div>

              )
            )

          ) : (

            <div className="p-8 text-center text-gray-500">
              No patients found for this hospital.
            </div>

          )}

        </div>

      </div>


      {/* =====================================
          QUICK ACTIONS
      ===================================== */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

        <div className="mb-5">

          <h2 className="text-lg font-semibold text-gray-800">
            Quick Actions
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Operations for {selectedHospital.name}
          </p>

        </div>


        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">


          <Link
            to="/patients"
            className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition"
          >

            <span className="text-2xl">
              👤
            </span>

            <div>

              <p className="font-medium text-gray-800">
                Add Patient
              </p>

              <p className="text-xs text-gray-500">
                Register new patient
              </p>

            </div>

          </Link>


          <Link
            to="/appointments"
            className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition"
          >

            <span className="text-2xl">
              📅
            </span>

            <div>

              <p className="font-medium text-gray-800">
                New Appointment
              </p>

              <p className="text-xs text-gray-500">
                Schedule appointment
              </p>

            </div>

          </Link>


          <Link
            to="/pharmacy"
            className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition"
          >

            <span className="text-2xl">
              💊
            </span>

            <div>

              <p className="font-medium text-gray-800">
                Pharmacy
              </p>

              <p className="text-xs text-gray-500">
                Issue medicines
              </p>

            </div>

          </Link>


          <Link
            to="/queue"
            className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition"
          >

            <span className="text-2xl">
              🎫
            </span>

            <div>

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


      {/* =====================================
          HOSPITAL STATUS
      ===================================== */}

      <div className="bg-blue-50 border border-blue-100 rounded-2xl p-5">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">

          <div>

            <p className="font-semibold text-blue-800">
              Current Hospital
            </p>

            <p className="text-sm text-blue-600 mt-1">
              All information on this page belongs to{" "}
              <span className="font-semibold">
                {selectedHospital.name}
              </span>
              .
            </p>

          </div>


          <div className="text-sm text-blue-600">

            Hospital ID:{" "}
            <span className="font-semibold">
              {selectedHospital.id}
            </span>

          </div>

        </div>

      </div>


    </div>
  )
}


// =====================================
// GUEST STEP COMPONENT
// =====================================

function GuestStep({
  number,
  icon,
  title,
  text,
}) {

  return (

    <div className="text-center">

      <div className="relative mx-auto w-14 h-14">

        <div className="w-14 h-14 rounded-2xl bg-blue-100 flex items-center justify-center text-2xl">
          {icon}
        </div>

        <span className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
          {number}
        </span>

      </div>


      <h3 className="font-semibold text-gray-800 mt-4">
        {title}
      </h3>


      <p className="text-sm text-gray-500 mt-1">
        {text}
      </p>

    </div>

  )
}


export default Home