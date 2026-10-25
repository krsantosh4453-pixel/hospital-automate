import { useEffect, useState } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import { CreditCardIcon, HospitalIcon, MapPinIcon, PrinterIcon, TriangleAlertIcon } from "lucide-react"
import { useToast } from "../components/Toast.jsx"
import { useConfirm } from "../components/ui"

function Billing() {
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()


  const { selectedHospital } = usePatient()

  const [bills, setBills] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState("")

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


  // =========================
  // Load bills from API
  // =========================

  useEffect(() => {
    if (!selectedHospital) {
      setBills([])
      setLoadError("")
      return
    }

    let cancelled = false

    const loadBills = async () => {
      setLoading(true)
      setLoadError("")

      try {
        const data = await api.billing.invoices.list(selectedHospital.id)
        const results = Array.isArray(data) ? data : data?.results || []

        if (cancelled) return

        // Map API data to UI format
        const mappedBills = results.map((inv) => {
          const totalPaid = inv.total_paid !== undefined ? Number(inv.total_paid) : 
            (inv.payments?.reduce((sum, p) => sum + Number(p.amount), 0) || 0)
          
          const subtotal = inv.items?.reduce((sum, item) => sum + Number(item.subtotal), 0) || 0
          
          return {
            id: inv.invoice_number,
            apiId: inv.id,
            patient: inv.patient_name || inv.patient?.name || "Unknown",
            patientId: inv.patient ? `P${String(inv.patient).padStart(3, "0")}` : "",
            hospitalId: inv.hospital,
            date: inv.created_at ? new Date(inv.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "",
            services: inv.items?.map((item) => ({
              name: item.description,
              amount: Number(item.subtotal),
            })) || [],
            discount: Number(inv.discount || 0),
            paid: totalPaid,
            payment: inv.payments?.[0]?.payment_method || "Cash",
            status: inv.status,
            // Keep API fields for update/delete
            apiInvoice: inv,
          }
        })

        setBills(mappedBills)
      } catch (error) {
        if (cancelled) return
        setLoadError(error.message || "Failed to load billing data")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadBills()

    return () => {
      cancelled = true
    }
  }, [selectedHospital])


  // =========================
  // Hospital Bills
  // =========================

  const hospitalBills = selectedHospital
    ? bills.filter(
      (bill) =>
        bill.hospitalId === selectedHospital.id
    )
    : []


  // =========================
  // Calculate Subtotal
  // =========================

  const calculateSubtotal = (bill) => {

    return bill.services.reduce(
      (total, service) =>
        total + Number(service.amount),
      0
    )
  }


  // =========================
  // Calculate Total
  // =========================

  const calculateTotal = (bill) => {

    return Math.max(
      0,
      calculateSubtotal(bill) -
      Number(bill.discount || 0)
    )
  }


  // =========================
  // Statistics
  // =========================

  const totalRevenue =
    hospitalBills.reduce(
      (total, bill) =>
        total + Number(bill.paid),
      0
    )


  const totalOutstanding =
    hospitalBills.reduce(
      (total, bill) =>
        total +
        calculateTotal(bill) -
        Number(bill.paid),
      0
    )


  const paidBills =
    hospitalBills.filter(
      (bill) =>
        bill.status === "Paid"
    ).length


  // =========================
  // Filter Bills
  // =========================

  const filteredBills =
    hospitalBills.filter((bill) => {

      const matchesSearch =
        bill.patient
          .toLowerCase()
          .includes(
            search.toLowerCase()
          ) ||

        bill.patientId
          .toLowerCase()
          .includes(
            search.toLowerCase()
          ) ||

        bill.id
          .toLowerCase()
          .includes(
            search.toLowerCase()
          )


      const matchesStatus =
        statusFilter ===
        "All Status" ||
        bill.status ===
        statusFilter


      return (
        matchesSearch &&
        matchesStatus
      )
    })


  // =========================
  // Form Change
  // =========================

  const handleChange = (e) => {

    const {
      name,
      value,
    } = e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }


  // =========================
  // Reset Form
  // =========================

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


  // =========================
  // Create Services
  // =========================

  const createServices = () => {

    const services = []


    if (
      Number(formData.consultation) > 0
    ) {

      services.push({
        name:
          "Doctor Consultation",

        amount:
          Number(
            formData.consultation
          ),
      })
    }


    if (
      Number(formData.laboratory) > 0
    ) {

      services.push({
        name:
          "Laboratory Services",

        amount:
          Number(
            formData.laboratory
          ),
      })
    }


    if (
      Number(formData.pharmacy) > 0
    ) {

      services.push({
        name:
          "Pharmacy / Medicines",

        amount:
          Number(
            formData.pharmacy
          ),
      })
    }


    if (
      Number(formData.other) > 0
    ) {

      services.push({
        name:
          "Other Services",

        amount:
          Number(
            formData.other
          ),
      })
    }


    return services
  }


  // =========================
  // Get Status
  // =========================

  const getStatus = (
    total,
    paid
  ) => {

    if (
      Number(paid) >=
      Number(total)
    ) {

      return "Paid"
    }


    if (
      Number(paid) > 0
    ) {

      return "Partial"
    }


    return "Pending"
  }


  // =========================
  // Submit New Bill
  // =========================

  const handleSubmit = async (e) => {

    e.preventDefault()


    if (!selectedHospital) {

      toast.warning(
        "Please select a hospital first."
      )

      return
    }


    const services =
      createServices()


    if (
      services.length === 0
    ) {

      toast.warning(
        "Please enter at least one service amount."
      )

      return
    }


    const subtotal =
      services.reduce(
        (total, service) =>
          total +
          service.amount,
        0
      )


    const discount =
      Number(
        formData.discount || 0
      )


    const total =
      Math.max(
        0,
        subtotal - discount
      )


    const paid =
      Number(
        formData.paid || 0
      )


    if (paid > total) {

      toast.error(
        "Paid amount cannot be greater than total amount."
      )

      return
    }


    // Get patient from the system
    const patientsRes = await api.patients.list(selectedHospital.id)
    const patients = Array.isArray(patientsRes) ? patientsRes : patientsRes?.results || []
    const patient = patients.find(p => 
      p.name?.toLowerCase() === formData.patient?.toLowerCase() ||
      `P${String(p.id).padStart(3, "0")}` === formData.patientId
    )

    if (!patient) {
      toast.error("Patient not found in this hospital. Please check the name/ID.")
      return
    }

    // Totals, tax and status are calculated by the server from these lines.
    const payload = {
      hospital: selectedHospital.id,
      patient: patient.id,
      discount: discount,
      items_data: services.map((s) => ({
        description: s.name,
        quantity: 1,
        unit_price: s.amount,
      })),
    }

    try {
      const created = await api.billing.invoices.create(payload)

      // Also create payment record if paid > 0
      if (paid > 0) {
        await api.billing.payments.create({
          invoice: created.id,
          amount: Number(paid).toFixed(2),
          payment_method: formData.payment,
          idempotency_key: `${created.id}-initial`,
        })
      }

      // Reload bills
      const data = await api.billing.invoices.list(selectedHospital.id)
      const results = Array.isArray(data) ? data : data?.results || []
      const mappedBills = results.map((inv) => {
        const totalPaid = inv.total_paid !== undefined ? Number(inv.total_paid) : 
          (inv.payments?.reduce((sum, p) => sum + Number(p.amount), 0) || 0)
        
        return {
          id: inv.invoice_number,
          apiId: inv.id,
          patient: inv.patient_name || inv.patient?.name || "Unknown",
          patientId: inv.patient ? `P${String(inv.patient).padStart(3, "0")}` : "",
          hospitalId: inv.hospital,
          date: inv.created_at ? new Date(inv.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "",
          services: inv.items?.map((item) => ({
            name: item.description,
            amount: Number(item.subtotal),
          })) || [],
          discount: Number(inv.discount || 0),
          paid: totalPaid,
          payment: inv.payments?.[0]?.payment_method || "Cash",
          status: inv.status,
        }
      })
      setBills(mappedBills)

      resetForm()
      toast.success("Invoice created successfully!")
    } catch (error) {
      toast.error(error.message || "Failed to create invoice")
    }
  }


  // =========================
  // Edit Bill
  // =========================

  const handleEdit = (
    bill
  ) => {

    const consultation =
      bill.services.find(
        (service) =>
          service.name ===
          "Doctor Consultation"
      )?.amount || 0


    const laboratory =
      bill.services.find(
        (service) =>
          service.name ===
          "Laboratory Services"
      )?.amount || 0


    const pharmacy =
      bill.services.find(
        (service) =>
          service.name ===
          "Pharmacy / Medicines"
      )?.amount || 0


    const other =
      bill.services.find(
        (service) =>
          service.name ===
          "Other Services"
      )?.amount || 0


    setSelectedBill(
      bill
    )


    setFormData({

      patient:
        bill.patient,

      patientId:
        bill.patientId,

      consultation:
        String(
          consultation
        ),

      laboratory:
        String(
          laboratory
        ),

      pharmacy:
        String(
          pharmacy
        ),

      other:
        String(
          other
        ),

      discount:
        String(
          bill.discount || 0
        ),

      paid:
        String(
          bill.paid || 0
        ),

      payment:
        bill.payment,
    })


    setShowForm(true)
  }


  // =========================
  // Update Bill
  // =========================

  const handleUpdate = async (e) => {

    e.preventDefault()


    const services =
      createServices()


    if (
      services.length === 0
    ) {

      toast.warning(
        "Please enter at least one service amount."
      )

      return
    }


    const subtotal =
      services.reduce(
        (total, service) =>
          total +
          service.amount,
        0
      )


    const discount =
      Number(
        formData.discount || 0
      )


    const total =
      Math.max(
        0,
        subtotal - discount
      )


    const paid =
      Number(
        formData.paid || 0
      )


    if (paid > total) {

      toast.error(
        "Paid amount cannot be greater than total amount."
      )

      return
    }


    if (!selectedBill?.apiInvoice?.id) {
      toast.error("Cannot update: missing server record ID")
      return
    }

    // Payments are permanent records: an edit can only add money received.
    // Lowering the paid amount needs a refund; line items are fixed once paid.
    const alreadyPaid = Number(selectedBill.apiInvoice.total_paid || 0)
    const additional = Math.round((Number(paid) - alreadyPaid) * 100) / 100
    if (additional < 0) {
      toast.info(`₹${alreadyPaid} has already been received. To return money, record a refund instead of lowering the paid amount.`)
      return
    }
    const hasPayments = alreadyPaid > 0 || (selectedBill.apiInvoice.payments || []).length > 0

    try {
      const payload = { discount: discount }
      if (!hasPayments) {
        payload.items_data = services.map((s) => ({
          description: s.name,
          quantity: 1,
          unit_price: s.amount,
        }))
      }

      await api.billing.invoices.update(selectedBill.apiInvoice.id, payload)

      if (additional > 0) {
        await api.billing.payments.create({
          invoice: selectedBill.apiInvoice.id,
          amount: additional.toFixed(2),
          payment_method: formData.payment,
          idempotency_key: `${selectedBill.apiInvoice.id}-${Date.now()}`,
        })
      }

      // Reload bills
      const data = await api.billing.invoices.list(selectedHospital.id)
      const results = Array.isArray(data) ? data : data?.results || []
      const mappedBills = results.map((inv) => {
        const totalPaid = inv.total_paid !== undefined ? Number(inv.total_paid) : 
          (inv.payments?.reduce((sum, p) => sum + Number(p.amount), 0) || 0)
        
        return {
          id: inv.invoice_number,
          apiId: inv.id,
          patient: inv.patient_name || inv.patient?.name || "Unknown",
          patientId: inv.patient ? `P${String(inv.patient).padStart(3, "0")}` : "",
          hospitalId: inv.hospital,
          date: inv.created_at ? new Date(inv.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "",
          services: inv.items?.map((item) => ({
            name: item.description,
            amount: Number(item.subtotal),
          })) || [],
          discount: Number(inv.discount || 0),
          paid: totalPaid,
          payment: inv.payments?.[0]?.payment_method || "Cash",
          status: inv.status,
        }
      })
      setBills(mappedBills)

      resetForm()
      toast.success("Invoice updated successfully!")
    } catch (error) {
      toast.error(error.message || "Failed to update invoice")
    }
  }


  // =========================
  // Delete
  // =========================

  const handleDelete = async (
    id
  ) => {

    const confirmed =
      (await confirm(
        "Are you sure you want to delete this bill?"
      ))


    if (!confirmed) {
      return
    }

    const bill = bills.find(b => b.id === id)
    if (!bill?.apiInvoice?.id) {
      toast.error("Cannot delete: missing server record ID")
      return
    }

    try {
      await api.billing.invoices.delete(bill.apiInvoice.id)
      
      // Reload bills
      const data = await api.billing.invoices.list(selectedHospital.id)
      const results = Array.isArray(data) ? data : data?.results || []
      const mappedBills = results.map((inv) => {
        const totalPaid = inv.total_paid !== undefined ? Number(inv.total_paid) : 
          (inv.payments?.reduce((sum, p) => sum + Number(p.amount), 0) || 0)
        
        return {
          id: inv.invoice_number,
          apiId: inv.id,
          patient: inv.patient_name || inv.patient?.name || "Unknown",
          patientId: inv.patient ? `P${String(inv.patient).padStart(3, "0")}` : "",
          hospitalId: inv.hospital,
          date: inv.created_at ? new Date(inv.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "",
          services: inv.items?.map((item) => ({
            name: item.description,
            amount: Number(item.subtotal),
          })) || [],
          discount: Number(inv.discount || 0),
          paid: totalPaid,
          payment: inv.payments?.[0]?.payment_method || "Cash",
          status: inv.status,
        }
      })
      setBills(mappedBills)

      toast.success("Invoice deleted successfully!")
    } catch (error) {
      toast.error(error.message || "Failed to delete invoice")
    }
  }


  // =========================
  // View Invoice
  // =========================

  const handleViewInvoice = (
    bill
  ) => {

    setSelectedBill(
      bill
    )

    setShowInvoice(true)
  }


  // =========================
  // Payment
  // =========================

  const handlePayment = (
    bill
  ) => {

    setSelectedBill(
      bill
    )


    const remaining =
      calculateTotal(
        bill
      ) -
      Number(
        bill.paid
      )


    setFormData({

      patient:
        bill.patient,

      patientId:
        bill.patientId,

      consultation: "",

      laboratory: "",

      pharmacy: "",

      other: "",

      discount:
        String(
          bill.discount || 0
        ),

      paid:
        String(
          Number(
            bill.paid
          ) +
          remaining
        ),

      payment:
        "UPI",
    })


    setShowForm(true)
  }


  // =========================
  // Print
  // =========================

  const printInvoice = () => {

    window.print()
  }


  // =========================
  // Status Class
  // =========================

  const getStatusClass = (
    status
  ) => {

    if (
      status ===
      "Paid"
    ) {

      return "bg-green-100 text-green-700"
    }


    if (
      status ===
      "Partial"
    ) {

      return "bg-blue-100 text-blue-700"
    }


    return "bg-orange-100 text-orange-700"
  }


  return (

    <>{confirmDialog}<div>


      {/* =========================
          Normal Billing Page
      ========================= */}

      <div className="print:hidden">


        {/* Header */}

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">

          <div>

            <p className="text-blue-600 font-semibold text-sm">
              FINANCE & BILLING
            </p>

            <h1 className="text-3xl font-bold text-gray-800 mt-1">
              Billing
            </h1>

            <p className="text-gray-500 mt-1">
              Manage invoices, payments and hospital charges
            </p>

          </div>


          <button

            onClick={() => {

              if (
                !selectedHospital
              ) {

                toast.warning(
                  "Please select a hospital first."
                )

                return
              }


              setSelectedBill(
                null
              )


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


              setShowForm(
                true
              )
            }}

            className="bg-blue-600 text-white px-5 py-3 rounded-xl font-medium hover:bg-blue-700"
          >

            + Create Bill

          </button>

        </div>


        {/* =========================
            Current Hospital
        ========================= */}

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

          {selectedHospital ? (

            <div className="flex items-center gap-4">

              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">
                <HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />
              </div>


              <div>

                <p className="text-xs text-gray-500">
                  Current Hospital
                </p>

                <h2 className="font-bold text-gray-800">
                  {selectedHospital.name}
                </h2>

                <p className="text-sm text-gray-500">
                  <MapPinIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> {selectedHospital.address}
                </p>

              </div>

            </div>

          ) : (

            <div>

              <p className="font-semibold text-orange-600">
                <TriangleAlertIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> No hospital selected
              </p>

              <p className="text-sm text-gray-500 mt-1">
                Select a hospital from the header first.
              </p>

            </div>

          )}

        </div>


        {/* =========================
            No Hospital Selected
        ========================= */}

        {!selectedHospital ? (

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">

            <div className="text-5xl mb-4">
              <CreditCardIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />
            </div>

            <h2 className="text-xl font-bold text-gray-800">
              Select a Hospital
            </h2>

            <p className="text-gray-500 mt-2">
              Select a hospital from the header to view billing data.
            </p>

          </div>

        ) : (

          <>


            {/* =========================
                Statistics
            ========================= */}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">


              {/* Revenue */}

              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

                <p className="text-sm text-gray-500">
                  Total Revenue
                </p>

                <h2 className="text-3xl font-bold text-green-600 mt-3">
                  ₹
                  {totalRevenue.toLocaleString(
                    "en-IN"
                  )}
                </h2>

              </div>


              {/* Outstanding */}

              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

                <p className="text-sm text-gray-500">
                  Outstanding
                </p>

                <h2 className="text-3xl font-bold text-orange-500 mt-3">
                  ₹
                  {totalOutstanding.toLocaleString(
                    "en-IN"
                  )}
                </h2>

              </div>


              {/* Paid */}

              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

                <p className="text-sm text-gray-500">
                  Paid Invoices
                </p>

                <h2 className="text-3xl font-bold text-blue-600 mt-3">
                  {paidBills}
                </h2>

              </div>

            </div>


            {/* =========================
                Search & Filter
            ========================= */}

            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">


                <input

                  type="text"

                  value={search}

                  onChange={(e) =>
                    setSearch(
                      e.target.value
                    )
                  }

                  placeholder="Search patient, patient ID or invoice..."

                  className="hms-input"

                />


                <select

                  value={
                    statusFilter
                  }

                  onChange={(e) =>
                    setStatusFilter(
                      e.target.value
                    )
                  }

                  className="hms-input"

                >

                  <option>
                    All Status
                  </option>

                  <option>
                    Paid
                  </option>

                  <option>
                    Partial
                  </option>

                  <option>
                    Pending
                  </option>

                </select>

              </div>

            </div>


            {/* =========================
                Invoice List
            ========================= */}

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


                    {filteredBills.length === 0 ? (

                      <tr>

                        <td
                          colSpan="8"
                          className="text-center py-12 text-gray-500"
                        >

                          <div className="text-4xl mb-3">
                            <CreditCardIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />
                          </div>

                          No bills found for this hospital.

                        </td>

                      </tr>

                    ) : (

                      filteredBills.map(
                        (bill) => {

                          const total =
                            calculateTotal(
                              bill
                            )

                          const due =
                            total -
                            Number(
                              bill.paid
                            )


                          return (

                            <tr

                              key={
                                bill.id
                              }

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

                                ₹
                                {total.toLocaleString(
                                  "en-IN"
                                )}

                              </td>


                              <td className="px-6 py-4 text-green-600 font-semibold">

                                ₹
                                {Number(
                                  bill.paid
                                ).toLocaleString(
                                  "en-IN"
                                )}

                              </td>


                              <td className="px-6 py-4 text-orange-600 font-semibold">

                                ₹
                                {due.toLocaleString(
                                  "en-IN"
                                )}

                              </td>


                              <td className="px-6 py-4">

                                <span

                                  className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                                    bill.status
                                  )}`}

                                >

                                  {
                                    bill.status
                                  }

                                </span>

                              </td>


                              <td className="px-6 py-4">

                                <div className="flex gap-2 flex-wrap">


                                  <button

                                    onClick={() =>
                                      handleViewInvoice(
                                        bill
                                      )
                                    }

                                    className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg"

                                  >
                                    Invoice
                                  </button>


                                  <button

                                    onClick={() =>
                                      handleEdit(
                                        bill
                                      )
                                    }

                                    className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg"

                                  >
                                    Edit
                                  </button>


                                  {bill.status !==
                                    "Paid" && (

                                      <button

                                        onClick={() =>
                                          handlePayment(
                                            bill
                                          )
                                        }

                                        className="px-3 py-2 text-sm bg-indigo-50 text-indigo-700 rounded-lg"

                                      >
                                        Payment
                                      </button>

                                    )}


                                  <button

                                    onClick={() =>
                                      handleDelete(
                                        bill.id
                                      )
                                    }

                                    className="px-3 py-2 text-sm bg-red-50 text-red-700 rounded-lg"

                                  >
                                    Delete
                                  </button>


                                </div>

                              </td>

                            </tr>

                          )

                        }
                      )

                    )}

                  </tbody>

                </table>

              </div>

            </div>

          </>

        )}

      </div>


      {/* =========================
          CREATE / EDIT MODAL
      ========================= */}

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

                <p className="text-sm text-blue-600 mt-1">
                  {selectedHospital?.name}
                </p>

              </div>


              <button
                onClick={
                  resetForm
                }
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

                    value={
                      formData.patient
                    }

                    onChange={
                      handleChange
                    }

                    required

                    placeholder="Rahul Kumar"

                    className="hms-input w-full"

                  />

                </div>


                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Patient ID
                  </label>

                  <input

                    type="text"

                    name="patientId"

                    value={
                      formData.patientId
                    }

                    onChange={
                      handleChange
                    }

                    required

                    placeholder="P001"

                    className="hms-input w-full"

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

                    value={
                      formData.consultation
                    }

                    onChange={
                      handleChange
                    }

                    placeholder="Doctor Consultation ₹"

                    className="hms-input w-full"

                  />


                  <input

                    type="number"

                    min="0"

                    name="laboratory"

                    value={
                      formData.laboratory
                    }

                    onChange={
                      handleChange
                    }

                    placeholder="Laboratory Charges ₹"

                    className="hms-input w-full"

                  />


                  <input

                    type="number"

                    min="0"

                    name="pharmacy"

                    value={
                      formData.pharmacy
                    }

                    onChange={
                      handleChange
                    }

                    placeholder="Pharmacy / Medicines ₹"

                    className="hms-input w-full"

                  />


                  <input

                    type="number"

                    min="0"

                    name="other"

                    value={
                      formData.other
                    }

                    onChange={
                      handleChange
                    }

                    placeholder="Other Charges ₹"

                    className="hms-input w-full"

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

                  value={
                    formData.discount
                  }

                  onChange={
                    handleChange
                  }

                  placeholder="₹ 0"

                  className="hms-input w-full"

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

                    value={
                      formData.paid
                    }

                    onChange={
                      handleChange
                    }

                    placeholder="₹ 0"

                    className="hms-input w-full"

                  />

                </div>


                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Payment Method
                  </label>

                  <select

                    name="payment"

                    value={
                      formData.payment
                    }

                    onChange={
                      handleChange
                    }

                    className="hms-input w-full"

                  >

                    <option>
                      Cash
                    </option>

                    <option>
                      UPI
                    </option>

                    <option>
                      Card
                    </option>

                    <option>
                      Bank Transfer
                    </option>

                  </select>

                </div>

              </div>


              {/* Buttons */}

              <div className="flex justify-end gap-3 pt-3">

                <button

                  type="button"

                  onClick={
                    resetForm
                  }

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


      {/* =========================
          INVOICE MODAL
      ========================= */}

      {showInvoice &&
        selectedBill && (

          <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 print:static print:bg-white print:p-0">

            <div

              id="print-invoice"

              className="bg-white w-full max-w-3xl rounded-2xl shadow-xl max-h-[95vh] overflow-y-auto print:max-w-none print:shadow-none print:rounded-none print:max-h-none"

            >


              {/* Invoice Header */}

              <div className="p-8 border-b-2 border-gray-800">

                <div className="flex flex-col md:flex-row md:justify-between gap-6">


                  <div>

                    <div className="flex items-center gap-3">

                      <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">
                        <HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />
                      </div>

                      <div>

                        <h1 className="text-2xl font-bold text-gray-900">
                          {selectedHospital?.name}
                        </h1>

                        <p className="text-gray-600">
                          Hospital Management System
                        </p>

                      </div>

                    </div>


                    <p className="text-gray-600 mt-3">
                      {selectedHospital?.address}
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


              {/* Patient Information */}

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
                      (
                        service,
                        index
                      ) => (

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
                            ).toLocaleString(
                              "en-IN"
                            )}

                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>


                {/* Totals */}

                <div className="mt-8 ml-auto max-w-sm space-y-3">


                  <div className="flex justify-between">

                    <span>
                      Subtotal
                    </span>

                    <span>

                      ₹
                      {calculateSubtotal(
                        selectedBill
                      ).toLocaleString(
                        "en-IN"
                      )}

                    </span>

                  </div>


                  <div className="flex justify-between">

                    <span>
                      Discount
                    </span>

                    <span>

                      - ₹
                      {Number(
                        selectedBill.discount ||
                        0
                      ).toLocaleString(
                        "en-IN"
                      )}

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
                      ).toLocaleString(
                        "en-IN"
                      )}

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
                      ).toLocaleString(
                        "en-IN"
                      )}

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
                        Number(
                          selectedBill.paid
                        )
                      ).toLocaleString(
                        "en-IN"
                      )}

                    </span>

                  </div>

                </div>


                {/* Payment Information */}

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

                      {
                        selectedBill.status
                      }

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


              {/* Buttons */}

              <div className="p-6 border-t flex justify-end gap-3 print:hidden">

                <button

                  onClick={() =>
                    setShowInvoice(
                      false
                    )
                  }

                  className="px-5 py-3 border border-gray-300 rounded-xl"

                >
                  Close
                </button>


                <button

                  onClick={
                    printInvoice
                  }

                  className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700"

                >
                  <PrinterIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> Print Bill
                </button>

              </div>


            </div>

          </div>

        )}

    </div></>
  )
}

export default Billing