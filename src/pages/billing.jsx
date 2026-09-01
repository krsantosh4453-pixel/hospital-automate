import { useState } from "react"

function Billing() {
  const [bills, setBills] = useState([
    {
      id: "INV001",
      patient: "Rahul Kumar",
      patientId: "P001",
      date: "01 Sep 2026",
      services: [
        { name: "Doctor Consultation", amount: 500 },
        { name: "Complete Blood Count", amount: 350 },
        { name: "Medicines", amount: 400 },
      ],
      discount: 0,
      paid: 1250,
      payment: "UPI",
      status: "Paid",
    },
    {
      id: "INV002",
      patient: "Priya Singh",
      patientId: "P002",
      date: "01 Sep 2026",
      services: [
        { name: "Doctor Consultation", amount: 500 },
        { name: "Blood Sugar Test", amount: 350 },
      ],
      discount: 0,
      paid: 500,
      payment: "Cash",
      status: "Partial",
    },
    {
      id: "INV003",
      patient: "Amit Kumar",
      patientId: "P003",
      date: "01 Sep 2026",
      services: [
        { name: "Cardiology Consultation", amount: 1500 },
      ],
      discount: 0,
      paid: 0,
      payment: "Pending",
      status: "Pending",
    },
  ])

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("All Status")

  const [showForm, setShowForm] = useState(false)
  const [showInvoice, setShowInvoice] = useState(false)

  const [selectedBill, setSelectedBill] = useState(null)

  const [formData, setFormData] = useState({
    patient: "",
    patientId: "",
    consultation: "",
    laboratory: "",
    pharmacy: "",
    other: "",
    discount: "",
    paid: "",
    payment: "Cash",
  })

  const calculateSubtotal = (bill) => {
    return bill.services.reduce(
      (total, service) => total + Number(service.amount),
      0
    )
  }

  const calculateTotal = (bill) => {
    return Math.max(
      0,
      calculateSubtotal(bill) - Number(bill.discount || 0)
    )
  }

  const totalRevenue = bills.reduce(
    (total, bill) => total + Number(bill.paid),
    0
  )

  const totalOutstanding = bills.reduce(
    (total, bill) =>
      total + calculateTotal(bill) - Number(bill.paid),
    0
  )

  const paidBills = bills.filter(
    (bill) => bill.status === "Paid"
  ).length

  const filteredBills = bills.filter((bill) => {
    const matchesSearch =
      bill.patient
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      bill.patientId
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      bill.id
        .toLowerCase()
        .includes(search.toLowerCase())

    const matchesStatus =
      statusFilter === "All Status" ||
      bill.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const handleChange = (e) => {
    const { name, value } = e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }

  const resetForm = () => {
    setFormData({
      patient: "",
      patientId: "",
      consultation: "",
      laboratory: "",
      pharmacy: "",
      other: "",
      discount: "",
      paid: "",
      payment: "Cash",
    })

    setSelectedBill(null)
    setShowForm(false)
  }

  const createServices = () => {
    const services = []

    if (Number(formData.consultation) > 0) {
      services.push({
        name: "Doctor Consultation",
        amount: Number(formData.consultation),
      })
    }

    if (Number(formData.laboratory) > 0) {
      services.push({
        name: "Laboratory Services",
        amount: Number(formData.laboratory),
      })
    }

    if (Number(formData.pharmacy) > 0) {
      services.push({
        name: "Pharmacy / Medicines",
        amount: Number(formData.pharmacy),
      })
    }

    if (Number(formData.other) > 0) {
      services.push({
        name: "Other Services",
        amount: Number(formData.other),
      })
    }

    return services
  }

  const getStatus = (total, paid) => {
    if (Number(paid) >= Number(total)) {
      return "Paid"
    }

    if (Number(paid) > 0) {
      return "Partial"
    }

    return "Pending"
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    const services = createServices()

    if (services.length === 0) {
      alert("Please enter at least one service amount.")
      return
    }

    const subtotal = services.reduce(
      (total, service) => total + service.amount,
      0
    )

    const discount = Number(formData.discount || 0)

    const total = Math.max(
      0,
      subtotal - discount
    )

    const paid = Number(formData.paid || 0)

    if (paid > total) {
      alert("Paid amount cannot be greater than total amount.")
      return
    }

    const newBill = {
      id: `INV${String(bills.length + 1).padStart(3, "0")}`,
      patient: formData.patient,
      patientId: formData.patientId,
      date: new Date().toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
      services,
      discount,
      paid,
      payment: formData.payment,
      status: getStatus(total, paid),
    }

    setBills([...bills, newBill])

    resetForm()
  }

  const handleEdit = (bill) => {
    const consultation =
      bill.services.find(
        (service) =>
          service.name === "Doctor Consultation"
      )?.amount || 0

    const laboratory =
      bill.services.find(
        (service) =>
          service.name === "Laboratory Services"
      )?.amount || 0

    const pharmacy =
      bill.services.find(
        (service) =>
          service.name === "Pharmacy / Medicines"
      )?.amount || 0

    const other =
      bill.services.find(
        (service) =>
          service.name === "Other Services"
      )?.amount || 0

    setSelectedBill(bill)

    setFormData({
      patient: bill.patient,
      patientId: bill.patientId,
      consultation: String(consultation),
      laboratory: String(laboratory),
      pharmacy: String(pharmacy),
      other: String(other),
      discount: String(bill.discount || 0),
      paid: String(bill.paid || 0),
      payment: bill.payment,
    })

    setShowForm(true)
  }

  const handleUpdate = (e) => {
    e.preventDefault()

    const services = createServices()

    const subtotal = services.reduce(
      (total, service) => total + service.amount,
      0
    )

    const discount = Number(formData.discount || 0)

    const total = Math.max(
      0,
      subtotal - discount
    )

    const paid = Number(formData.paid || 0)

    if (paid > total) {
      alert("Paid amount cannot be greater than total amount.")
      return
    }

    const updatedBills = bills.map((bill) =>
      bill.id === selectedBill.id
        ? {
          ...bill,
          patient: formData.patient,
          patientId: formData.patientId,
          services,
          discount,
          paid,
          payment: formData.payment,
          status: getStatus(total, paid),
        }
        : bill
    )

    setBills(updatedBills)

    resetForm()
  }

  const handleDelete = (id) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this bill?"
    )

    if (!confirmed) return

    setBills(
      bills.filter((bill) => bill.id !== id)
    )
  }

  const handleViewInvoice = (bill) => {
    setSelectedBill(bill)
    setShowInvoice(true)
  }

  const handlePayment = (bill) => {
    setSelectedBill(bill)

    const remaining =
      calculateTotal(bill) - Number(bill.paid)

    setFormData({
      patient: bill.patient,
      patientId: bill.patientId,
      consultation: "",
      laboratory: "",
      pharmacy: "",
      other: "",
      discount: String(bill.discount || 0),
      paid: String(
        Number(bill.paid) + remaining
      ),
      payment: "UPI",
    })

    setShowForm(true)
  }

  const printInvoice = () => {
    window.print()
  }

  const getStatusClass = (status) => {
    if (status === "Paid") {
      return "bg-green-100 text-green-700"
    }

    if (status === "Partial") {
      return "bg-blue-100 text-blue-700"
    }

    return "bg-orange-100 text-orange-700"
  }

  return (
    <div>

      {/* Normal Billing Page */}
      <div className="print:hidden">

        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">

          <div>
            <h1 className="text-3xl font-bold text-gray-800">
              Billing
            </h1>

            <p className="text-gray-500 mt-1">
              Manage invoices, payments and hospital charges
            </p>
          </div>

          <button
            onClick={() => {
              setSelectedBill(null)

              setFormData({
                patient: "",
                patientId: "",
                consultation: "",
                laboratory: "",
                pharmacy: "",
                other: "",
                discount: "",
                paid: "",
                payment: "Cash",
              })

              setShowForm(true)
            }}
            className="bg-blue-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-blue-700"
          >
            + Create Bill
          </button>

        </div>


        {/* Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

            <p className="text-sm text-gray-500">
              Total Revenue
            </p>

            <h2 className="text-3xl font-bold text-green-600 mt-3">
              ₹{totalRevenue.toLocaleString("en-IN")}
            </h2>

          </div>


          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

            <p className="text-sm text-gray-500">
              Outstanding
            </p>

            <h2 className="text-3xl font-bold text-orange-500 mt-3">
              ₹{totalOutstanding.toLocaleString("en-IN")}
            </h2>

          </div>


          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

            <p className="text-sm text-gray-500">
              Paid Invoices
            </p>

            <h2 className="text-3xl font-bold text-blue-600 mt-3">
              {paidBills}
            </h2>

          </div>

        </div>


        {/* Search */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            <input
              type="text"
              value={search}
              onChange={(e) =>
                setSearch(e.target.value)
              }
              placeholder="Search patient, patient ID or invoice..."
              className="border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
            />

            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value)
              }
              className="border border-gray-300 rounded-xl px-4 py-3"
            >

              <option>All Status</option>
              <option>Paid</option>
              <option>Partial</option>
              <option>Pending</option>

            </select>

          </div>

        </div>


        {/* Invoice Table */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

          <div className="p-6 border-b">

            <h2 className="text-xl font-bold text-gray-800">
              Invoice List
            </h2>

            <p className="text-sm text-gray-500 mt-1">
              {filteredBills.length} invoice(s) found
            </p>

          </div>


          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="bg-gray-50">

                <tr>

                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                    Invoice
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                    Patient
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                    Date
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                    Total
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                    Paid
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                    Due
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                    Status
                  </th>

                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                    Actions
                  </th>

                </tr>

              </thead>


              <tbody>

                {filteredBills.map((bill) => {

                  const total = calculateTotal(bill)

                  const due =
                    total - Number(bill.paid)

                  return (

                    <tr
                      key={bill.id}
                      className="border-t hover:bg-gray-50"
                    >

                      <td className="px-6 py-4 font-semibold text-blue-600">
                        {bill.id}
                      </td>


                      <td className="px-6 py-4">

                        <p className="font-semibold text-gray-800">
                          {bill.patient}
                        </p>

                        <p className="text-xs text-gray-500">
                          {bill.patientId}
                        </p>

                      </td>


                      <td className="px-6 py-4 text-gray-600">
                        {bill.date}
                      </td>


                      <td className="px-6 py-4 font-semibold">
                        ₹{total.toLocaleString("en-IN")}
                      </td>


                      <td className="px-6 py-4 text-green-600 font-semibold">
                        ₹{Number(bill.paid).toLocaleString("en-IN")}
                      </td>


                      <td className="px-6 py-4 text-orange-600 font-semibold">
                        ₹{due.toLocaleString("en-IN")}
                      </td>


                      <td className="px-6 py-4">

                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                            bill.status
                          )}`}
                        >
                          {bill.status}
                        </span>

                      </td>


                      <td className="px-6 py-4">

                        <div className="flex gap-2 flex-wrap">

                          <button
                            onClick={() =>
                              handleViewInvoice(bill)
                            }
                            className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg"
                          >
                            Invoice
                          </button>


                          <button
                            onClick={() =>
                              handleEdit(bill)
                            }
                            className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg"
                          >
                            Edit
                          </button>


                          {bill.status !== "Paid" && (

                            <button
                              onClick={() =>
                                handlePayment(bill)
                              }
                              className="px-3 py-2 text-sm bg-indigo-50 text-indigo-700 rounded-lg"
                            >
                              Payment
                            </button>

                          )}


                          <button
                            onClick={() =>
                              handleDelete(bill.id)
                            }
                            className="px-3 py-2 text-sm bg-red-50 text-red-700 rounded-lg"
                          >
                            Delete
                          </button>

                        </div>

                      </td>

                    </tr>

                  )
                })}

              </tbody>

            </table>

          </div>

        </div>

      </div>


      {/* Create / Edit Bill Modal */}
      {showForm && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white w-full max-w-xl rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">

            <div className="flex justify-between items-center p-6 border-b">

              <div>

                <h2 className="text-xl font-bold text-gray-800">
                  {selectedBill
                    ? "Edit Bill"
                    : "Create New Bill"}
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Add hospital services and payment details
                </p>

              </div>

              <button
                onClick={resetForm}
                className="text-2xl text-gray-500"
              >
                ×
              </button>

            </div>


            <form
              onSubmit={
                selectedBill
                  ? handleUpdate
                  : handleSubmit
              }
              className="p-6 space-y-5"
            >

              {/* Patient */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Patient Name
                  </label>

                  <input
                    type="text"
                    name="patient"
                    value={formData.patient}
                    onChange={handleChange}
                    required
                    placeholder="Rahul Kumar"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  />

                </div>


                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Patient ID
                  </label>

                  <input
                    type="text"
                    name="patientId"
                    value={formData.patientId}
                    onChange={handleChange}
                    required
                    placeholder="P001"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  />

                </div>

              </div>


              {/* Services */}
              <div>

                <h3 className="font-semibold text-gray-800 mb-3">
                  Hospital Charges
                </h3>

                <div className="space-y-3">

                  <input
                    type="number"
                    min="0"
                    name="consultation"
                    value={formData.consultation}
                    onChange={handleChange}
                    placeholder="Doctor Consultation ₹"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  />


                  <input
                    type="number"
                    min="0"
                    name="laboratory"
                    value={formData.laboratory}
                    onChange={handleChange}
                    placeholder="Laboratory Charges ₹"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  />


                  <input
                    type="number"
                    min="0"
                    name="pharmacy"
                    value={formData.pharmacy}
                    onChange={handleChange}
                    placeholder="Pharmacy / Medicines ₹"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  />


                  <input
                    type="number"
                    min="0"
                    name="other"
                    value={formData.other}
                    onChange={handleChange}
                    placeholder="Other Charges ₹"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  />

                </div>

              </div>


              {/* Discount */}
              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Discount
                </label>

                <input
                  type="number"
                  min="0"
                  name="discount"
                  value={formData.discount}
                  onChange={handleChange}
                  placeholder="₹ 0"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3"
                />

              </div>


              {/* Payment */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Amount Paid
                  </label>

                  <input
                    type="number"
                    min="0"
                    name="paid"
                    value={formData.paid}
                    onChange={handleChange}
                    placeholder="₹ 0"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  />

                </div>


                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Payment Method
                  </label>

                  <select
                    name="payment"
                    value={formData.payment}
                    onChange={handleChange}
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  >

                    <option>Cash</option>
                    <option>UPI</option>
                    <option>Card</option>
                    <option>Bank Transfer</option>

                  </select>

                </div>

              </div>


              {/* Buttons */}
              <div className="flex justify-end gap-3 pt-3">

                <button
                  type="button"
                  onClick={resetForm}
                  className="px-5 py-3 border border-gray-300 rounded-xl"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700"
                >
                  {selectedBill
                    ? "Save Changes"
                    : "Generate Bill"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}


      {/* FINAL PRINTABLE INVOICE */}
      {showInvoice && selectedBill && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 print:static print:bg-white print:p-0">

          <div
            id="print-invoice"
            className="bg-white w-full max-w-3xl rounded-2xl shadow-xl max-h-[95vh] overflow-y-auto print:max-w-none print:shadow-none print:rounded-none print:max-h-none"
          >

            {/* Invoice Header */}
            <div className="p-8 border-b-2 border-gray-800">

              <div className="flex flex-col md:flex-row md:justify-between gap-6">

                <div>

                  <h1 className="text-3xl font-bold text-gray-900">
                    HOSPITAL MANAGEMENT SYSTEM
                  </h1>

                  <p className="text-gray-600 mt-2">
                    Main Hospital Campus
                  </p>

                  <p className="text-gray-600">
                    Bihar, India
                  </p>

                  <p className="text-gray-600">
                    Phone: +91 XXXXX XXXXX
                  </p>

                </div>


                <div className="md:text-right">

                  <h2 className="text-2xl font-bold">
                    INVOICE
                  </h2>

                  <p className="mt-2">
                    Invoice No:
                    <span className="font-semibold ml-2">
                      {selectedBill.id}
                    </span>
                  </p>

                  <p>
                    Date:
                    <span className="font-semibold ml-2">
                      {selectedBill.date}
                    </span>
                  </p>

                </div>

              </div>

            </div>


            {/* Patient */}
            <div className="p-8 border-b">

              <h3 className="text-sm uppercase tracking-wide text-gray-500">
                Patient Information
              </h3>

              <div className="mt-3">

                <p className="text-lg font-bold text-gray-900">
                  {selectedBill.patient}
                </p>

                <p className="text-gray-600">
                  Patient ID: {selectedBill.patientId}
                </p>

              </div>

            </div>


            {/* Services */}
            <div className="p-8">

              <table className="w-full">

                <thead>

                  <tr className="border-b-2 border-gray-300">

                    <th className="text-left py-3">
                      Description
                    </th>

                    <th className="text-right py-3">
                      Amount
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {selectedBill.services.map(
                    (service, index) => (

                      <tr
                        key={index}
                        className="border-b"
                      >

                        <td className="py-4">
                          {service.name}
                        </td>

                        <td className="py-4 text-right">
                          ₹
                          {Number(
                            service.amount
                          ).toLocaleString("en-IN")}
                        </td>

                      </tr>

                    )
                  )}

                </tbody>

              </table>


              {/* Total Section */}
              <div className="mt-8 ml-auto max-w-sm space-y-3">

                <div className="flex justify-between">

                  <span>
                    Subtotal
                  </span>

                  <span>
                    ₹
                    {calculateSubtotal(
                      selectedBill
                    ).toLocaleString("en-IN")}
                  </span>

                </div>


                <div className="flex justify-between">

                  <span>
                    Discount
                  </span>

                  <span>
                    - ₹
                    {Number(
                      selectedBill.discount || 0
                    ).toLocaleString("en-IN")}
                  </span>

                </div>


                <div className="flex justify-between border-t-2 border-gray-800 pt-3 text-xl font-bold">

                  <span>
                    Total
                  </span>

                  <span>
                    ₹
                    {calculateTotal(
                      selectedBill
                    ).toLocaleString("en-IN")}
                  </span>

                </div>


                <div className="flex justify-between text-green-700 font-semibold">

                  <span>
                    Paid
                  </span>

                  <span>
                    ₹
                    {Number(
                      selectedBill.paid
                    ).toLocaleString("en-IN")}
                  </span>

                </div>


                <div className="flex justify-between text-orange-600 font-bold">

                  <span>
                    Balance Due
                  </span>

                  <span>
                    ₹
                    {(
                      calculateTotal(
                        selectedBill
                      ) -
                      Number(selectedBill.paid)
                    ).toLocaleString("en-IN")}
                  </span>

                </div>

              </div>


              {/* Payment Info */}
              <div className="mt-8 bg-gray-50 rounded-xl p-5">

                <div className="flex justify-between">

                  <span className="text-gray-500">
                    Payment Method
                  </span>

                  <span className="font-semibold">
                    {selectedBill.payment}
                  </span>

                </div>


                <div className="flex justify-between mt-3">

                  <span className="text-gray-500">
                    Payment Status
                  </span>

                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusClass(
                      selectedBill.status
                    )}`}
                  >
                    {selectedBill.status}
                  </span>

                </div>

              </div>


              {/* Footer */}
              <div className="mt-12 pt-6 border-t text-center">

                <p className="font-semibold">
                  Thank you for choosing our hospital.
                </p>

                <p className="text-sm text-gray-500 mt-2">
                  This is a computer-generated invoice.
                </p>

              </div>

            </div>


            {/* Invoice Buttons */}
            <div className="p-6 border-t flex justify-end gap-3 print:hidden">

              <button
                onClick={() => setShowInvoice(false)}
                className="px-5 py-3 border border-gray-300 rounded-xl"
              >
                Close
              </button>

              <button
                onClick={printInvoice}
                className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700"
              >
                🖨️ Print Bill
              </button>

            </div>

          </div>

        </div>

      )}

    </div>
  )
}

export default Billing