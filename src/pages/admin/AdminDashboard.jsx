import { useState } from "react"

function AdminDashboard() {
  const [activities] = useState([
    {
      id: 1,
      text: "New doctor added",
      user: "Admin",
      time: "10 minutes ago",
    },
    {
      id: 2,
      text: "New patient registered",
      user: "Reception",
      time: "25 minutes ago",
    },
    {
      id: 3,
      text: "Department updated",
      user: "Admin",
      time: "1 hour ago",
    },
    {
      id: 4,
      text: "Nurse account activated",
      user: "Admin",
      time: "2 hours ago",
    },
    {
      id: 5,
      text: "Appointment created",
      user: "Reception",
      time: "3 hours ago",
    },
  ])

  const stats = [
    {
      title: "Total Users",
      value: 125,
      description: "Registered users",
      link: "/admin/users",
    },
    {
      title: "Hospitals",
      value: 3,
      description: "Active hospitals",
      link: "/admin/hospitals",
    },
    {
      title: "Doctors",
      value: 40,
      description: "Medical doctors",
      link: "/doctors",
    },
    {
      title: "Nurses",
      value: 65,
      description: "Nursing staff",
      link: "/nurses",
    },
    {
      title: "Compounders",
      value: 18,
      description: "Pharmacy staff",
      link: "/compounder",
    },
    {
      title: "Departments",
      value: 19,
      description: "Hospital departments",
      link: "/admin/departments",
    },
    {
      title: "Patients",
      value: 1250,
      description: "Registered patients",
      link: "/patients",
    },
    {
      title: "Appointments",
      value: 86,
      description: "Today's appointments",
      link: "/appointments",
    },
  ]

  const quickActions = [
    {
      title: "Manage Users",
      description: "Add, edit and manage users",
      link: "/admin/users",
    },
    {
      title: "Manage Hospitals",
      description: "Manage hospital information",
      link: "/admin/hospitals",
    },
    {
      title: "Manage Roles",
      description: "Configure user roles",
      link: "/admin/roles",
    },
    {
      title: "Departments",
      description: "Manage hospital departments",
      link: "/admin/departments",
    },
    {
      title: "Permissions",
      description: "Control module permissions",
      link: "/admin/permissions",
    },
    {
      title: "Doctors",
      description: "View doctor management",
      link: "/doctors",
    },
    {
      title: "Nurses",
      description: "View nursing management",
      link: "/nurses",
    },
    {
      title: "Compounders",
      description: "View compounder management",
      link: "/compounder",
    },
  ]

  const handleNavigation = (link) => {
    window.location.href = link
  }

  return (
    <div className="p-6">

      {/* Header */}
      <div className="mb-8">

        <h1 className="text-3xl font-bold text-gray-800">
          Admin Dashboard
        </h1>

        <p className="text-gray-500 mt-1">
          Manage and monitor the complete hospital system
        </p>

      </div>

      {/* Welcome Card */}
      <div className="bg-blue-600 text-white rounded-2xl p-6 mb-6">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5">

          <div>

            <p className="text-blue-100 text-sm mb-1">
              Welcome back
            </p>

            <h2 className="text-2xl font-bold">
              Hospital Administrator
            </h2>

            <p className="text-blue-100 mt-2">
              Manage hospitals, staff, users,
              departments and permissions from one place.
            </p>

          </div>

          <div className="text-5xl">
            🏥
          </div>

        </div>

      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">

        {stats.map((stat) => (

          <div
            key={stat.title}
            onClick={() =>
              handleNavigation(stat.link)
            }
            className="bg-white rounded-xl shadow p-5 cursor-pointer hover:shadow-lg transition"
          >

            <p className="text-gray-500 text-sm">
              {stat.title}
            </p>

            <h2 className="text-3xl font-bold text-gray-800 mt-2">
              {stat.value}
            </h2>

            <p className="text-sm text-gray-400 mt-1">
              {stat.description}
            </p>

          </div>

        ))}

      </div>

      {/* Quick Management */}
      <div className="mb-8">

        <div className="mb-4">

          <h2 className="text-xl font-bold text-gray-800">
            Quick Management
          </h2>

          <p className="text-gray-500 text-sm mt-1">
            Quickly access administration modules
          </p>

        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

          {quickActions.map((action) => (

            <button
              key={action.title}
              onClick={() =>
                handleNavigation(action.link)
              }
              className="bg-white rounded-xl shadow p-5 text-left hover:shadow-lg transition border border-transparent hover:border-blue-200"
            >

              <h3 className="font-semibold text-gray-800">
                {action.title}
              </h3>

              <p className="text-sm text-gray-500 mt-2">
                {action.description}
              </p>

              <span className="text-blue-600 text-sm font-medium inline-block mt-4">
                Open →
              </span>

            </button>

          ))}

        </div>

      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Recent Activity */}
        <div className="bg-white rounded-xl shadow">

          <div className="p-5 border-b">

            <h2 className="text-xl font-bold text-gray-800">
              Recent Activity
            </h2>

            <p className="text-sm text-gray-500 mt-1">
              Latest activities in the system
            </p>

          </div>

          <div className="divide-y">

            {activities.map((activity) => (

              <div
                key={activity.id}
                className="p-5 flex items-start gap-4"
              >

                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                  ✓
                </div>

                <div className="flex-1">

                  <p className="font-medium text-gray-800">
                    {activity.text}
                  </p>

                  <p className="text-sm text-gray-500 mt-1">
                    By {activity.user}
                  </p>

                  <p className="text-xs text-gray-400 mt-1">
                    {activity.time}
                  </p>

                </div>

              </div>

            ))}

          </div>

        </div>

        {/* System Overview */}
        <div className="bg-white rounded-xl shadow">

          <div className="p-5 border-b">

            <h2 className="text-xl font-bold text-gray-800">
              System Overview
            </h2>

            <p className="text-sm text-gray-500 mt-1">
              Current hospital system status
            </p>

          </div>

          <div className="p-5 space-y-5">

            {/* Hospital Status */}
            <div>

              <div className="flex justify-between mb-2">

                <span className="font-medium">
                  Hospitals
                </span>

                <span className="text-green-600">
                  3 Active
                </span>

              </div>

              <div className="w-full bg-gray-200 rounded-full h-2">

                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: "100%" }}
                />

              </div>

            </div>

            {/* User Status */}
            <div>

              <div className="flex justify-between mb-2">

                <span className="font-medium">
                  Active Users
                </span>

                <span className="text-blue-600">
                  118 / 125
                </span>

              </div>

              <div className="w-full bg-gray-200 rounded-full h-2">

                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: "94%" }}
                />

              </div>

            </div>

            {/* Departments */}
            <div>

              <div className="flex justify-between mb-2">

                <span className="font-medium">
                  Departments
                </span>

                <span className="text-purple-600">
                  19 Active
                </span>

              </div>

              <div className="w-full bg-gray-200 rounded-full h-2">

                <div
                  className="bg-purple-500 h-2 rounded-full"
                  style={{ width: "90%" }}
                />

              </div>

            </div>

            {/* Today's Appointments */}
            <div>

              <div className="flex justify-between mb-2">

                <span className="font-medium">
                  Today&apos;s Appointments
                </span>

                <span className="text-orange-600">
                  86
                </span>

              </div>

              <div className="w-full bg-gray-200 rounded-full h-2">

                <div
                  className="bg-orange-500 h-2 rounded-full"
                  style={{ width: "72%" }}
                />

              </div>

            </div>

          </div>

          {/* System Status */}
          <div className="p-5 border-t">

            <div className="flex items-center gap-3">

              <div className="w-3 h-3 bg-green-500 rounded-full" />

              <div>

                <p className="font-medium text-gray-800">
                  System Operational
                </p>

                <p className="text-sm text-gray-500">
                  All major modules are running
                </p>

              </div>

            </div>

          </div>

        </div>

      </div>

    </div>
  )
}

export default AdminDashboard