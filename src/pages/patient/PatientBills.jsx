import { useEffect, useState } from "react"
import { useAuth } from "../../assets/context/AuthContext.jsx"
import api from "../../services/api.js"
import { CreditCardIcon, ReceiptIcon, TriangleAlertIcon } from "lucide-react"

function PatientBills() {
  const { patient } = useAuth()
  const [bills, setBills] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState("all")

  useEffect(() => {
    if (!patient?.id) return

    const fetchBills = async () => {
      setLoading(true)
      try {
        const data = await api.billing.invoices.list()
        const allBills = data?.results || data || []
        const patientBills = allBills.filter(
          (b) => String(b.patient) === String(patient.id)
        )
        setBills(patientBills)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchBills()
  }, [patient?.id])

  const formatDate = (dateStr) => {
    if (!dateStr) return "—"
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
  }

  const formatCurrency = (amount) => {
    if (!amount) return "₹0"
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount)
  }

  const filteredBills = bills.filter((bill) => {
    if (filter === "all") return true
    if (filter === "paid") return bill.status === "Paid"
    if (filter === "unpaid") return bill.status === "Unpaid"
    if (filter === "partial") return bill.status === "Partial"
    return true
  })

  const totalUnpaid = bills
    .filter(b => b.status === "Unpaid" || b.status === "Partial")
    .reduce((sum, b) => sum + (Number(b.total_amount) - Number(b.paid_amount || 0)), 0)

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Bills & Payments</h1>
          <p className="text-gray-500 mt-1">View and pay your medical bills</p>
        </div>
        {totalUnpaid > 0 && (
          <div className="bg-orange-50 border border-orange-200 text-orange-700 rounded-xl px-4 py-3 text-sm font-medium">
            <TriangleAlertIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> Total Outstanding: {formatCurrency(totalUnpaid)}
          </div>
        )}
      </div>

      <div className="flex gap-2 flex-wrap">
        {["all", "unpaid", "partial", "paid"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
              filter === f
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-200"
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm"><TriangleAlertIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> {error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : filteredBills.length > 0 ? (
        <div className="space-y-4">
          {filteredBills.map((bill) => (
            <div key={bill.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl"><ReceiptIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></span>
                    <div>
                      <h3 className="font-semibold text-gray-800 text-lg">Invoice {bill.invoice_number || bill.id}</h3>
                      <p className="text-sm text-gray-500">Generated on {formatDate(bill.invoice_date || bill.created_at)}</p>
                    </div>
                    <span className={`ml-auto px-3 py-1 rounded-full text-xs font-medium ${
                      bill.status === "Paid" ? "bg-green-100 text-green-700" :
                      bill.status === "Partial" ? "bg-orange-100 text-orange-700" :
                      "bg-red-100 text-red-700"
                    }`}>
                      {bill.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div><p className="text-gray-500">Total Amount</p><p className="font-medium text-lg">{formatCurrency(bill.total_amount)}</p></div>
                    <div><p className="text-gray-500">Paid</p><p className="font-medium text-green-600">{formatCurrency(bill.paid_amount || 0)}</p></div>
                    <div><p className="text-gray-500">Balance</p><p className="font-medium text-red-600">{formatCurrency(Number(bill.total_amount) - Number(bill.paid_amount || 0))}</p></div>
                  </div>
                </div>
                <div className="flex gap-2">
                  {bill.status !== "Paid" && (
                    <button className="px-5 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">
                      Pay Now
                    </button>
                  )}
                  <button className="px-5 py-2 border border-gray-300 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50">
                    View Details
                  </button>
                  <button className="px-5 py-2 border border-gray-300 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50">
                    Download PDF
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
          <div className="text-4xl mb-3"><CreditCardIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <h3 className="font-bold text-gray-800">No bills found</h3>
          <p className="text-sm text-gray-500 mt-1">You don&apos;t have any bills matching this filter.</p>
        </div>
      )}
    </div>
  )
}

export default PatientBills