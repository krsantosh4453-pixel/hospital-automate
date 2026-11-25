import { useEffect, useRef, useState } from "react"
import { useSubmitGuard } from "../utils/submitGuard.js"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import { useLinkedPatient } from "../utils/linkedPatient.js"
import { CreditCardIcon, HospitalIcon, PrinterIcon } from "lucide-react"
import { useToast } from "../components/Toast.jsx"
import { Alert, Button, Card, EmptyState, Field, PageHeader, useConfirm } from "../components/ui"
import PatientPicker from "../components/patients/PatientPicker.jsx"
import { displayPatientId } from "../utils/patientIdentity.js"
import AdvancePayments from "../components/billing/AdvancePayments.jsx"
import DischargeBills from "../components/billing/DischargeBills.jsx"
import PriceList from "../components/billing/PriceList.jsx"
import RefundDialog from "../components/billing/RefundDialog.jsx"
import PricedServicePicker from "../components/billing/PricedServicePicker.jsx"
import UnbilledWork from "../components/billing/UnbilledWork.jsx"
import { itemsData, otherLinesOf, pricedAmount } from "../utils/billingLines.js"
import { AMOUNT_FORMAT_ERROR, formatRupees, fromPaise, paymentToRecord, toPaise } from "../utils/money.js"
import { Plus as PlusIcon } from "lucide-react"
import { useLanguage } from "../assets/context/LanguageContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"

// Refunds of advance money are for billing staff and above (the server enforces this).
const REFUND_ROLES = ["Admin", "Hospital Manager", "Billing Staff"]
// Prices are added and retired, and unbilled work charged, by these (server-enforced).
const PRICING_ROLES = ["Admin", "Hospital Manager"]

