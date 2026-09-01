function StatCard({ title, value, icon, color, subtitle }) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">

      {/* Top Section */}
      <div className="flex items-start justify-between">

        {/* Title */}
        <div>
          <p className="text-sm font-medium text-gray-500">
            {title}
          </p>

          {/* Value */}
          <h2 className="text-3xl font-bold text-gray-800 mt-2">
            {value}
          </h2>
        </div>

        {/* Icon */}
        <div
          className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${color}`}
        >
          {icon}
        </div>

      </div>

      {/* Bottom Section */}
      {subtitle && (
        <p className="text-xs text-gray-500 mt-4">
          {subtitle}
        </p>
      )}

    </div>
  )
}

export default StatCard