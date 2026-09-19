import { useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"

function Settings() {
  const { selectedHospital } = usePatient()

  const [settings, setSettings] = useState({
    hospitalName: selectedHospital?.name || "",
    phone: selectedHospital?.phone || "",
    email: selectedHospital?.email || "",
    address: selectedHospital?.address || "",
    appointmentDuration: 15,
    queueEnabled: true,
    pharmacyEnabled: true,
    laboratoryEnabled: true,
    billingEnabled: true,
    notificationsEnabled: true,
  })

  const [saved, setSaved] = useState(false)

  if (!selectedHospital) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6">
          <h1 className="text-2xl font-bold text-gray-800">
            Settings
          </h1>

          <p className="text-gray-600 mt-2">
            Please select a hospital to view hospital settings.
          </p>
        </div>
      </div>
    )
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target

    setSettings((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }))

    setSaved(false)
  }

  const handleSave = () => {
    // Later this will be connected to Django backend
    setSaved(true)

    setTimeout(() => {
      setSaved(false)
    }, 3000)
  }

  return (
    <div className="p-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            Settings
          </h1>

          <p className="text-gray-500 mt-1">
            Manage settings for the selected hospital.
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
          <p className="text-xs text-gray-500">
            Selected Hospital
          </p>

          <p className="font-semibold text-blue-700">
            {selectedHospital.name}
          </p>
        </div>
      </div>

      {/* Hospital Information */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mb-6">

        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">
            Hospital Information
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Basic information of the selected hospital.
          </p>
        </div>

        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-5">

          {/* Hospital Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Hospital Name
            </label>

            <input
              type="text"
              name="hospitalName"
              value={settings.hospitalName}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Hospital name"
            />
          </div>

          {/* Phone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Phone Number
            </label>

            <input
              type="text"
              name="phone"
              value={settings.phone}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Hospital phone"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>

            <input
              type="email"
              name="email"
              value={settings.email}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Hospital email"
            />
          </div>

          {/* Appointment Duration */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Appointment Duration
            </label>

            <select
              name="appointmentDuration"
              value={settings.appointmentDuration}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={10}>10 Minutes</option>
              <option value={15}>15 Minutes</option>
              <option value={20}>20 Minutes</option>
              <option value={30}>30 Minutes</option>
              <option value={45}>45 Minutes</option>
              <option value={60}>60 Minutes</option>
            </select>
          </div>

          {/* Address */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Hospital Address
            </label>

            <textarea
              name="address"
              value={settings.address}
              onChange={handleChange}
              rows="3"
              className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Hospital address"
            />
          </div>

        </div>
      </div>

      {/* Hospital Modules */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mb-6">

        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">
            Hospital Modules
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Enable or disable modules for this hospital.
          </p>
        </div>

        <div className="p-6 space-y-4">

          {/* Queue */}
          <SettingToggle
            title="Queue Management"
            description="Manage patient tokens and waiting queues."
            name="queueEnabled"
            checked={settings.queueEnabled}
            onChange={handleChange}
          />

          {/* Pharmacy */}
          <SettingToggle
            title="Pharmacy"
            description="Manage medicines, prescriptions and pharmacy sales."
            name="pharmacyEnabled"
            checked={settings.pharmacyEnabled}
            onChange={handleChange}
          />

          {/* Laboratory */}
          <SettingToggle
            title="Laboratory"
            description="Manage laboratory tests and reports."
            name="laboratoryEnabled"
            checked={settings.laboratoryEnabled}
            onChange={handleChange}
          />

          {/* Billing */}
          <SettingToggle
            title="Billing"
            description="Manage hospital billing and payments."
            name="billingEnabled"
            checked={settings.billingEnabled}
            onChange={handleChange}
          />

          {/* Notifications */}
          <SettingToggle
            title="Notifications"
            description="Enable hospital notifications and alerts."
            name="notificationsEnabled"
            checked={settings.notificationsEnabled}
            onChange={handleChange}
          />

        </div>
      </div>

      {/* Save Section */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">

        {saved ? (
          <div className="text-green-600 font-medium">
            ✓ Settings saved successfully
          </div>
        ) : (
          <div className="text-sm text-gray-500">
            Changes apply to {selectedHospital.name}
          </div>
        )}

        <button
          onClick={handleSave}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-3 rounded-xl transition"
        >
          Save Settings
        </button>

      </div>

    </div>
  )
}


/* Reusable Toggle Component */

function SettingToggle({
  title,
  description,
  name,
  checked,
  onChange,
}) {
  return (
    <div className="flex items-center justify-between gap-4 p-4 border border-gray-100 rounded-xl">

      <div>
        <h3 className="font-medium text-gray-800">
          {title}
        </h3>

        <p className="text-sm text-gray-500 mt-1">
          {description}
        </p>
      </div>

      <label className="relative inline-flex items-center cursor-pointer shrink-0">

        <input
          type="checkbox"
          name={name}
          checked={checked}
          onChange={onChange}
          className="sr-only peer"
        />

        <div className="w-11 h-6 bg-gray-300 rounded-full peer peer-checked:bg-blue-600 transition"></div>

        <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition peer-checked:translate-x-5"></div>

      </label>

    </div>
  )
}

export default Settings