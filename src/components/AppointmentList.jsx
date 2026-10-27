import { usePatient } from "../assets/context/PatientContext.jsx"

function AppointmentList() {

  const { selectedHospital } = usePatient()

  const appointments = [
    {
      patient: "Patient A",
      doctor: "Dr. Sharma",
      time: "10:30 AM",
      status: "Confirmed",
      hospitalId: 1,
    },
    {
      patient: "Patient B",
      doctor: "Dr. Kumar",
      time: "11:00 AM",
      status: "Waiting",
      hospitalId: 1,
    },
    {
      patient: "Patient C",
      doctor: "Dr. Singh",
      time: "11:30 AM",
      status: "Completed",
      hospitalId: 2,
    },
  ]

  // Selected hospital ke appointments
  const hospitalAppointments = selectedHospital
    ? appointments.filter(
      (appointment) =>
        appointment.hospitalId === selectedHospital.id
    )
    : []

  return (

    <div className="bg-white rounded-2xl shadow-sm overflow-hidden">

      {/* Header */}

      <div className="flex items-center justify-between p-6 border-b">

        <div>

          <h2 className="text-xl font-bold text-gray-800">
            Today&apos;s Appointments
          </h2>

          <p className="text-gray-500 mt-1">

            {selectedHospital
              ? `Scheduled appointments for ${selectedHospital.name}`
              : "Select a hospital to view appointments"}

          </p>

        </div>

      </div>


      {/* No Hospital */}

      {!selectedHospital ? (

        <div className="p-10 text-center">

          <div className="text-4xl mb-3">
            🏥
          </div>

          <p className="font-semibold text-gray-800">
            No hospital selected
          </p>

          <p className="text-sm text-gray-500 mt-1">
            Select a hospital from the header.
          </p>

        </div>

      ) : hospitalAppointments.length === 0 ? (

        <div className="p-10 text-center">

          <div className="text-4xl mb-3">
            📅
          </div>

          <p className="font-semibold text-gray-800">
            No appointments
          </p>

          <p className="text-sm text-gray-500 mt-1">
            No appointments are scheduled for this hospital.
          </p>

        </div>

      ) : (

        /* Appointment List */

        <div>

          {hospitalAppointments.map(
            (appointment, index) => (

              <div
                key={index}
                className="flex items-center justify-between px-6 py-5 border-b last:border-b-0 hover:bg-gray-50"
              >

                {/* Patient */}

                <div>

                  <h3 className="font-semibold text-gray-800">
                    {appointment.patient}
                  </h3>

                  <p className="text-sm text-gray-500 mt-1">
                    {appointment.doctor}
                  </p>

                </div>


                {/* Time */}

                <div className="font-medium text-gray-700">
                  {appointment.time}
                </div>


                {/* Status */}

                <div>

                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${appointment.status === "Confirmed"
                        ? "bg-blue-100 text-blue-700"
                        : appointment.status === "Waiting"
                          ? "bg-orange-100 text-orange-700"
                          : "bg-green-100 text-green-700"
                      }`}
                  >
                    {appointment.status}
                  </span>

                </div>

              </div>

            )
          )}

        </div>

      )}

    </div>
  )
}

export default AppointmentList