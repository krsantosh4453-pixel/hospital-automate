
import AppointmentList from "../components/AppointmentList"
import StatCard from "../components/StatCard"
import BedStatus from "../components/BedStatus"
import EmergencyStatus from "../components/EmergencyStatus"

function Dashboard() {
  return (

    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">
          Hospital Dashboard
        </h1>

        <p className="text-gray-500 mt-1">
          Overview of hospital activities
        </p>
      </div>


      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">

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


      {/* Dashboard Main Sections */}
      <div className="mt-6">

        <AppointmentList />

      </div>


      {/* Current Queue */}
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
              Token #24
            </span>
          </div>


          <div className="flex justify-between items-center">
            <span className="text-gray-600">
              Waiting Patients
            </span>

            <span className="font-semibold text-orange-500">
              12
            </span>
          </div>


          <div className="flex justify-between items-center">
            <span className="text-gray-600">
              Estimated Waiting
            </span>

            <span className="font-semibold text-green-600">
              14 min
            </span>
          </div>

        </div>

      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">

        <BedStatus />

        <EmergencyStatus />

      </div>
      {/* Recent Patients */}
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

          <div className="p-5 flex items-center justify-between">

            <div className="flex items-center gap-4">

              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                👤
              </div>

              <div>
                <p className="font-medium text-gray-800">
                  Rahul Kumar
                </p>

                <p className="text-sm text-gray-500">
                  P001
                </p>
              </div>

            </div>

            <span className="text-sm text-gray-600">
              General Medicine
            </span>

          </div>


          <div className="p-5 flex items-center justify-between">

            <div className="flex items-center gap-4">

              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                👤
              </div>

              <div>
                <p className="font-medium text-gray-800">
                  Patient B
                </p>

                <p className="text-sm text-gray-500">
                  P002
                </p>
              </div>

            </div>

            <span className="text-sm text-gray-600">
              Cardiology
            </span>

          </div>


          <div className="p-5 flex items-center justify-between">

            <div className="flex items-center gap-4">

              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                👤
              </div>

              <div>
                <p className="font-medium text-gray-800">
                  Patient C
                </p>

                <p className="text-sm text-gray-500">
                  P003
                </p>
              </div>

            </div>

            <span className="text-sm text-gray-600">
              Orthopedics
            </span>

          </div>

        </div>

      </div>
      {/* Quick Actions */}
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

    </div>

  )
}

export default Dashboard