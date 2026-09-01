function AppointmentList() {
  const appointments = [
    {
      patient: "Patient A",
      doctor: "Dr. Sharma",
      time: "10:30 AM",
      status: "Confirmed",
    },
    {
      patient: "Patient B",
      doctor: "Dr. Kumar",
      time: "11:00 AM",
      status: "Waiting",
    },
    {
      patient: "Patient C",
      doctor: "Dr. Singh",
      time: "11:30 AM",
      status: "Completed",
    },
  ]

  return (
    <div className="bg-white rounded-2xl shadow-sm overflow-hidden">

      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b">

        <div>
          <h2 className="text-xl font-bold text-gray-800">
            Today's Appointments
          </h2>

          <p className="text-gray-500 mt-1">
            Scheduled appointments for today
          </p>
        </div>

      </div>


      {/* Appointment List */}
      <div>

        {appointments.map((appointment, index) => (

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

        ))}

      </div>

    </div>
  )
}

export default AppointmentList