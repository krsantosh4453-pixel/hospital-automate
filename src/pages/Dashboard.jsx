import { useMemo } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"

import AppointmentList from "../components/AppointmentList"
import StatCard from "../components/StatCard"
import BedStatus from "../components/BedStatus"
import EmergencyStatus from "../components/EmergencyStatus"

function Dashboard() {

  const { selectedHospital } = usePatient()

  /*
   * Demo data
   * Later Django API se hospital-wise data aayega.
   */
  const hospitalData = {
    1: {
      patients: "1,245",
      doctors: "68",
      appointments: "86",
      beds: "46",

      queueToken: "24",
      waitingPatients: "12",
      waitingTime: "14 min",

      recentPatients: [
        {
          name: "Rahul Kumar",
          id: "P001",
          department: "General Medicine",
        },
        {
          name: "Patient B",
          id: "P002",
          department: "Cardiology",
        },
        {
          name: "Patient C",
          id: "P003",
          department: "Orthopedics",
        },
      ],
    },

    2: {
      patients: "824",
      doctors: "42",
      appointments: "54",
      beds: "31",

      queueToken: "17",
      waitingPatients: "8",
      waitingTime: "11 min",

      recentPatients: [
        {
          name: "Amit Kumar",
          id: "P101",
          department: "Orthopedics",
        },
        {
          name: "Neha Singh",
          id: "P102",
          department: "Dermatology",
        },
        {
          name: "Ravi Kumar",
          id: "P103",
          department: "General Medicine",
        },
      ],
    },

    3: {
      patients: "562",
      doctors: "27",
      appointments: "38",
      beds: "19",

      queueToken: "11",
      waitingPatients: "5",
      waitingTime: "9 min",

      recentPatients: [
        {
          name: "Sanjay Kumar",
          id: "P201",
          department: "Pediatrics",
        },
        {
          name: "Priya Kumari",
          id: "P202",
          department: "General Medicine",
        },
        {
          name: "Rohit Singh",
          id: "P203",
          department: "Cardiology",
        },
      ],
    },
  }


  const currentData = useMemo(() => {

    if (!selectedHospital) {
      return null
    }

    return hospitalData[selectedHospital.id] || {
      patients: "0",
      doctors: "0",
      appointments: "0",
      beds: "0",

      queueToken: "0",
      waitingPatients: "0",
      waitingTime: "0 min",

      recentPatients: [],
    }

  }, [selectedHospital])


  return (

    <div>

      {/* ==============================
          PAGE HEADER
      ============================== */}

      <div className="mb-6">

        <h1 className="text-2xl font-bold text-gray-800">
          Hospital Dashboard
        </h1>

        <p className="text-gray-500 mt-1">
          Overview of hospital activities
        </p>

      </div>


      {/* ==============================
          CURRENT HOSPITAL
      ============================== */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        {selectedHospital ? (

          <div className="flex items-center justify-between gap-4">

            <div className="flex items-center gap-4">

              <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-2xl">
                🏥
              </div>

              <div>

                <p className="text-xs text-gray-500">
                  Current Hospital
                </p>

                <h2 className="font-bold text-gray-800">
                  {selectedHospital.name}
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  📍 {selectedHospital.address}
                </p>

              </div>

            </div>

            <div className="hidden md:block">

              <span className="px-3 py-2 rounded-lg bg-green-50 text-green-700 text-xs font-semibold">
                Active Hospital
              </span>

            </div>

          </div>

        ) : (

          <div>

            <p className="font-semibold text-orange-600">
              ⚠️ No hospital selected
            </p>

            <p className="text-sm text-gray-500 mt-1">
              Select a hospital from the header to view hospital data.
            </p>

          </div>

        )}

      </div>


      {/* ==============================
          NO HOSPITAL
      ============================== */}

      {!selectedHospital ? (

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">

          <div className="text-5xl mb-4">
            🏥
          </div>

          <h2 className="text-xl font-bold text-gray-800">
            Select a Hospital
          </h2>

          <p className="text-gray-500 mt-2">
            Please select a hospital from the header to load the dashboard.
          </p>

        </div>

      ) : (

        <>

          {/* ==============================
              STATISTICS CARDS
          ============================== */}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">

            <StatCard
              title="Total Patients"
              value={currentData.patients}
              icon="👥"
              color="bg-blue-100"
              subtitle={`Patients in ${selectedHospital.name}`}
            />

            <StatCard
              title="Doctors"
              value={currentData.doctors}
              icon="👨‍⚕️"
              color="bg-green-100"
              subtitle={`Doctors at ${selectedHospital.name}`}
            />

            <StatCard
              title="Today's Appointments"
              value={currentData.appointments}
              icon="📅"
              color="bg-orange-100"
              subtitle="Appointments scheduled today"
            />

            <StatCard
              title="Available Beds"
              value={currentData.beds}
              icon="🛏️"
              color="bg-purple-100"
              subtitle="Beds currently available"
            />

          </div>


          {/* ==============================
              APPOINTMENTS
          ============================== */}

          <div className="mt-6">

            <AppointmentList />

          </div>


          {/* ==============================
              CURRENT QUEUE
          ============================== */}

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mt-6">

            <div className="p-6 border-b">

              <h2 className="text-lg font-semibold text-gray-800">
                Current Queue
              </h2>

              <p className="text-sm text-gray-500 mt-1">
                Live patient consultation queue
              </p>

            </div>


            <div className="p-6 space-y-5">

              <div className="flex justify-between items-center">

                <span className="text-gray-600">
                  Doctor Consultation
                </span>

                <span className="font-semibold text-gray-800">
                  Token #{currentData.queueToken}
                </span>

              </div>


              <div className="flex justify-between items-center">

                <span className="text-gray-600">
                  Waiting Patients
                </span>

                <span className="font-semibold text-orange-500">
                  {currentData.waitingPatients}
                </span>

              </div>


              <div className="flex justify-between items-center">

                <span className="text-gray-600">
                  Estimated Waiting
                </span>

                <span className="font-semibold text-green-600">
                  {currentData.waitingTime}
                </span>

              </div>

            </div>

          </div>


          {/* ==============================
              BED + EMERGENCY
          ============================== */}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">

            <BedStatus />

            <EmergencyStatus />

          </div>


          {/* ==============================
              RECENT PATIENTS
          ============================== */}

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mt-6">

            {/* Header */}

            <div className="flex items-center justify-between p-6 border-b">

              <div>

                <h2 className="text-lg font-semibold text-gray-800">
                  Recent Patients
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Recently registered patients
                </p>

              </div>


              <button className="text-sm text-blue-600 font-medium hover:text-blue-700">
                View All
              </button>

            </div>


            {/* Patient List */}

            <div className="divide-y">

              {currentData.recentPatients.length > 0 ? (

                currentData.recentPatients.map(
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


                      <span className="text-sm text-gray-600">
                        {patient.department}
                      </span>

                    </div>

                  )
                )

              ) : (

                <div className="p-8 text-center text-gray-500">
                  No recent patients
                </div>

              )}

            </div>

          </div>


          {/* ==============================
              QUICK ACTIONS
          ============================== */}

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mt-6 p-6">

            <div className="mb-5">

              <h2 className="text-lg font-semibold text-gray-800">
                Quick Actions
              </h2>

              <p className="text-sm text-gray-500 mt-1">
                Frequently used hospital operations
              </p>

            </div>


            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">


              {/* Add Patient */}

              <button className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition">

                <span className="text-2xl">
                  👤
                </span>

                <div className="text-left">

                  <p className="font-medium text-gray-800">
                    Add Patient
                  </p>

                  <p className="text-xs text-gray-500">
                    Register new patient
                  </p>

                </div>

              </button>


              {/* New Appointment */}

              <button className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition">

                <span className="text-2xl">
                  📅
                </span>

                <div className="text-left">

                  <p className="font-medium text-gray-800">
                    New Appointment
                  </p>

                  <p className="text-xs text-gray-500">
                    Schedule appointment
                  </p>

                </div>

              </button>


              {/* Admit Patient */}

              <button className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition">

                <span className="text-2xl">
                  🛏️
                </span>

                <div className="text-left">

                  <p className="font-medium text-gray-800">
                    Admit Patient
                  </p>

                  <p className="text-xs text-gray-500">
                    Start patient admission
                  </p>

                </div>

              </button>


              {/* View Queue */}

              <button className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition">

                <span className="text-2xl">
                  🎫
                </span>

                <div className="text-left">

                  <p className="font-medium text-gray-800">
                    View Queue
                  </p>

                  <p className="text-xs text-gray-500">
                    Check live queue
                  </p>

                </div>

              </button>

            </div>

          </div>

        </>

      )}

    </div>
  )
}

export default Dashboard