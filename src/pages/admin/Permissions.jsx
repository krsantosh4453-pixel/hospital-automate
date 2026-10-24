import { useRole, ALL_MODULES } from "../../assets/context/RoleContext.jsx"

function Permissions() {
  const modules = ALL_MODULES

  const {
    roles,
    updateRolePermissions,
  } = useRole()

  const [selectedRoleId, setSelectedRoleId] = useState(1)

  const selectedRole = roles.find((role) => role.id === selectedRoleId) || roles[0]

  const hasPermission = (module, action) => {
    return selectedRole?.permissions?.[module]?.includes(action) || false
  }

  const togglePermission = (module, action) => {
    if (!selectedRole) return

    const currentPermissions = selectedRole.permissions?.[module] || []
    const exists = currentPermissions.includes(action)

    const updatedPermissions = exists
      ? currentPermissions.filter((item) => item !== action)
      : [...currentPermissions, action]

    const newRolePermissions = {
      ...selectedRole.permissions,
      [module]: updatedPermissions,
    }

    updateRolePermissions(selectedRoleId, newRolePermissions)
  }

  const toggleModule = (module) => {
    if (!selectedRole) return
    const allActions = ["View", "Add", "Edit", "Delete"]
    const modulePermissions = selectedRole.permissions?.[module] || []
    const allSelected = allActions.every((action) => modulePermissions.includes(action))

    const newRolePermissions = {
      ...selectedRole.permissions,
      [module]: allSelected ? [] : allActions,
    }

    updateRolePermissions(selectedRoleId, newRolePermissions)
  }

  const selectAll = () => {
    if (!selectedRole) return
    const allActions = ["View", "Add", "Edit", "Delete"]
    const updatedPermissions = {}
    modules.forEach((module) => {
      updatedPermissions[module] = [...allActions]
    })
    updateRolePermissions(selectedRoleId, updatedPermissions)
  }

  const clearAll = () => {
    if (!selectedRole) return
    const updatedPermissions = {}
    modules.forEach((module) => {
      updatedPermissions[module] = []
    })
    updateRolePermissions(selectedRoleId, updatedPermissions)
  }

  const permissionCount = selectedRole
    ? Object.values(selectedRole.permissions || {}).reduce(
        (total, permissions) => total + permissions.length,
        0
      )
    : 0

  const { activeRoleName, switchRole } = useRole()

  const roleIcons = {
    Admin: "👑",
    Doctor: "👨‍⚕️",
    Nurse: "👩‍⚕️",
    Compounder: "🧑‍💼",
    Reception: "🏥",
    Patient: "👤",
  }

  return (
    <div className="p-4 sm:p-6 space-y-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">
            Permissions & Role Access
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Control exact modules and actions for each hospital role
          </p>
        </div>

        {/* Current Active Role Badge & Switcher */}
        <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-xl shadow-xs border border-gray-200">
          <span className="text-xs text-gray-500 font-medium">Your Current Role:</span>
          <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100">
            {roleIcons[activeRoleName] || "👤"} {activeRoleName}
          </span>
        </div>
      </div>

      {/* Role Selection Tabs & Controls */}
      <div className="bg-white rounded-2xl shadow-xs border border-gray-100 p-5 space-y-4">
        <div>
          <label className="block text-xs uppercase font-semibold text-gray-500 tracking-wider mb-2">
            Select Role to Configure
          </label>
          <div className="flex flex-wrap gap-2">
            {roles.map((role) => {
              const isSelected = role.id === selectedRoleId
              const isCurrent = role.name === activeRoleName

              return (
                <button
                  key={role.id}
                  type="button"
                  onClick={() => setSelectedRoleId(role.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-xs transition cursor-pointer ${
                    isSelected
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-gray-50 hover:bg-gray-100 text-gray-700 border border-gray-200"
                  }`}
                >
                  <span className="text-sm">{roleIcons[role.name] || "👤"}</span>
                  <span className="font-semibold">{role.name}</span>
                  {isCurrent && (
                    <span className="text-[10px] bg-white/20 px-1.5 py-0.5 rounded-full font-bold">
                      Current
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Selected Role Info Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-gray-100">
          <div className="flex items-center gap-3">
            <div className="bg-blue-50 text-blue-700 px-3.5 py-1.5 rounded-xl text-xs font-semibold border border-blue-100">
              Role: <span className="font-bold">{selectedRole?.name}</span>
            </div>
            <div className="bg-green-50 text-green-700 px-3.5 py-1.5 rounded-xl text-xs font-semibold border border-green-100">
              Total Permissions: <span className="font-bold">{permissionCount}</span>
            </div>
          </div>

          {/* Button to test this role immediately */}
          {selectedRole && selectedRole.name !== activeRoleName && (
            <button
              type="button"
              onClick={() => switchRole(selectedRole.name)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold transition cursor-pointer shadow-sm"
            >
              <span>Switch App to &quot;{selectedRole.name}&quot; View</span>
            </button>
          )}
        </div>
      </div>

      {/* Permission Controls */}
      <div className="bg-white rounded-xl shadow mb-6">

        <div className="p-5 border-b flex flex-col md:flex-row md:items-center md:justify-between gap-4">

          <div>
            <h2 className="text-xl font-bold">
              Access Control
            </h2>

            <p className="text-sm text-gray-500 mt-1">
              Manage permissions for{" "}
              <span className="font-medium">
                {selectedRole?.name}
              </span>
            </p>
          </div>

          <div className="flex gap-2">

            <button
              onClick={selectAll}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm"
            >
              Select All
            </button>

            <button
              onClick={clearAll}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm"
            >
              Clear All
            </button>

          </div>

        </div>

        {/* Permission Table */}
        <div className="overflow-x-auto">

          <table className="w-full min-w-[800px]">

            <thead className="bg-gray-100">

              <tr>

                <th className="p-4 text-left">
                  Module
                </th>

                <th className="p-4 text-center">
                  View
                </th>

                <th className="p-4 text-center">
                  Add
                </th>

                <th className="p-4 text-center">
                  Edit
                </th>

                <th className="p-4 text-center">
                  Delete
                </th>

                <th className="p-4 text-center">
                  All
                </th>

              </tr>

            </thead>

            <tbody>

              {modules.map((module) => {

                const actions = [
                  "View",
                  "Add",
                  "Edit",
                  "Delete",
                ]

                const modulePermissions =
                  selectedRole?.permissions?.[
                  module
                  ] || []

                const allSelected =
                  actions.every((action) =>
                    modulePermissions.includes(
                      action
                    )
                  )

                return (
                  <tr
                    key={module}
                    className="border-t hover:bg-gray-50"
                  >

                    <td className="p-4">

                      <span className="font-medium text-gray-800">
                        {module}
                      </span>

                    </td>

                    {actions.map((action) => (

                      <td
                        key={action}
                        className="p-4 text-center"
                      >

                        <input
                          type="checkbox"
                          checked={hasPermission(
                            module,
                            action
                          )}
                          onChange={() =>
                            togglePermission(
                              module,
                              action
                            )
                          }
                          className="w-5 h-5 cursor-pointer"
                        />

                      </td>

                    ))}

                    <td className="p-4 text-center">

                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={() =>
                          toggleModule(module)
                        }
                        className="w-5 h-5 cursor-pointer"
                      />

                    </td>

                  </tr>
                )
              })}

            </tbody>

          </table>

        </div>

      </div>

      {/* Information */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">

        <h3 className="font-semibold text-blue-800 mb-2">
          Permission Guide
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-blue-700">

          <p>
            <strong>View:</strong> User can see
            module information.
          </p>

          <p>
            <strong>Add:</strong> User can create
            new records.
          </p>

          <p>
            <strong>Edit:</strong> User can update
            existing records.
          </p>

          <p>
            <strong>Delete:</strong> User can remove
            records.
          </p>

        </div>

      </div>

    </div>
  )
}

export default Permissions