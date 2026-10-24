import { useEffect, useState } from "react"
import api from "../services/api.js"
import { usePatient } from "../assets/context/PatientContext.jsx"


function Reports() {

  // =====================================
  // SELECTED HOSPITAL
  // =====================================

  const { selectedHospital } = usePatient()


  // =====================================
  // REPORT PERIOD
  // =====================================

  const [period, setPeriod] =
    useState("Today")


  // =====================================
  // LIVE DATA (analytics API, counted on the server)
  // =====================================

  const PERIODS = {
    Today: "today",
    "This Week": "last_7_days",
    "This Month": "this_month",
    "This Year": "this_year",
  }

  const [kpis, setKpis] = useState(null)
  const [hospitalDoctors, setHospitalDoctors] = useState([])
  const [hospitalLaboratory, setHospitalLaboratory] = useState([])
  const [prescriptionTotal, setPrescriptionTotal] = useState(0)
  const [loadError, setLoadError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!selectedHospital) return
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setLoadError("")
      const results = await Promise.allSettled([
        api.reports.dashboard(selectedHospital.id, PERIODS[period] || "today"),
        api.doctors.list(selectedHospital.id),
        api.laboratory.tests.list(selectedHospital.id),
        api.prescriptions.list({ hospitalId: selectedHospital.id }),
      ])
      if (cancelled) return
      const [dash, docs, labs, rx] = results
      const rows = (r) => (r.status === "fulfilled" ? (Array.isArray(r.value) ? r.value : r.value?.results || []) : [])
      setKpis(dash.status === "fulfilled" ? dash.value : null)
      setHospitalDoctors(rows(docs).map((d) => ({
        id: d.id, name: d.name, department: d.specialization || "", status: d.status,
      })))
      setHospitalLaboratory(rows(labs).slice(0, 10).map((t) => ({
        id: `LAB-${t.id}`, test: t.name, patient: t.patient_name, status: t.status,
      })))
      setPrescriptionTotal(rx.status === "fulfilled" ? rx.value?.count ?? rows(rx).length : 0)
      const failed = results.filter((r) => r.status === "rejected")
      if (failed.length) setLoadError(failed[0].reason?.message || "Some report data could not be loaded.")
      setLoading(false)
    }
    load()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHospital?.id, period])

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
  // FIGURES FROM THE KPIs
  // =====================================

  const k = kpis || {}
  const patientsTotal = k.patients?.total ?? 0
  const doctorsTotal = k.doctors?.total ?? hospitalDoctors.length
  const appointmentsTotal = k.appointments?.period_total ?? 0
  const completedAppointments = k.appointments?.completed ?? 0
  const confirmedAppointments = k.appointments?.scheduled ?? 0
  const waitingAppointments = k.queue?.waiting ?? 0
  const billsTotal = k.billing?.period_invoices ?? 0
  const paidBills = k.billing?.paid ?? 0
  const pendingBills = (k.billing?.unpaid ?? 0) + (k.billing?.partial ?? 0)
  const pharmacyRevenue = Number(k.pharmacy?.period_revenue ?? 0)
  const billingRevenue = Number(k.billing?.period_revenue ?? 0)
  const totalRevenue = billingRevenue + pharmacyRevenue
  const totalBeds = k.ipd?.total_beds ?? 0
  const availableBeds = k.ipd?.available_beds ?? 0
  const occupiedBeds = k.ipd?.occupied_beds ?? 0
  // Lab tests carry no price in this system, so lab revenue is not reported.
  const laboratoryRevenue = null
  // No activity feed API yet; the section shows only what the server reports.
  const recentActivity = []

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

      {loadError && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm" role="alert">
          {loadError}
        </div>
      )}
      {loading && (
        <p className="text-sm text-gray-500" role="status">Loading report figures…</p>
      )}

      <div>

        <h2 className="text-xl font-bold text-gray-800 mb-4">
          Overview
        </h2>


        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">


          <ReportCard
            title="Patients"
            value={
              patientsTotal
            }
            subtitle="Registered patients"
            icon="👥"
            iconBg="bg-blue-100"
          />


          <ReportCard
            title="Doctors"
            value={
              doctorsTotal
            }
            subtitle="Active doctors"
            icon="👨‍⚕️"
            iconBg="bg-green-100"
          />


          <ReportCard
            title="Appointments"
            value={
              appointmentsTotal
            }
            subtitle="Appointments"
            icon="📅"
            iconBg="bg-orange-100"
          />


          <ReportCard
            title="Prescriptions"
            value={
              prescriptionTotal
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
            value={laboratoryRevenue === null ? "Not tracked" : `₹${laboratoryRevenue.toLocaleString("en-IN")}`}
            subtitle="Laboratory revenue"
            icon="🧪"
            iconBg="bg-blue-100"
          />


          <ReportCard
            title="Bills"
            value={
              billsTotal
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
                      appointmentsTotal
                        ? `${(completedAppointments / appointmentsTotal) * 100}%`
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
                      appointmentsTotal
                        ? `${(waitingAppointments / appointmentsTotal) * 100}%`
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
                      appointmentsTotal
                        ? `${(confirmedAppointments / appointmentsTotal) * 100}%`
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