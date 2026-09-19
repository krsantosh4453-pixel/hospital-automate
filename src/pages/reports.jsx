import { useMemo, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { usePharmacy } from "../assets/context/PharmacyContext.jsx"
import { usePrescription } from "../assets/context/PrescriptionContext.jsx"


function Reports() {

  // =====================================
  // SELECTED HOSPITAL
  // =====================================

  const { selectedHospital } = usePatient()


  // =====================================
  // SHARED PHARMACY DATA
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
  // REPORT PERIOD
  // =====================================

  const [period, setPeriod] =
    useState("Today")


  // =====================================
  // DEMO HOSPITAL DATA
  // =====================================
  // Later these will come from Django API.
  // hospitalId keeps data isolated.
  // =====================================

  const patients = [

    {
      id: "P001",
      name: "Rahul Kumar",
      hospitalId: 1,
      gender: "Male",
      age: 32,
    },

    {
      id: "P002",
      name: "Priya Singh",
      hospitalId: 1,
      gender: "Female",
      age: 28,
    },

    {
      id: "P003",
      name: "Amit Kumar",
      hospitalId: 2,
      gender: "Male",
      age: 45,
    },

    {
      id: "P004",
      name: "Neha Kumari",
      hospitalId: 2,
      gender: "Female",
      age: 36,
    },

    {
      id: "P005",
      name: "Ravi Sharma",
      hospitalId: 3,
      gender: "Male",
      age: 51,
    },

  ]


  const doctors = [

    {
      id: "D001",
      name: "Dr. Sharma",
      department: "General Medicine",
      hospitalId: 1,
      status: "Active",
    },

    {
      id: "D002",
      name: "Dr. Kumar",
      department: "Cardiology",
      hospitalId: 1,
      status: "Active",
    },

    {
      id: "D003",
      name: "Dr. Singh",
      department: "Orthopedics",
      hospitalId: 2,
      status: "Active",
    },

    {
      id: "D004",
      name: "Dr. Verma",
      department: "Pediatrics",
      hospitalId: 3,
      status: "Active",
    },

  ]


  const appointments = [

    {
      id: "A001",
      patient: "Rahul Kumar",
      doctor: "Dr. Sharma",
      hospitalId: 1,
      status: "Completed",
      time: "10:30 AM",
    },

    {
      id: "A002",
      patient: "Priya Singh",
      doctor: "Dr. Kumar",
      hospitalId: 1,
      status: "Waiting",
      time: "11:00 AM",
    },

    {
      id: "A003",
      patient: "Amit Kumar",
      doctor: "Dr. Singh",
      hospitalId: 2,
      status: "Confirmed",
      time: "11:30 AM",
    },

    {
      id: "A004",
      patient: "Neha Kumari",
      doctor: "Dr. Verma",
      hospitalId: 3,
      status: "Completed",
      time: "12:00 PM",
    },

  ]


  const laboratory = [

    {
      id: "LAB001",
      patient: "Rahul Kumar",
      test: "CBC",
      amount: 500,
      hospitalId: 1,
      status: "Completed",
    },

    {
      id: "LAB002",
      patient: "Priya Singh",
      test: "Blood Sugar",
      amount: 200,
      hospitalId: 1,
      status: "Completed",
    },

    {
      id: "LAB003",
      patient: "Amit Kumar",
      test: "X-Ray",
      amount: 800,
      hospitalId: 2,
      status: "Pending",
    },

    {
      id: "LAB004",
      patient: "Neha Kumari",
      test: "Urine Test",
      amount: 300,
      hospitalId: 3,
      status: "Completed",
    },

  ]


  const bills = [

    {
      id: "BILL001",
      patient: "Rahul Kumar",
      hospitalId: 1,
      consultation: 500,
      laboratory: 500,
      pharmacy: 150,
      other: 0,
      status: "Paid",
    },

    {
      id: "BILL002",
      patient: "Priya Singh",
      hospitalId: 1,
      consultation: 500,
      laboratory: 200,
      pharmacy: 250,
      other: 100,
      status: "Pending",
    },

    {
      id: "BILL003",
      patient: "Amit Kumar",
      hospitalId: 2,
      consultation: 700,
      laboratory: 800,
      pharmacy: 300,
      other: 0,
      status: "Paid",
    },

  ]


  const beds = [

    {
      id: "BED001",
      ward: "General",
      hospitalId: 1,
      status: "Available",
    },

    {
      id: "BED002",
      ward: "General",
      hospitalId: 1,
      status: "Occupied",
    },

    {
      id: "BED003",
      ward: "ICU",
      hospitalId: 1,
      status: "Occupied",
    },

    {
      id: "BED004",
      ward: "General",
      hospitalId: 2,
      status: "Available",
    },

    {
      id: "BED005",
      ward: "ICU",
      hospitalId: 3,
      status: "Available",
    },

  ]


  // =====================================
  // NO HOSPITAL
  // =====================================

  if (!selectedHospital) {

    return (

      <div className="space-y-6">

        <div>

          <p className="text-blue-600 font-semibold text-sm">
            HOSPITAL REPORTS
          </p>

          <h1 className="text-3xl font-bold text-gray-800 mt-1">
            Reports
          </h1>

        </div>


        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-12 text-center">

          <div className="text-5xl mb-4">
            🏥
          </div>

          <h2 className="text-xl font-bold text-gray-800">
            Select a Hospital
          </h2>

          <p className="text-gray-500 mt-2">
            Select a hospital from the header to view reports.
          </p>

        </div>

      </div>

    )
  }


  // =====================================
  // HOSPITAL FILTERING
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


  const hospitalLaboratory =
    laboratory.filter(
      (test) =>
        test.hospitalId ===
        selectedHospital.id
    )


  const hospitalBills =
    bills.filter(
      (bill) =>
        bill.hospitalId ===
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
  // PHARMACY REVENUE
  // =====================================

  const pharmacyRevenue =
    hospitalSales.reduce(
      (total, sale) =>
        total +
        Number(
          sale.total || 0
        ),
      0
    )


  // =====================================
  // LAB REVENUE
  // =====================================

  const laboratoryRevenue =
    hospitalLaboratory.reduce(
      (total, test) =>
        total +
        Number(
          test.amount || 0
        ),
      0
    )


  // =====================================
  // BILL REVENUE
  // =====================================

  const billingRevenue =
    hospitalBills.reduce(
      (total, bill) =>

        total +

        Number(
          bill.consultation || 0
        ) +

        Number(
          bill.laboratory || 0
        ) +

        Number(
          bill.pharmacy || 0
        ) +

        Number(
          bill.other || 0
        ),

      0
    )


  // =====================================
  // BED STATS
  // =====================================

  const availableBeds =
    hospitalBeds.filter(
      (bed) =>
        bed.status ===
        "Available"
    ).length


  const occupiedBeds =
    hospitalBeds.filter(
      (bed) =>
        bed.status ===
        "Occupied"
    ).length


  const totalBeds =
    hospitalBeds.length


  // =====================================
  // APPOINTMENT STATS
  // =====================================

  const completedAppointments =
    hospitalAppointments.filter(
      (appointment) =>
        appointment.status ===
        "Completed"
    ).length


  const waitingAppointments =
    hospitalAppointments.filter(
      (appointment) =>
        appointment.status ===
        "Waiting"
    ).length


  const confirmedAppointments =
    hospitalAppointments.filter(
      (appointment) =>
        appointment.status ===
        "Confirmed"
    ).length


  // =====================================
  // BILL STATUS
  // =====================================

  const paidBills =
    hospitalBills.filter(
      (bill) =>
        bill.status ===
        "Paid"
    ).length


  const pendingBills =
    hospitalBills.filter(
      (bill) =>
        bill.status ===
        "Pending"
    ).length


  // =====================================
  // TOTAL REVENUE
  // =====================================

  const totalRevenue =
    billingRevenue +
    pharmacyRevenue +
    laboratoryRevenue


  // =====================================
  // RECENT ACTIVITY
  // =====================================

  const recentActivity =
    useMemo(() => [

      {
        icon: "👤",
        title: "Patient Registration",
        text:
          hospitalPatients.length > 0
            ? `${hospitalPatients[0].name} registered`
            : "No recent patient",
        time: "Today",
      },

      {
        icon: "📅",
        title: "Appointment",
        text:
          hospitalAppointments.length > 0
            ? `${hospitalAppointments[0].patient} appointment`
            : "No appointments",
        time: "Today",
      },

      {
        icon: "💊",
        title: "Pharmacy",
        text:
          hospitalSales.length > 0
            ? `${hospitalSales[0].medicineName} dispensed`
            : "No pharmacy activity",
        time: "Today",
      },

      {
        icon: "🧪",
        title: "Laboratory",
        text:
          hospitalLaboratory.length > 0
            ? `${hospitalLaboratory[0].test} completed`
            : "No lab activity",
        time: "Today",
      },

      {
        icon: "🧾",
        title: "Billing",
        text:
          hospitalBills.length > 0
            ? `${hospitalBills[0].id} generated`
            : "No billing activity",
        time: "Today",
      },

    ], [
      hospitalPatients,
      hospitalAppointments,
      hospitalSales,
      hospitalLaboratory,
      hospitalBills,
    ])


  // =====================================
  // REPORT CARD
  // =====================================

  const ReportCard = ({
    title,
    value,
    subtitle,
    icon,
    iconBg,
  }) => (

    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">

      <div className="flex items-center justify-between">

        <div>

          <p className="text-sm text-gray-500">
            {title}
          </p>

          <h3 className="text-3xl font-bold text-gray-800 mt-2">
            {value}
          </h3>

          <p className="text-xs text-gray-500 mt-1">
            {subtitle}
          </p>

        </div>


        <div
          className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${iconBg}`}
        >
          {icon}
        </div>

      </div>

    </div>

  )


  return (

    <div className="space-y-6">


      {/* =====================================
          HEADER
      ===================================== */}

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">

        <div>

          <p className="text-blue-600 font-semibold text-sm">
            HOSPITAL REPORTS
          </p>

          <h1 className="text-3xl font-bold text-gray-800 mt-1">
            Reports
          </h1>

          <p className="text-gray-500 mt-1">
            Complete operational and financial overview.
          </p>

        </div>


        <select

          value={period}

          onChange={(e) =>
            setPeriod(
              e.target.value
            )
          }

          className="border border-gray-300 rounded-xl px-4 py-3 bg-white outline-none focus:ring-2 focus:ring-blue-500"

        >

          <option>
            Today
          </option>

          <option>
            This Week
          </option>

          <option>
            This Month
          </option>

          <option>
            This Year
          </option>

        </select>

      </div>


      {/* =====================================
          HOSPITAL
      ===================================== */}

      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">

        <div className="flex items-center gap-4">

          <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">
            🏥
          </div>

          <div>

            <p className="text-xs text-gray-500">
              Selected Hospital
            </p>

            <h2 className="font-bold text-gray-800 text-lg">
              {selectedHospital.name}
            </h2>

            <p className="text-sm text-gray-500">
              📍 {selectedHospital.address}
            </p>

          </div>

        </div>

      </div>


      {/* =====================================
          OVERVIEW
      ===================================== */}

      <div>

        <h2 className="text-xl font-bold text-gray-800 mb-4">
          Overview
        </h2>


        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">


          <ReportCard
            title="Patients"
            value={
              hospitalPatients.length
            }
            subtitle="Registered patients"
            icon="👥"
            iconBg="bg-blue-100"
          />


          <ReportCard
            title="Doctors"
            value={
              hospitalDoctors.length
            }
            subtitle="Active doctors"
            icon="👨‍⚕️"
            iconBg="bg-green-100"
          />


          <ReportCard
            title="Appointments"
            value={
              hospitalAppointments.length
            }
            subtitle="Appointments"
            icon="📅"
            iconBg="bg-orange-100"
          />


          <ReportCard
            title="Prescriptions"
            value={
              hospitalPrescriptions.length
            }
            subtitle="Doctor prescriptions"
            icon="🧾"
            iconBg="bg-purple-100"
          />

        </div>

      </div>


      {/* =====================================
          REVENUE
      ===================================== */}

      <div>

        <h2 className="text-xl font-bold text-gray-800 mb-4">
          Financial Report
        </h2>


        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">


          <ReportCard
            title="Total Revenue"
            value={`₹${totalRevenue.toLocaleString("en-IN")}`}
            subtitle="Overall revenue"
            icon="💰"
            iconBg="bg-green-100"
          />


          <ReportCard
            title="Pharmacy"
            value={`₹${pharmacyRevenue.toLocaleString("en-IN")}`}
            subtitle="Medicine sales"
            icon="💊"
            iconBg="bg-purple-100"
          />


          <ReportCard
            title="Laboratory"
            value={`₹${laboratoryRevenue.toLocaleString("en-IN")}`}
            subtitle="Laboratory revenue"
            icon="🧪"
            iconBg="bg-blue-100"
          />


          <ReportCard
            title="Bills"
            value={
              hospitalBills.length
            }
            subtitle={`${paidBills} paid • ${pendingBills} pending`}
            icon="🧾"
            iconBg="bg-orange-100"
          />

        </div>

      </div>


      {/* =====================================
          APPOINTMENT REPORT
      ===================================== */}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">


        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-6">

          <h2 className="text-lg font-bold text-gray-800">
            Appointment Report
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Current appointment status.
          </p>


          <div className="mt-6 space-y-5">


            <div>

              <div className="flex justify-between mb-2">

                <span className="text-sm text-gray-600">
                  Completed
                </span>

                <span className="font-semibold text-green-600">
                  {completedAppointments}
                </span>

              </div>


              <div className="h-2 bg-gray-100 rounded-full">

                <div
                  className="h-2 bg-green-500 rounded-full"
                  style={{
                    width:
                      hospitalAppointments.length
                        ? `${(completedAppointments / hospitalAppointments.length) * 100}%`
                        : "0%",
                  }}
                />

              </div>

            </div>


            <div>

              <div className="flex justify-between mb-2">

                <span className="text-sm text-gray-600">
                  Waiting
                </span>

                <span className="font-semibold text-orange-600">
                  {waitingAppointments}
                </span>

              </div>


              <div className="h-2 bg-gray-100 rounded-full">

                <div
                  className="h-2 bg-orange-500 rounded-full"
                  style={{
                    width:
                      hospitalAppointments.length
                        ? `${(waitingAppointments / hospitalAppointments.length) * 100}%`
                        : "0%",
                  }}
                />

              </div>

            </div>


            <div>

              <div className="flex justify-between mb-2">

                <span className="text-sm text-gray-600">
                  Confirmed
                </span>

                <span className="font-semibold text-blue-600">
                  {confirmedAppointments}
                </span>

              </div>


              <div className="h-2 bg-gray-100 rounded-full">

                <div
                  className="h-2 bg-blue-500 rounded-full"
                  style={{
                    width:
                      hospitalAppointments.length
                        ? `${(confirmedAppointments / hospitalAppointments.length) * 100}%`
                        : "0%",
                  }}
                />

              </div>

            </div>

          </div>

        </div>


        {/* =====================================
            BED REPORT
        ===================================== */}

        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-6">

          <h2 className="text-lg font-bold text-gray-800">
            Bed Report
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Current hospital bed occupancy.
          </p>


          <div className="grid grid-cols-3 gap-4 mt-6">


            <div className="bg-blue-50 rounded-xl p-4 text-center">

              <p className="text-xs text-gray-500">
                Total
              </p>

              <p className="text-2xl font-bold text-blue-600 mt-2">
                {totalBeds}
              </p>

            </div>


            <div className="bg-green-50 rounded-xl p-4 text-center">

              <p className="text-xs text-gray-500">
                Available
              </p>

              <p className="text-2xl font-bold text-green-600 mt-2">
                {availableBeds}
              </p>

            </div>


            <div className="bg-orange-50 rounded-xl p-4 text-center">

              <p className="text-xs text-gray-500">
                Occupied
              </p>

              <p className="text-2xl font-bold text-orange-600 mt-2">
                {occupiedBeds}
              </p>

            </div>

          </div>


          <div className="mt-6">

            <div className="flex justify-between text-sm mb-2">

              <span className="text-gray-600">
                Occupancy
              </span>

              <span className="font-semibold">
                {
                  totalBeds
                    ? Math.round(
                      (occupiedBeds /
                        totalBeds) *
                      100
                    )
                    : 0
                }%
              </span>

            </div>


            <div className="h-3 bg-gray-100 rounded-full">

              <div
                className="h-3 bg-orange-500 rounded-full"
                style={{
                  width:
                    totalBeds
                      ? `${(occupiedBeds / totalBeds) * 100}%`
                      : "0%",
                }}
              />

            </div>

          </div>

        </div>

      </div>


      {/* =====================================
          DEPARTMENT REPORT
      ===================================== */}

      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm">

        <div className="p-6 border-b">

          <h2 className="text-lg font-bold text-gray-800">
            Doctor Departments
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Doctors working in this hospital.
          </p>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-gray-50">

              <tr>

                <th className="text-left px-6 py-4 text-sm">
                  Doctor
                </th>

                <th className="text-left px-6 py-4 text-sm">
                  Department
                </th>

                <th className="text-left px-6 py-4 text-sm">
                  Status
                </th>

              </tr>

            </thead>


            <tbody>

              {hospitalDoctors.map(
                (doctor) => (

                  <tr
                    key={doctor.id}
                    className="border-t"
                  >

                    <td className="px-6 py-4 font-semibold">
                      {doctor.name}
                    </td>

                    <td className="px-6 py-4 text-gray-600">
                      {doctor.department}
                    </td>

                    <td className="px-6 py-4">

                      <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                        {doctor.status}
                      </span>

                    </td>

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      </div>


      {/* =====================================
          LAB REPORT
      ===================================== */}

      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm">

        <div className="p-6 border-b">

          <h2 className="text-lg font-bold text-gray-800">
            Laboratory Report
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Laboratory activity for this hospital.
          </p>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-gray-50">

              <tr>

                <th className="text-left px-6 py-4 text-sm">
                  Test ID
                </th>

                <th className="text-left px-6 py-4 text-sm">
                  Patient
                </th>

                <th className="text-left px-6 py-4 text-sm">
                  Test
                </th>

                <th className="text-left px-6 py-4 text-sm">
                  Amount
                </th>

                <th className="text-left px-6 py-4 text-sm">
                  Status
                </th>

              </tr>

            </thead>


            <tbody>

              {hospitalLaboratory.map(
                (test) => (

                  <tr
                    key={test.id}
                    className="border-t"
                  >

                    <td className="px-6 py-4 font-semibold text-blue-600">
                      {test.id}
                    </td>

                    <td className="px-6 py-4">
                      {test.patient}
                    </td>

                    <td className="px-6 py-4">
                      {test.test}
                    </td>

                    <td className="px-6 py-4 font-semibold">
                      ₹
                      {test.amount.toLocaleString(
                        "en-IN"
                      )}
                    </td>

                    <td className="px-6 py-4">

                      <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                        {test.status}
                      </span>

                    </td>

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      </div>


      {/* =====================================
          RECENT ACTIVITY
      ===================================== */}

      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm">

        <div className="p-6 border-b">

          <h2 className="text-lg font-bold text-gray-800">
            Recent Hospital Activity
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Latest activities for {selectedHospital.name}.
          </p>

        </div>


        <div className="divide-y">

          {recentActivity.map(
            (activity, index) => (

              <div
                key={index}
                className="p-5 flex items-center gap-4"
              >

                <div className="w-11 h-11 bg-gray-100 rounded-xl flex items-center justify-center text-xl">
                  {activity.icon}
                </div>


                <div className="flex-1">

                  <p className="font-semibold text-gray-800">
                    {activity.title}
                  </p>

                  <p className="text-sm text-gray-500">
                    {activity.text}
                  </p>

                </div>


                <span className="text-xs text-gray-400">
                  {activity.time}
                </span>

              </div>

            )
          )}

        </div>

      </div>


      {/* =====================================
          REPORT FOOTER
      ===================================== */}

      <div className="bg-blue-50 border border-blue-100 rounded-2xl p-5">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">

          <div>

            <p className="font-semibold text-blue-800">
              Report Period
            </p>

            <p className="text-sm text-blue-600">
              {period} • {selectedHospital.name}
            </p>

          </div>


          <p className="text-sm text-blue-600">
            Hospital data is isolated using hospital ID.
          </p>

        </div>

      </div>

    </div>
  )
}


export default Reports