function Billing() {
  const { t } = useLanguage()
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()


  const { selectedHospital } = usePatient()
  const { activeRoleName } = useRole()
  // Bumped when a discharge final bill is created, to reload the invoices.
  const [billsReloadToken, setBillsReloadToken] = useState(0)

  const [bills, setBills] = useState([])
  const [, setLoading] = useState(false)
  const [loadError, setLoadError] = useState("")

  // Opened from another module (e.g. the ER) with ?q=<patient name>.
  const linked = useLinkedPatient()
  const [search, setSearch] = useState(linked.query)
  const [statusFilter, setStatusFilter] = useState("All Status")

  const [showForm, setShowForm] = useState(false)
  // Bill being refunded (its server record), or null.
  const [refunding, setRefunding] = useState(null)
  const [showInvoice, setShowInvoice] = useState(false)

  const [selectedBill, setSelectedBill] = useState(null)

  // B-4: lines chosen from the price list, and other lines of an edited bill
  // that the four typed amounts do not cover (kept, never dropped on save).
  const [pricedLines, setPricedLines] = useState([])
  const [keptLines, setKeptLines] = useState([])
  // The Payment button opens the form to take money only: no bill lines are
  // sent, so another bill's lines can never be written onto this one.
  const [paymentOnly, setPaymentOnly] = useState(false)
  const otherTotal = () =>
    pricedLines.reduce((sum, line) => sum + pricedAmount(line), 0) +
    keptLines.reduce((sum, line) => sum + pricedAmount(line), 0)

  // One idempotency key per opened form (RL-04): a retry after a lost
  // response re-sends the same key, so the server records the payment once.
  const paymentKey = useRef("")
  const paymentKeyFor = (invoiceId) => {
    if (!paymentKey.current) paymentKey.current = `${invoiceId}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
    return paymentKey.current
  }


  const [formData, setFormData] = useState({
    patient: "",
    patientId: "",
    patientRecord: "",
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
          
          return {
            id: inv.invoice_number,
            apiId: inv.id,
            patient: inv.patient_name || inv.patient?.name || "Unknown",
            patientId: inv.patient ? displayPatientId({ id: inv.patient, uhid: inv.patient_uhid }) : "",
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
  }, [selectedHospital, billsReloadToken])


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

    // The server's total includes GST on priced lines; the line sum does not.
    const serverTotal = bill.apiInvoice?.total_amount ?? bill.apiInvoice?.total
    if (serverTotal !== undefined && serverTotal !== null) return Number(serverTotal)

    return Math.max(
      0,
      calculateSubtotal(bill) -
      Number(bill.discount || 0)
    )
  }


  // A bill's money in whole paise, from the server's own figures when it sent
  // them (BUG-002: no floating-point rupees in totals, balances or sums).
  const billPaise = (bill) => {
    const inv = bill.apiInvoice || {}
    const total = toPaise(inv.total_amount ?? inv.total ?? calculateTotal(bill))
    const paid = toPaise(inv.total_paid ?? bill.paid ?? 0)
    const due = inv.balance_due !== undefined && inv.balance_due !== null ? toPaise(inv.balance_due) : total - paid
    return { total, paid, due }
  }

  // =========================
  // Statistics
  // =========================

  const totalRevenue =
    hospitalBills.reduce(
      (total, bill) =>
        total + billPaise(bill).paid,
      0
    )


  const totalOutstanding =
    hospitalBills.reduce(
      (total, bill) =>
        total + billPaise(bill).due,
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
      patientRecord: "",
      consultation: "",
      laboratory: "",
      pharmacy: "",
      other: "",
      discount: "",
      paid: "",
      payment: "Cash",
    })

    setSelectedBill(null)
    setPricedLines([])
    setKeptLines([])
    setPaymentOnly(false)
    setShowForm(false)
    paymentKey.current = ""
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
      services.length === 0 && pricedLines.length === 0 && keptLines.length === 0
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
      ) + otherTotal()


    const discount =
      Number(
        formData.discount || 0
      )


    const total =
      Math.max(
        0,
        subtotal - discount
      )


    // BUG-002: amounts are compared in whole paise; more than 2 decimals is refused.
    const paidPaise = toPaise(String(formData.paid || "0"))
    const discountPaise = toPaise(String(formData.discount || "0"))
    if (Number.isNaN(paidPaise) || paidPaise < 0 || Number.isNaN(discountPaise) || discountPaise < 0) {
      toast.error(AMOUNT_FORMAT_ERROR)
      return
    }

    // A new bill's GST is added by the server, so this is the pre-tax limit.
    if (paidPaise > toPaise(total)) {

      toast.error(
        "Paid amount cannot be greater than total amount."
      )

      return
    }


    // The patient chosen in the picker, by id: never matched by name (RL-03).
    if (!formData.patientRecord) {
      toast.error("Choose the patient by searching their name, phone or UHID.")
      return
    }

    // Totals, tax and status are calculated by the server from these lines.
    const payload = {
      hospital: selectedHospital.id,
      patient: Number(formData.patientRecord),
      discount: discount,
      items_data: itemsData(services, pricedLines, keptLines),
    }

    try {
      const created = await api.billing.invoices.create(payload)

      // Also create payment record if paid > 0
      if (paidPaise > 0) {
        await api.billing.payments.create({
          invoice: created.id,
          amount: fromPaise(paidPaise),
          payment_method: formData.payment,
          idempotency_key: `${created.id}-initial`,
        })
      }

      // Reload bills through the page loader, which keeps each bill's server record.
      setBillsReloadToken((n) => n + 1)

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

    // B-4: priced and other lines of this bill are kept on save.
    const others = otherLinesOf(bill.apiInvoice?.items)
    setPricedLines(others.priced)
    setKeptLines(others.kept)
    setPaymentOnly(false)


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

  // Payment button: record money received against the server's total only.
  const recordPaymentOnly = async () => {
    if (!selectedBill?.apiInvoice?.id) {
      toast.error("Cannot update: missing server record ID")
      return
    }
    // BUG-002: exact paise against the server's total (with GST), never floats.
    const payment = paymentToRecord({
      total: selectedBill.apiInvoice.total_amount ?? selectedBill.apiInvoice.total ?? calculateTotal(selectedBill),
      alreadyPaid: selectedBill.apiInvoice.total_paid ?? "0",
      enteredPaid: String(formData.paid ?? ""),
    })
    if (payment.error) {
      toast.error(payment.error)
      return
    }
    if (payment.info) {
      toast.info(t(payment.info, { alreadyPaid: payment.alreadyPaid }))
      return
    }
    await api.billing.payments.create({
      invoice: selectedBill.apiInvoice.id,
      amount: payment.amount,
      payment_method: formData.payment,
      idempotency_key: paymentKeyFor(selectedBill.apiInvoice.id),
    })
    setBillsReloadToken((n) => n + 1)
    resetForm()
    toast.success("Payment recorded.")
  }

  const handleUpdate = async (e) => {

    e.preventDefault()

    if (paymentOnly) {
      try {
        await recordPaymentOnly()
      } catch (error) {
        toast.error(error.message || "Failed to record the payment")
      }
      return
    }


    const services =
      createServices()


    if (
      services.length === 0 && pricedLines.length === 0 && keptLines.length === 0
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
      ) + otherTotal()


    const discount =
      Number(
        formData.discount || 0
      )


    const total =
      Math.max(
        0,
        subtotal - discount
      )


    // BUG-002: amounts are compared in whole paise; more than 2 decimals is refused.
    const paidPaise = toPaise(String(formData.paid || "0"))
    const discountPaise = toPaise(String(formData.discount || "0"))
    if (Number.isNaN(paidPaise) || paidPaise < 0 || Number.isNaN(discountPaise) || discountPaise < 0) {
      toast.error(AMOUNT_FORMAT_ERROR)
      return
    }

    // An existing bill's limit is the server's total, which includes GST
    // (the line sum here does not, and refused paying a GST bill in full).
    if (paidPaise > (selectedBill ? toPaise(calculateTotal(selectedBill)) : toPaise(total))) {

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
    const alreadyPaid = fromPaise(toPaise(selectedBill.apiInvoice.total_paid ?? "0"))
    const additionalPaise = paidPaise - toPaise(alreadyPaid)
    if (additionalPaise < 0) {
      toast.info(t("₹{alreadyPaid} has already been received. To return money, record a refund instead of lowering the paid amount.", { alreadyPaid }))
      return
    }
    const hasPayments = toPaise(alreadyPaid) > 0 || (selectedBill.apiInvoice.payments || []).length > 0
    // Lines charged automatically (consultation, lab, bed) are fixed; the
    // server refuses to replace them, so only the discount is sent.
    const hasCapturedCharges = (selectedBill.apiInvoice.items || []).some((item) => item.charge_key)

    try {
      const payload = { discount: discount }
      if (!hasPayments && !hasCapturedCharges) {
        payload.items_data = itemsData(services, pricedLines, keptLines)
      }

      await api.billing.invoices.update(selectedBill.apiInvoice.id, payload)

      if (additionalPaise > 0) {
        await api.billing.payments.create({
          invoice: selectedBill.apiInvoice.id,
          amount: fromPaise(additionalPaise),
          payment_method: formData.payment,
          idempotency_key: paymentKeyFor(selectedBill.apiInvoice.id),
        })
      }

      // Reload bills through the page loader, which keeps each bill's server record.
      setBillsReloadToken((n) => n + 1)

      resetForm()
      toast.success("Invoice updated successfully!")
    } catch (error) {
      toast.error(error.message || "Failed to update invoice")
    }
  }


  // A second click while the bill is saving does nothing (RL-04).
  const [submitBill, savingBill] = useSubmitGuard(selectedBill ? handleUpdate : handleSubmit, {
    onError: (error) => toast.error(error.message || "Could not save the bill."),
  })


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
      
      // Reload bills through the page loader, which keeps each bill's server record.
      setBillsReloadToken((n) => n + 1)

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
    setPricedLines([])
    setKeptLines([])
    setPaymentOnly(true)


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
      "Partially Paid"
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

      <div className="space-y-6 print:hidden">


        <PageHeader
          title={t("Billing")}
          description={selectedHospital ? t("Invoices, payments and refunds at {hospital}.", { hospital: selectedHospital.name }) : t("Select a hospital from the header to view billing.")}
          breadcrumbs={[{ label: "Home", to: "/" }, { label: "Billing" }]}
          actions={
            selectedHospital && (
              <Button
                icon={PlusIcon}
                onClick={() => {
                  setSelectedBill(null)
                  setPricedLines([])
                  setKeptLines([])
                  setPaymentOnly(false)
                  setFormData({ patient: "", patientId: "", patientRecord: "", consultation: "", laboratory: "", pharmacy: "", other: "", discount: "", paid: "", payment: "Cash" })
                  setShowForm(true)
                }}
              >
                {t("Create invoice")}
              </Button>
            )
          }
        />
        {loadError && <Alert tone="danger" className="mb-4">{t(loadError)}</Alert>}

        {!selectedHospital ? (
          <Card><EmptyState icon={CreditCardIcon} title={t("Select a hospital")} description="Choose a hospital in the header to view its invoices." /></Card>
        ) : (

          <>

            <DischargeBills
              hospitalId={selectedHospital.id}
              refreshKey={bills}
              onCreated={() => setBillsReloadToken((n) => n + 1)}
            />

            <AdvancePayments
              hospitalId={selectedHospital.id}
              canRefund={REFUND_ROLES.includes(activeRoleName)}
              onChanged={() => setBillsReloadToken((n) => n + 1)}
            />

            <UnbilledWork
              hospitalId={selectedHospital.id}
              canCharge={PRICING_ROLES.includes(activeRoleName)}
              onCharged={() => setBillsReloadToken((n) => n + 1)}
            />

            {refunding && (
              <RefundDialog
                invoice={refunding}
                onClose={() => setRefunding(null)}
                onRefunded={(refund) => {
                  toast.success(t("Refund of ₹{amount} recorded ({receipt}).", { amount: refund.amount, receipt: refund.receipt_number }))
                  setBillsReloadToken((n) => n + 1)
                }}
              />
            )}

            <PriceList
              hospitalId={selectedHospital.id}
              canManage={PRICING_ROLES.includes(activeRoleName)}
            />

            {/* =========================
                Statistics
            ========================= */}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">


              {/* Revenue */}

              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

                <p className="text-sm text-gray-500">
                  {t("Total Revenue")}
                </p>

                <h2 className="text-3xl font-bold text-green-600 mt-3">
                  ₹
                  {formatRupees(totalRevenue)}
                </h2>

              </div>


              {/* Outstanding */}

              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

                <p className="text-sm text-gray-500">
                  {t("Outstanding")}
                </p>

                <h2 className="text-3xl font-bold text-orange-500 mt-3">
                  ₹
                  {formatRupees(totalOutstanding)}
                </h2>

              </div>


              {/* Paid */}

              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

                <p className="text-sm text-gray-500">
                  {t("Paid Invoices")}
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

                  placeholder={t("Search patient, patient ID or invoice...")}

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

                  <option value="All Status">{t("All Status")}</option>

                  <option value="Paid">{t("Paid")}</option>

                  <option value="Partially Paid">{t("Partial")}</option>

                  <option value="Unpaid">{t("Pending")}</option>

                </select>

              </div>

            </div>


            {/* =========================
                Invoice List
            ========================= */}

            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">


              <div className="p-6 border-b">

                <h2 className="text-xl font-bold text-gray-800">
                  {t("Invoice List")}
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  {filteredBills.length}{" "}{t("invoice(s) found")}
                </p>

              </div>


              <div className="overflow-x-auto">

                <table className="w-full">


                  <thead className="bg-gray-50">

                    <tr>

                      <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                        {t("Invoice")}
                      </th>

                      <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                        {t("Patient")}
                      </th>

                      <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                        {t("Date")}
                      </th>

                      <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                        {t("Total")}
                      </th>

                      <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                        {t("Paid")}
                      </th>

                      <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                        {t("Due")}
                      </th>

                      <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                        {t("Status")}
                      </th>

                      <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                        {t("Actions")}
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

                          {t("No bills found for this hospital.")}

                        </td>

                      </tr>

                    ) : (

                      filteredBills.map(
                        (bill) => {

                          const { total, paid, due } = billPaise(bill)


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
                                {formatRupees(total)}

                              </td>


                              <td className="px-6 py-4 text-green-600 font-semibold">

                                ₹
                                {formatRupees(paid)}

                              </td>


                              <td className="px-6 py-4 text-orange-600 font-semibold">

                                ₹
                                {formatRupees(due)}

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
                                    {t("Invoice")}
                                  </button>


                                  <button

                                    onClick={() =>
                                      handleEdit(
                                        bill
                                      )
                                    }

                                    className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg"

                                  >
                                    {t("Edit")}
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
                                        {t("Payment")}
                                      </button>

                                    )}

                                  {/* Money received can be paid back (with a reason). */}
                                  {REFUND_ROLES.includes(activeRoleName) && bill.apiInvoice?.id && Number(bill.apiInvoice.total_paid) > 0 && (
                                    <button
                                      onClick={() => setRefunding(bill.apiInvoice)}
                                      className="px-3 py-2 text-sm bg-amber-50 text-amber-800 rounded-lg"
                                    >
                                      {t("Refund")}
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
                                    {t("Delete")}
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

          {/* BUG-010: announced as a dialog with its title; Escape closes it. */}
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="bill-form-title"
            onKeyDown={(e) => { if (e.key === "Escape") resetForm() }}
            className="bg-white w-full max-w-xl rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto"
          >


            <div className="flex justify-between items-center p-6 border-b">

              <div>

                <h2 id="bill-form-title" className="text-xl font-bold text-gray-800">

                  {selectedBill
                    ? t("Edit Bill")
                    : t("Create New Bill")}

                </h2>

                <p className="text-sm text-blue-600 mt-1">
                  {selectedHospital?.name}
                </p>

              </div>


              <button
                type="button"
                onClick={
                  resetForm
                }
                aria-label={t("Close")}
                className="text-2xl text-gray-500"
              >
                ×
              </button>

            </div>


            <form

              onSubmit={submitBill}

              className="p-6 space-y-5"

            >


              {/* Patient: found by search and kept by id, never matched by name (RL-03) */}

              {selectedBill ? (
                <div>
                  <p className="hms-label">{t("Patient")}</p>
                  <p className="text-sm text-ink-900">
                    {formData.patient}{formData.patientId ? ` · ${formData.patientId}` : ""}
                  </p>
                </div>
              ) : (
                <Field label="Patient" required>
                  <PatientPicker
                    hospitalId={selectedHospital?.id}
                    value={formData.patientRecord}
                    onChange={(id, patient) => setFormData((prev) => ({
                      ...prev,
                      patientRecord: id,
                      patient: patient?.name || "",
                      patientId: patient ? displayPatientId(patient) : "",
                    }))}
                  />
                </Field>
              )}


              {/* Services: not shown when only taking a payment. */}
              {!paymentOnly && (

              <div>

                <h3 className="font-semibold text-gray-800 mb-3">
                  {t("Hospital Charges")}
                </h3>


                <div className="space-y-3">


                  <p className="text-sm text-ink-600">
                    {t("Consultations, laboratory tests and bed days are billed automatically when the visit is completed, the result is verified or the stay is discharged. Do not add them here.")}
                  </p>

                  {/* B-1: shown only to keep the lines an older bill already has. */}
                  {selectedBill && (Number(formData.consultation) > 0 || Number(formData.laboratory) > 0) && (
                    <>
                  <input

                    type="number"

                    min="0"

                    step="0.01"

                    inputMode="decimal"

                    name="consultation"

                    aria-label={t("Doctor Consultation ₹")}

                    value={
                      formData.consultation
                    }

                    onChange={
                      handleChange
                    }

                    placeholder={t("Doctor Consultation ₹")}

                    className="hms-input w-full"

                  />


                  <input

                    type="number"

                    min="0"

                    step="0.01"

                    inputMode="decimal"

                    name="laboratory"

                    aria-label={t("Laboratory Charges ₹")}

                    value={
                      formData.laboratory
                    }

                    onChange={
                      handleChange
                    }

                    placeholder={t("Laboratory Charges ₹")}

                    className="hms-input w-full"

                  />
                    </>
                  )}


                  <input

                    type="number"

                    min="0"

                    step="0.01"

                    inputMode="decimal"

                    name="pharmacy"

                    aria-label={t("Pharmacy / Medicines ₹")}

                    value={
                      formData.pharmacy
                    }

                    onChange={
                      handleChange
                    }

                    placeholder={t("Pharmacy / Medicines ₹")}

                    className="hms-input w-full"

                  />


                  <input

                    type="number"

                    min="0"

                    step="0.01"

                    inputMode="decimal"

                    name="other"

                    aria-label={t("Other Charges ₹")}

                    value={
                      formData.other
                    }

                    onChange={
                      handleChange
                    }

                    placeholder={t("Other Charges ₹")}

                    className="hms-input w-full"

                  />

                  {keptLines.length > 0 && (
                    <div className="text-sm text-ink-600">
                      <p className="font-medium">{t("Other lines on this bill (kept as they are)")}</p>
                      <ul className="list-disc pl-5">
                        {keptLines.map((line, index) => (
                          <li key={`${line.description}-${index}`}>{line.description} · ₹{pricedAmount(line).toFixed(2)}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <PricedServicePicker hospitalId={selectedHospital?.id} lines={pricedLines} onChange={setPricedLines} />

                </div>

              </div>
              )}


              {/* Discount */}

              <div>

                <label htmlFor="bill-discount" className="block text-sm font-medium text-gray-700 mb-1">
                  {t("Discount")}
                </label>

                <input

                  id="bill-discount"

                    type="number"

                  min="0"

                  step="0.01"

                  inputMode="decimal"

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

                  <label htmlFor="bill-paid" className="block text-sm font-medium text-gray-700 mb-1">
                    {t("Amount Paid")}
                  </label>

                  <input

                    id="bill-paid"

                    type="number"

                    min="0"

                    step="0.01"

                    inputMode="decimal"

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

                  <label htmlFor="bill-payment" className="block text-sm font-medium text-gray-700 mb-1">
                    {t("Payment Method")}
                  </label>

                  <select

                    id="bill-payment"

                    name="payment"

                    value={
                      formData.payment
                    }

                    onChange={
                      handleChange
                    }

                    className="hms-input w-full"

                  >

                    <option value="Cash">{t("Cash")}</option>

                    <option value="UPI">{t("UPI")}</option>

                    <option value="Card">{t("Card")}</option>

                    <option value="Bank Transfer">{t("Bank Transfer")}</option>

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
                  {t("Cancel")}
                </button>


                <button

                  type="submit"

                  disabled={savingBill}

                  className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-60"

                >

                  {savingBill
                    ? t("Saving…")
                    : selectedBill
                      ? t("Save Changes")
                      : t("Generate Bill")}

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
                          {t("Hospital Management System")}
                        </p>

                      </div>

                    </div>


                    <p className="text-gray-600 mt-3">
                      {selectedHospital?.address}
                    </p>

                  </div>


                  <div className="md:text-right">

                    <h2 className="text-2xl font-bold">
                      {t("INVOICE")}
                    </h2>

                    <p className="mt-2">

                      {t("Invoice No:")}

                      <span className="font-semibold ml-2">
                        {selectedBill.id}
                      </span>

                    </p>

                    <p>

                      {t("Date:")}

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
                  {t("Patient Information")}
                </h3>


                <div className="mt-3">

                  <p className="text-lg font-bold text-gray-900">
                    {selectedBill.patient}
                  </p>

                  <p className="text-gray-600">
                    {t("Patient ID:")}{" "}{selectedBill.patientId}
                  </p>

                </div>

              </div>


              {/* Services */}

              <div className="p-8">

                <table className="w-full">

                  <thead>

                    <tr className="border-b-2 border-gray-300">

                      <th className="text-left py-3">
                        {t("Description")}
                      </th>

                      <th className="text-right py-3">
                        {t("Amount")}
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
                      {t("Subtotal")}
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
                      {t("Discount")}
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
                      {t("Total")}
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
                      {t("Paid")}
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
                      {t("Balance Due")}
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
                      {t("Payment Method")}
                    </span>

                    <span className="font-semibold">
                      {selectedBill.payment}
                    </span>

                  </div>


                  <div className="flex justify-between mt-3">

                    <span className="text-gray-500">
                      {t("Payment Status")}
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
                    {t("Thank you for choosing our hospital.")}
                  </p>

                  <p className="text-sm text-gray-500 mt-2">
                    {t("This is a computer-generated invoice.")}
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
                  {t("Close")}
                </button>


                <button

                  onClick={
                    printInvoice
                  }

                  className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700"

                >
                  <PrinterIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" />{" "}{t("Print Bill")}
                </button>

              </div>


            </div>

          </div>

        )}

    </div></>
  )
}

export default Billing