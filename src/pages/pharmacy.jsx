import { useEffect, useState, useMemo } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { usePrescription } from "../assets/context/PrescriptionContext.jsx"
import { usePharmacy } from "../assets/context/PharmacyContext.jsx"
import { LoadingSpinner } from "../components/LoadingSpinner.jsx"

// Convert "MM/YYYY" (UI) to "YYYY-MM-01" (API DateField). Returns null if invalid.
const toApiDate = (value) => {
  if (!value) return null
  const parts = String(value).trim().split("/")
  if (parts.length < 2) return null
  const [month, year] = parts
  const monthNum = Number(month)
  const yearNum = Number(year)
  if (!Number.isInteger(monthNum) || !Number.isInteger(yearNum)) return null
  if (monthNum < 1 || monthNum > 12) return null
  return `${String(yearNum).padStart(4, "0")}-${String(monthNum).padStart(2, "0")}-01`
}

const formatExpiry = (value) => {
  if (!value) return ""
  const parts = String(value).split("-")
  if (parts.length < 2) return value
  const [year, month] = parts
  return `${month}/${year}`
}

const parseExpiry = (value) => {
  if (!value) return null
  const parts = String(value).split("/")
  if (parts.length < 2) return null
  const [month, year] = parts
  return new Date(Number(year), Number(month) - 1, 1)
}

function Pharmacy() {
  const {
    loadMedicines,
    createMedicine,
    updateMedicine,
    deleteMedicine,
    loadSales,
    createSale,
    loadSuppliers,
    createSupplier,
    updateSupplier,
    deleteSupplier,
    loadPurchases,
    createPurchase,
    receivePurchase,
    loadGRNs,
    loadStockTransactions,
    adjustStock,
    suppliers,
    purchaseOrders,
    grns,
    stockTransactions,
  } = usePharmacy()

  const { selectedHospital } = usePatient()

  const {
    prescriptions,
    dispensePrescription,
  } = usePrescription()

  // =========================
  // STATE
  // =========================

  const [medicines, setMedicines] = useState([])
  const [sales, setSales] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState("")

  const [showForm, setShowForm] = useState(false)
  const [showView, setShowView] = useState(false)
  const [showIssue, setShowIssue] = useState(false)
  const [showSales, setShowSales] = useState(false)

  const [selectedMedicine, setSelectedMedicine] = useState(null)

  const [formData, setFormData] = useState({
    name: "",
    category: "",
    batch: "",
    stock: "",
    expiry: "",
    price: "",
  })

  const [issueData, setIssueData] = useState({
    medicineId: "",
    patient: "",
    quantity: "",
  })

  const [prescriptionId, setPrescriptionId] = useState("")
  const [foundPrescription, setFoundPrescription] = useState(null)

  // =========================
  // EXPIRY & LOW STOCK ALERTS
  // =========================

  // SEARCH / FILTER
  // =========================

  const [search, setSearch] =
    useState("")

  const [categoryFilter, setCategoryFilter] =
    useState("All Categories")

  const [stockFilter, setStockFilter] =
    useState("All Stock")


  const reloadPharmacyData = async () => {
    if (!selectedHospital) return
    setLoading(true)
    setLoadError("")
    try {
      const [medicinesList, salesList] = await Promise.all([
        loadMedicines(selectedHospital.id),
        loadSales(selectedHospital.id),
      ])
      setMedicines((prev) => [
        ...medicinesList,
        ...prev.filter((m) => m.hospitalId !== selectedHospital.id),
      ])
      setSales((prev) => [
        ...salesList,
        ...prev.filter((s) => s.hospitalId !== selectedHospital.id),
      ])
    } catch (error) {
      setLoadError(error?.message || "Unable to load pharmacy data.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!selectedHospital) {
      setMedicines([])
      setSales([])
      setFoundPrescription(null)
      return
    }
    reloadPharmacyData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHospital?.id])


  // =========================
  // HOSPITAL FILTER
  // =========================

  const hospitalMedicines = useMemo(
    () =>
      selectedHospital
        ? medicines.filter(
          (medicine) =>
            medicine.hospitalId ===
            selectedHospital.id
        )
        : [],
    [medicines, selectedHospital]
  )

  // Expiry and low-stock alerts (must follow hospitalMedicines: the hook
  // dependency arrays read it during render).

  const expiredMedicines = useMemo(() => {
    const now = new Date()
    return hospitalMedicines.filter((m) => {
      const exp = parseExpiry(m.expiry)
      return exp && exp < now && m.stock > 0
    })
  }, [hospitalMedicines])

  const expiringSoonMedicines = useMemo(() => {
    const now = new Date()
    const thirtyDaysLater = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000)
    return hospitalMedicines.filter((m) => {
      const exp = parseExpiry(m.expiry)
      return exp && exp >= now && exp <= thirtyDaysLater && m.stock > 0
    })
  }, [hospitalMedicines])

  const lowStockMedicines = useMemo(() =>
    hospitalMedicines.filter((m) => m.stock > 0 && m.stock <= 20), [hospitalMedicines])



  const hospitalSales =
    selectedHospital
      ? sales.filter(
        (sale) =>
          sale.hospitalId ===
          selectedHospital.id
      )
      : []


  // =========================
  // CALCULATIONS
  // =========================

  const totalMedicines =
    hospitalMedicines.length


  const totalUnits =
    hospitalMedicines.reduce(
      (total, medicine) =>
        total +
        Number(medicine.stock),
      0
    )


  const lowStock =
    hospitalMedicines.filter(
      (medicine) =>
        Number(medicine.stock) <= 20
    ).length


  const totalSales =
    hospitalSales.reduce(
      (total, sale) =>
        total +
        Number(sale.total),
      0
    )


  // =========================
  // SEARCH MEDICINES
  // =========================

  const filteredMedicines =
    hospitalMedicines.filter(
      (medicine) => {

        const matchesSearch =
          medicine.name
            .toLowerCase()
            .includes(
              search.toLowerCase()
            ) ||

          medicine.category
            .toLowerCase()
            .includes(
              search.toLowerCase()
            ) ||

          medicine.batch
            .toLowerCase()
            .includes(
              search.toLowerCase()
            )


        const matchesCategory =
          categoryFilter ===
          "All Categories" ||
          medicine.category ===
          categoryFilter


        const matchesStock =
          stockFilter ===
            "All Stock"

            ? true

            : stockFilter ===
              "Low Stock"

              ? medicine.stock <= 20

              : medicine.stock > 20


        return (
          matchesSearch &&
          matchesCategory &&
          matchesStock
        )
      }
    )


  // =========================
  // FORM
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


  const resetForm = () => {

    setFormData({
      name: "",
      category: "",
      batch: "",
      stock: "",
      expiry: "",
      price: "",
    })

    setSelectedMedicine(null)
    setShowForm(false)
  }


  const getStatus = (stock) => {

    if (
      Number(stock) <= 20
    ) {
      return "Low Stock"
    }

    return "In Stock"
  }


  // =========================
  // ADD MEDICINE
  // =========================

  const handleSubmit = async (e) => {

    e.preventDefault()


    if (!selectedHospital) {

      alert(
        "Please select a hospital first."
      )

      return
    }


    try {

      await createMedicine({

        name:
          formData.name,

        category:
          formData.category,

        batch:
          formData.batch,

        quantity:
          Number(formData.stock),

        price:
          Number(formData.price),

        expiry_date:
          toApiDate(formData.expiry),

        hospital:
          selectedHospital.id,

      })


      await reloadPharmacyData()


      resetForm()

    } catch (error) {

      alert(
        error?.message ||
        "Unable to add medicine."
      )

    }
  }


  // =========================
  // EDIT
  // =========================

  const handleEdit = (
    medicine
  ) => {

    setSelectedMedicine(
      medicine
    )


    setFormData({

      name:
        medicine.name,

      category:
        medicine.category,

      batch:
        medicine.batch,

      stock:
        String(
          medicine.stock
        ),

      expiry:
        medicine.expiry,

      price:
        String(
          medicine.price
        ),

    })


    setShowForm(true)
  }


  const handleUpdate = async (e) => {

    e.preventDefault()


    if (!selectedMedicine) {
      return
    }


    try {

      await updateMedicine(
        selectedMedicine.id,
        {

          name:
            formData.name,

          category:
            formData.category,

          batch:
            formData.batch,

          quantity:
            Number(
              formData.stock
            ),

          price:
            Number(
              formData.price
            ),

          expiry_date:
            toApiDate(formData.expiry),

        }
      )


      await reloadPharmacyData()


      resetForm()

    } catch (error) {

      alert(
        error?.message ||
        "Unable to update medicine."
      )

    }
  }


  // =========================
  // DELETE
  // =========================

  const handleDelete = async (
    id
  ) => {

    const confirmed =
      window.confirm(
        "Are you sure you want to delete this medicine?"
      )


    if (!confirmed) {
      return
    }


    try {

      await deleteMedicine(id)

      await reloadPharmacyData()

    } catch (error) {

      alert(
        error?.message ||
        "Unable to delete medicine."
      )

    }
  }


  // =========================
  // VIEW
  // =========================

  const handleView = (
    medicine
  ) => {

    setSelectedMedicine(
      medicine
    )

    setShowView(true)
  }


  // =========================
  // ISSUE MEDICINE
  // =========================

  const handleIssueChange = (
    e
  ) => {

    const {
      name,
      value,
    } = e.target


    setIssueData({
      ...issueData,
      [name]: value,
    })
  }


  const resetIssue = () => {

    setIssueData({
      medicineId: "",
      patient: "",
      quantity: "",
    })

    setShowIssue(false)
  }


  const handleIssueMedicine = async (
    e
  ) => {

    e.preventDefault()


    if (!selectedHospital) {

      alert(
        "Please select a hospital first."
      )

      return
    }


    const medicine =
      hospitalMedicines.find(
        (item) =>
          item.id ===
          issueData.medicineId
      )


    if (!medicine) {

      alert(
        "Please select a medicine."
      )

      return
    }


    if (
      !issueData.patient.trim()
    ) {

      alert(
        "Please enter the patient name."
      )

      return
    }


    const quantity =
      Number(
        issueData.quantity
      )


    if (quantity <= 0) {

      alert(
        "Quantity must be greater than 0."
      )

      return
    }


    if (
      quantity >
      medicine.stock
    ) {

      alert(
        `Only ${medicine.stock} units are available.`
      )

      return
    }


    try {

      await createSale({

        medicine:
          medicine.id,

        hospital:
          selectedHospital.id,

        patient_name:
          issueData.patient,

        quantity,

      })


      await reloadPharmacyData()


      alert(
        `${quantity} ${medicine.name} issued successfully.`
      )


      resetIssue()

    } catch (error) {

      await reloadPharmacyData()


      alert(
        error?.message ||
        "Unable to issue medicine."
      )

    }
  }


  // =========================
  // PRESCRIPTION SEARCH
  // =========================

  const searchPrescription = () => {

    if (!selectedHospital) {

      alert(
        "Please select a hospital first."
      )

      return
    }


    if (
      !prescriptionId.trim()
    ) {

      alert(
        "Please enter Prescription ID."
      )

      return
    }


    const prescription =
      prescriptions.find(
        (item) =>

          item.id
            .toLowerCase() ===
          prescriptionId
            .trim()
            .toLowerCase()

          &&

          item.hospitalId ===
          selectedHospital.id
      )


    if (!prescription) {

      setFoundPrescription(
        null
      )

      alert(
        "Prescription not found for this hospital."
      )

      return
    }


    setFoundPrescription(
      prescription
    )
  }


  // =========================
  // PRESCRIPTION DISPENSE
  // =========================

  const handlePrescriptionDispense = async () => {

    if (
      !foundPrescription ||
      !selectedHospital
    ) {
      return
    }


    if (
      foundPrescription.status ===
      "Dispensed"
    ) {

      alert(
        "This prescription has already been dispensed."
      )

      return
    }


    const prescribedMedicines =
      foundPrescription.medicines || []


    if (
      prescribedMedicines.length === 0
    ) {

      alert(
        "This prescription has no medicines to dispense."
      )

      return
    }


    // Multi-medicine prescriptions are NOT supported here.
    // The backend Sale API dispenses one medicine atomically,
    // so we refuse rather than risk a partial dispense.
    if (
      prescribedMedicines.length > 1
    ) {

      alert(
        "This prescription contains multiple medicines. Automatic dispensing is not supported yet — please issue each medicine from the Issue Medicine section."
      )

      return
    }


    const prescriptionMedicine =
      prescribedMedicines[0]


    const inventoryMedicine =
      hospitalMedicines.find(
        (medicine) =>

          medicine.name
            .toLowerCase() ===
          prescriptionMedicine.name
            .toLowerCase()
      )


    if (!inventoryMedicine) {

      alert(
        `${prescriptionMedicine.name} is not available in ${selectedHospital.name} pharmacy stock.`
      )

      return
    }


    const quantity =
      Number(
        prescriptionMedicine.quantity
      )


    if (
      Number(
        inventoryMedicine.stock
      ) <
      quantity
    ) {

      alert(
        `Insufficient stock for ${prescriptionMedicine.name}. Available: ${inventoryMedicine.stock}`
      )

      return
    }


    try {

      await createSale({

        medicine:
          inventoryMedicine.id,

        hospital:
          selectedHospital.id,

        patient_name:
          foundPrescription.patientName,

        quantity,

        prescription:
          foundPrescription.apiId,

      })


      await reloadPharmacyData()


      await dispensePrescription(
        foundPrescription.id
      )


      setFoundPrescription({

        ...foundPrescription,

        status:
          "Dispensed",

      })


      alert(
        `Prescription ${foundPrescription.id} dispensed successfully.`
      )

    } catch (error) {

      await reloadPharmacyData()


      alert(
        error?.message ||
        "Unable to dispense prescription."
      )

    }
  }


  // =========================
  // STATUS CLASS
  // =========================

  const getStatusClass = (
    status
  ) => {

    if (
      status ===
      "In Stock"
    ) {

      return "bg-green-100 text-green-700"
    }


    return "bg-orange-100 text-orange-700"
  }


  return (

    <div>


      {/* =========================
          HEADER
      ========================= */}

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">

        <div>

          <p className="text-blue-600 font-semibold text-sm">
            PHARMACY MANAGEMENT
          </p>

          <h1 className="text-3xl font-bold text-gray-800">
            Pharmacy
          </h1>

          <p className="text-gray-500 mt-1">
            Manage medicines, stock, prescriptions and pharmacy sales
          </p>

        </div>


        <div className="flex flex-wrap gap-3">

          <button

            onClick={() => {

              if (!selectedHospital) {

                alert(
                  "Please select a hospital first."
                )

                return
              }

              setShowSales(true)

            }}

            className="px-5 py-3 border border-gray-300 rounded-xl font-medium hover:bg-gray-50"
          >
            🧾 Sales History
          </button>


          <button

            onClick={() => {

              if (!selectedHospital) {

                alert(
                  "Please select a hospital first."
                )

                return
              }

              setIssueData({

                medicineId: "",
                patient: "",
                quantity: "",

              })

              setShowIssue(true)

            }}

            className="px-5 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700"
          >
            💊 Issue Medicine
          </button>


          <button

            onClick={() => {

              if (!selectedHospital) {

                alert(
                  "Please select a hospital first."
                )

                return
              }

              setSelectedMedicine(
                null
              )

              setFormData({

                name: "",
                category: "",
                batch: "",
                stock: "",
                expiry: "",
                price: "",

              })

              setShowForm(true)

            }}

            className="px-5 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700"
          >
            + Add Medicine
          </button>

        </div>

      </div>


      {/* =========================
          CURRENT HOSPITAL
      ========================= */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        {selectedHospital ? (

          <div className="flex items-center gap-4">

            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">
              🏥
            </div>

            <div>

              <p className="text-xs text-gray-500">
                Current Hospital
              </p>

              <h2 className="font-bold text-gray-800">
                {selectedHospital.name}
              </h2>

              <p className="text-sm text-gray-500">
                📍 {selectedHospital.address}
              </p>

            </div>

          </div>

        ) : (

          <div>

            <p className="font-semibold text-orange-600">
              ⚠️ No hospital selected
            </p>

            <p className="text-sm text-gray-500 mt-1">
              Select a hospital from the header first.
            </p>

          </div>

        )}

      </div>


      {loadError && (

        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-4 mb-6 flex items-center justify-between gap-4">

          <p className="text-sm">
            ⚠️ {loadError}
          </p>

          <button
            onClick={reloadPharmacyData}
            className="px-4 py-2 bg-red-600 text-white rounded-xl text-sm font-medium hover:bg-red-700"
          >
            Retry
          </button>

        </div>

      )}


      {!selectedHospital ? (

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">

          <div className="text-5xl mb-4">
            💊
          </div>

          <h2 className="text-xl font-bold text-gray-800">
            Select a Hospital
          </h2>

          <p className="text-gray-500 mt-2">
            Select a hospital from the header to view pharmacy data.
          </p>

        </div>

      ) : (

        <>


          {/* =========================
              PRESCRIPTION DISPENSING
          ========================= */}

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">

            <p className="text-blue-600 font-semibold text-sm">
              PRESCRIPTION DISPENSING
            </p>

            <h2 className="text-xl font-bold text-gray-800 mt-1">
              Search Doctor Prescription
            </h2>

            <p className="text-sm text-gray-500 mt-1">
              Enter the confirmed prescription ID generated by the doctor.
            </p>


            <div className="flex flex-col md:flex-row gap-3 mt-5">

              <input

                type="text"

                value={
                  prescriptionId
                }

                onChange={(e) =>
                  setPrescriptionId(
                    e.target.value
                  )
                }

                placeholder="RX-2026-001"

                className="flex-1 border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"

              />


              <button

                onClick={
                  searchPrescription
                }

                className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700"

              >
                🔎 Search Prescription
              </button>

            </div>


            {foundPrescription && (

              <div className="mt-6 border border-gray-200 rounded-2xl overflow-hidden">


                <div className="bg-gray-50 p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">

                  <div>

                    <p className="text-xs text-gray-500">
                      Prescription ID
                    </p>

                    <p className="text-lg font-bold text-blue-600">
                      {foundPrescription.id}
                    </p>

                  </div>


                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${foundPrescription.status ===
                      "Dispensed"
                      ? "bg-green-100 text-green-700"
                      : "bg-blue-100 text-blue-700"
                      }`}
                  >
                    {foundPrescription.status}
                  </span>

                </div>


                <div className="p-5">


                  {/* Patient */}

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

                    <div>

                      <p className="text-xs text-gray-500">
                        Patient
                      </p>

                      <p className="font-semibold text-gray-800">
                        {
                          foundPrescription.patientName
                        }
                      </p>

                    </div>


                    <div>

                      <p className="text-xs text-gray-500">
                        Patient ID
                      </p>

                      <p className="font-semibold text-gray-800">
                        {
                          foundPrescription.patientId
                        }
                      </p>

                    </div>


                    <div>

                      <p className="text-xs text-gray-500">
                        Doctor
                      </p>

                      <p className="font-semibold text-gray-800">
                        {
                          foundPrescription.doctor
                        }
                      </p>

                    </div>

                  </div>


                  {/* Medicines */}

                  <div className="mt-6">

                    <h3 className="font-bold text-gray-800 mb-3">
                      Prescribed Medicines
                    </h3>


                    <div className="space-y-3">

                      {
                        foundPrescription.medicines.map(
                          (
                            medicine,
                            index
                          ) => {

                            const stockMedicine =
                              hospitalMedicines.find(
                                (item) =>
                                  item.name
                                    .toLowerCase() ===
                                  medicine.name
                                    .toLowerCase()
                              )


                            const availableStock =
                              stockMedicine
                                ? stockMedicine.stock
                                : 0


                            const enoughStock =
                              Number(
                                availableStock
                              ) >=
                              Number(
                                medicine.quantity
                              )


                            return (

                              <div

                                key={
                                  index
                                }

                                className="border border-gray-200 rounded-xl p-4"

                              >

                                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">


                                  <div>

                                    <p className="font-semibold text-gray-800">
                                      {
                                        medicine.name
                                      }
                                    </p>

                                    <p className="text-sm text-gray-500">
                                      {
                                        medicine.dosage
                                      }

                                      {" • "}

                                      {
                                        medicine.frequency
                                      }

                                      {" • "}

                                      {
                                        medicine.duration
                                      }
                                    </p>

                                  </div>


                                  <div className="text-sm">

                                    <p>

                                      Required:

                                      {" "}

                                      <span className="font-bold">
                                        {
                                          medicine.quantity
                                        }
                                      </span>

                                    </p>


                                    <p
                                      className={
                                        enoughStock
                                          ? "text-green-600"
                                          : "text-red-600"
                                      }
                                    >

                                      Stock:

                                      {" "}

                                      <span className="font-bold">
                                        {
                                          availableStock
                                        }
                                      </span>

                                    </p>

                                  </div>

                                </div>

                              </div>

                            )
                          }
                        )
                      }

                    </div>

                  </div>


                  {/* Multi-medicine limitation */}

                  {foundPrescription.medicines &&
                    foundPrescription.medicines.length > 1 && (

                      <div className="mt-4 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-4 text-sm">

                        ⚠️ This prescription has multiple medicines. Automatic one-click dispensing is not supported yet — please use the Issue Medicine section for each medicine.

                      </div>

                    )}


                  {/* Dispense */}

                  {foundPrescription.status !==
                    "Dispensed" && (

                      <button

                        onClick={
                          handlePrescriptionDispense
                        }

                        className="mt-6 w-full md:w-auto px-6 py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700"

                      >
                        ✓ Dispense Prescription
                      </button>

                    )}

                </div>

              </div>

            )}

          </div>


          {/* =========================
              STATISTICS
          ========================= */}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-6">


            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

              <p className="text-sm text-gray-500">
                Total Medicines
              </p>

              <h2 className="text-3xl font-bold text-blue-600 mt-3">
                {totalMedicines}
              </h2>

            </div>


            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

              <p className="text-sm text-gray-500">
                Available Units
              </p>

              <h2 className="text-3xl font-bold text-green-600 mt-3">
                {totalUnits}
              </h2>

            </div>


            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

              <p className="text-sm text-gray-500">
                Low Stock
              </p>

              <h2 className="text-3xl font-bold text-orange-500 mt-3">
                {lowStock}
              </h2>

            </div>


            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

              <p className="text-sm text-gray-500">
                Pharmacy Sales
              </p>

              <h2 className="text-3xl font-bold text-purple-600 mt-3">
                ₹
                {totalSales.toLocaleString(
                  "en-IN"
                )}
              </h2>

            </div>

          </div>

          {/* =========================
              ALERTS: EXPIRED / EXPIRING / LOW STOCK
          ========================= */}

          {(expiredMedicines.length > 0 || expiringSoonMedicines.length > 0 || lowStockMedicines.length > 0) && (
            <div className="mb-6 space-y-3">
              {expiredMedicines.length > 0 && (
                <div className="bg-red-50 border border-red-200 text-red-800 rounded-xl p-4 flex items-start gap-3">
                  <span className="text-2xl">⚠️</span>
                  <div>
                    <p className="font-semibold">Expired Medicines in Stock</p>
                    <p className="text-sm mt-1">
                      {expiredMedicines.length} medicine(s) have expired but still have stock:
                    </p>
                    <ul className="text-sm mt-2 list-disc list-inside max-h-32 overflow-y-auto">
                      {expiredMedicines.slice(0, 10).map((m) => (
                        <li key={m.id}>{m.name} (Batch: {m.batch || "N/A"}, Expiry: {m.expiry}, Stock: {m.stock})</li>
                      ))}
                      {expiredMedicines.length > 10 && (
                        <li>+{expiredMedicines.length - 10} more...</li>
                      )}
                    </ul>
                  </div>
                </div>
              )}
              {expiringSoonMedicines.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-4 flex items-start gap-3">
                  <span className="text-2xl">⏰</span>
                  <div>
                    <p className="font-semibold">Expiring Soon (within 30 days)</p>
                    <p className="text-sm mt-1">
                      {expiringSoonMedicines.length} medicine(s) expiring soon:
                    </p>
                    <ul className="text-sm mt-2 list-disc list-inside max-h-32 overflow-y-auto">
                      {expiringSoonMedicines.slice(0, 10).map((m) => (
                        <li key={m.id}>{m.name} (Batch: {m.batch || "N/A"}, Expiry: {m.expiry}, Stock: {m.stock})</li>
                      ))}
                      {expiringSoonMedicines.length > 10 && (
                        <li>+{expiringSoonMedicines.length - 10} more...</li>
                      )}
                    </ul>
                  </div>
                </div>
              )}
              {lowStockMedicines.length > 0 && (
                <div className="bg-orange-50 border border-orange-200 text-orange-800 rounded-xl p-4 flex items-start gap-3">
                  <span className="text-2xl">📉</span>
                  <div>
                    <p className="font-semibold">Low Stock Alert</p>
                    <p className="text-sm mt-1">
                      {lowStockMedicines.length} medicine(s) at or below reorder level (≤20 units):
                    </p>
                    <ul className="text-sm mt-2 list-disc list-inside max-h-32 overflow-y-auto">
                      {lowStockMedicines.slice(0, 10).map((m) => (
                        <li key={m.id}>{m.name} (Stock: {m.stock})</li>
                      ))}
                      {lowStockMedicines.length > 10 && (
                        <li>+{lowStockMedicines.length - 10} more...</li>
                      )}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* =========================
              SEARCH FILTER
          ========================= */}

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">


              <input

                type="text"

                value={
                  search
                }

                onChange={(e) =>
                  setSearch(
                    e.target.value
                  )
                }

                placeholder="Search medicine, category or batch..."

                className="border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"

              />


              <select

                value={
                  categoryFilter
                }

                onChange={(e) =>
                  setCategoryFilter(
                    e.target.value
                  )
                }

                className="border border-gray-300 rounded-xl px-4 py-3"

              >

                <option>
                  All Categories
                </option>

                <option>
                  Tablet
                </option>

                <option>
                  Capsule
                </option>

                <option>
                  Injection
                </option>

                <option>
                  Syrup
                </option>

              </select>


              <select

                value={
                  stockFilter
                }

                onChange={(e) =>
                  setStockFilter(
                    e.target.value
                  )
                }

                className="border border-gray-300 rounded-xl px-4 py-3"

              >

                <option>
                  All Stock
                </option>

                <option>
                  In Stock
                </option>

                <option>
                  Low Stock
                </option>

              </select>

            </div>

          </div>


          {/* =========================
              MEDICINE INVENTORY
          ========================= */}

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

            <div className="p-6 border-b">

              <h2 className="text-xl font-bold text-gray-800">
                Medicine Inventory
              </h2>

              <p className="text-sm text-gray-500 mt-1">
                {loading
                  ? "Loading medicines…"
                  : `${filteredMedicines.length} medicine(s) found`}
              </p>

            </div>


            {filteredMedicines.length === 0 ? (

              <div className="p-12 text-center">

                <div className="text-4xl mb-3">
                  💊
                </div>

                <h3 className="font-bold text-gray-800">
                  No medicines found
                </h3>

                <p className="text-sm text-gray-500 mt-1">
                  No medicine matches the current filters.
                </p>

              </div>

            ) : (

              <div className="overflow-x-auto">

                <table className="w-full">

                  <thead className="bg-gray-50">

                    <tr>

                      <th className="text-left px-6 py-4">
                        Medicine
                      </th>

                      <th className="text-left px-6 py-4">
                        Category
                      </th>

                      <th className="text-left px-6 py-4">
                        Batch
                      </th>

                      <th className="text-left px-6 py-4">
                        Stock
                      </th>

                      <th className="text-left px-6 py-4">
                        Expiry
                      </th>

                      <th className="text-left px-6 py-4">
                        Price
                      </th>

                      <th className="text-left px-6 py-4">
                        Status
                      </th>

                      <th className="text-left px-6 py-4">
                        Actions
                      </th>

                    </tr>

                  </thead>


                  <tbody>

                    {filteredMedicines.map(
                      (medicine) => (

                        <tr
                          key={
                            medicine.id
                          }
                          className="border-t hover:bg-gray-50"
                        >

                          <td className="px-6 py-4">

                            <p className="font-semibold text-gray-800">
                              {
                                medicine.name
                              }
                            </p>

                            <p className="text-xs text-gray-500">
                              {
                                medicine.id
                              }
                            </p>

                          </td>


                          <td className="px-6 py-4 text-gray-600">
                            {
                              medicine.category
                            }
                          </td>


                          <td className="px-6 py-4 text-gray-600">
                            {
                              medicine.batch
                            }
                          </td>


                          <td className="px-6 py-4">

                            <span
                              className={
                                medicine.stock <=
                                  20
                                  ? "font-bold text-orange-600"
                                  : "font-semibold"
                              }
                            >
                              {
                                medicine.stock
                              }
                            </span>

                          </td>


                          <td className="px-6 py-4 text-gray-600">
                            {
                              medicine.expiry
                            }
                          </td>


                          <td className="px-6 py-4 font-semibold">
                            ₹
                            {
                              medicine.price
                            }
                          </td>


                          <td className="px-6 py-4">

                            <span
                              className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                                medicine.status
                              )}`}
                            >
                              {
                                medicine.status
                              }
                            </span>

                          </td>


                          <td className="px-6 py-4">

                            <div className="flex gap-2 flex-wrap">


                              <button

                                onClick={() =>
                                  handleView(
                                    medicine
                                  )
                                }

                                className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg"

                              >
                                View
                              </button>


                              <button

                                onClick={() =>
                                  handleEdit(
                                    medicine
                                  )
                                }

                                className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg"

                              >
                                Edit
                              </button>


                              <button

                                onClick={() => {

                                  setIssueData({

                                    medicineId:
                                      medicine.id,

                                    patient:
                                      "",

                                    quantity:
                                      "",

                                  })

                                  setShowIssue(
                                    true
                                  )

                                }}

                                disabled={
                                  medicine.stock ===
                                  0
                                }

                                className="px-3 py-2 text-sm bg-purple-50 text-purple-700 rounded-lg disabled:opacity-50"

                              >
                                Issue
                              </button>


                              <button

                                onClick={() =>
                                  handleDelete(
                                    medicine.id
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
                    )}

                  </tbody>

                </table>

              </div>

            )}

          </div>


          {/* =========================
              ADD / EDIT MODAL
          ========================= */}

          {showForm && (

            <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

              <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">


                <div className="flex justify-between items-center p-6 border-b">

                  <div>

                    <h2 className="text-xl font-bold text-gray-800">

                      {
                        selectedMedicine
                          ? "Edit Medicine"
                          : "Add Medicine"
                      }

                    </h2>

                    <p className="text-sm text-gray-500 mt-1">
                      {
                        selectedHospital.name
                      }
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
                    selectedMedicine
                      ? handleUpdate
                      : handleSubmit
                  }

                  className="p-6 space-y-4"

                >


                  <input

                    type="text"

                    name="name"

                    value={
                      formData.name
                    }

                    onChange={
                      handleChange
                    }

                    required

                    placeholder="Medicine Name"

                    className="w-full border border-gray-300 rounded-xl px-4 py-3"

                  />


                  <select

                    name="category"

                    value={
                      formData.category
                    }

                    onChange={
                      handleChange
                    }

                    required

                    className="w-full border border-gray-300 rounded-xl px-4 py-3"

                  >

                    <option value="">
                      Select Category
                    </option>

                    <option>
                      Tablet
                    </option>

                    <option>
                      Capsule
                    </option>

                    <option>
                      Injection
                    </option>

                    <option>
                      Syrup
                    </option>

                  </select>


                  <input

                    type="text"

                    name="batch"

                    value={
                      formData.batch
                    }

                    onChange={
                      handleChange
                    }

                    required

                    placeholder="Batch Number"

                    className="w-full border border-gray-300 rounded-xl px-4 py-3"

                  />


                  <input

                    type="number"

                    name="stock"

                    min="0"

                    value={
                      formData.stock
                    }

                    onChange={
                      handleChange
                    }

                    required

                    placeholder="Stock Quantity"

                    className="w-full border border-gray-300 rounded-xl px-4 py-3"

                  />


                  <input

                    type="month"

                    value={

                      formData.expiry

                        ? formData.expiry
                          .split("/")
                          .reverse()
                          .join("-")
                          .slice(
                            0,
                            7
                          )

                        : ""

                    }

                    onChange={(e) => {

                      const [
                        year,
                        month,
                      ] =
                        e.target.value.split(
                          "-"
                        )


                      setFormData({

                        ...formData,

                        expiry:
                          `${month}/${year}`,

                      })

                    }}

                    required

                    className="w-full border border-gray-300 rounded-xl px-4 py-3"

                  />


                  <input

                    type="number"

                    name="price"

                    min="0"

                    step="0.01"

                    value={
                      formData.price
                    }

                    onChange={
                      handleChange
                    }

                    required

                    placeholder="Price"

                    className="w-full border border-gray-300 rounded-xl px-4 py-3"

                  />


                  <div className="flex justify-end gap-3 pt-4">

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

                      className="px-5 py-3 bg-blue-600 text-white rounded-xl"

                    >

                      {
                        selectedMedicine
                          ? "Save Changes"
                          : "Add Medicine"
                      }

                    </button>

                  </div>


                </form>

              </div>

            </div>

          )}


          {/* =========================
              VIEW MODAL
          ========================= */}

          {showView &&
            selectedMedicine && (

              <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

                <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">


                  <div className="flex justify-between items-center p-6 border-b">

                    <div>

                      <h2 className="text-xl font-bold">
                        Medicine Details
                      </h2>

                      <p className="text-sm text-blue-600">
                        {
                          selectedMedicine.id
                        }
                      </p>

                    </div>


                    <button

                      onClick={() =>
                        setShowView(
                          false
                        )
                      }

                      className="text-2xl text-gray-500"

                    >
                      ×
                    </button>

                  </div>


                  <div className="p-6 space-y-4">


                    <div>

                      <p className="text-sm text-gray-500">
                        Hospital
                      </p>

                      <p className="font-semibold">
                        {
                          selectedHospital.name
                        }
                      </p>

                    </div>


                    <div>

                      <p className="text-sm text-gray-500">
                        Medicine
                      </p>

                      <p className="font-bold text-lg">
                        {
                          selectedMedicine.name
                        }
                      </p>

                    </div>


                    <div className="grid grid-cols-2 gap-4">


                      <div className="bg-gray-50 rounded-xl p-4">

                        <p className="text-xs text-gray-500">
                          Stock
                        </p>

                        <p className="font-bold text-lg">
                          {
                            selectedMedicine.stock
                          }
                        </p>

                      </div>


                      <div className="bg-gray-50 rounded-xl p-4">

                        <p className="text-xs text-gray-500">
                          Price
                        </p>

                        <p className="font-bold text-lg">
                          ₹
                          {
                            selectedMedicine.price
                          }
                        </p>

                      </div>


                      <div className="bg-gray-50 rounded-xl p-4">

                        <p className="text-xs text-gray-500">
                          Batch
                        </p>

                        <p className="font-semibold">
                          {
                            selectedMedicine.batch
                          }
                        </p>

                      </div>


                      <div className="bg-gray-50 rounded-xl p-4">

                        <p className="text-xs text-gray-500">
                          Expiry
                        </p>

                        <p className="font-semibold">
                          {
                            selectedMedicine.expiry
                          }
                        </p>

                      </div>

                    </div>


                    <div>

                      <p className="text-sm text-gray-500">
                        Status
                      </p>

                      <span
                        className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                          selectedMedicine.status
                        )}`}
                      >
                        {
                          selectedMedicine.status
                        }
                      </span>

                    </div>

                  </div>


                  <div className="p-6 border-t flex justify-end">

                    <button

                      onClick={() =>
                        setShowView(
                          false
                        )
                      }

                      className="px-5 py-3 bg-gray-800 text-white rounded-xl"

                    >
                      Close
                    </button>

                  </div>

                </div>

              </div>

            )}


          {/* =========================
              ISSUE MODAL
          ========================= */}

          {showIssue && (

            <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

              <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl">


                <div className="flex justify-between items-center p-6 border-b">

                  <div>

                    <h2 className="text-xl font-bold">
                      Issue Medicine
                    </h2>

                    <p className="text-sm text-blue-600">
                      {
                        selectedHospital.name
                      }
                    </p>

                  </div>


                  <button

                    onClick={
                      resetIssue
                    }

                    className="text-2xl text-gray-500"

                  >
                    ×
                  </button>

                </div>


                <form

                  onSubmit={
                    handleIssueMedicine
                  }

                  className="p-6 space-y-4"

                >


                  <select

                    name="medicineId"

                    value={
                      issueData.medicineId
                    }

                    onChange={
                      handleIssueChange
                    }

                    required

                    className="w-full border border-gray-300 rounded-xl px-4 py-3"

                  >

                    <option value="">
                      Select Medicine
                    </option>


                    {
                      hospitalMedicines
                        .filter(
                          (medicine) =>
                            medicine.stock >
                            0
                        )
                        .map(
                          (medicine) => (

                            <option
                              key={
                                medicine.id
                              }
                              value={
                                medicine.id
                              }
                            >
                              {
                                medicine.name
                              }
                              {" — Stock: "}
                              {
                                medicine.stock
                              }
                            </option>

                          )
                        )
                    }

                  </select>


                  <input

                    type="text"

                    name="patient"

                    value={
                      issueData.patient
                    }

                    onChange={
                      handleIssueChange
                    }

                    required

                    placeholder="Patient Name"

                    className="w-full border border-gray-300 rounded-xl px-4 py-3"

                  />


                  <input

                    type="number"

                    name="quantity"

                    min="1"

                    value={
                      issueData.quantity
                    }

                    onChange={
                      handleIssueChange
                    }

                    required

                    placeholder="Quantity"

                    className="w-full border border-gray-300 rounded-xl px-4 py-3"

                  />


                  <div className="flex justify-end gap-3 pt-4">

                    <button

                      type="button"

                      onClick={
                        resetIssue
                      }

                      className="px-5 py-3 border border-gray-300 rounded-xl"

                    >
                      Cancel
                    </button>


                    <button

                      type="submit"

                      className="px-5 py-3 bg-green-600 text-white rounded-xl"

                    >
                      Issue Medicine
                    </button>

                  </div>


                </form>

              </div>

            </div>

          )}


          {/* =========================
              SALES HISTORY
          ========================= */}

          {showSales && (

            <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

              <div className="bg-white w-full max-w-5xl rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">


                <div className="flex justify-between items-center p-6 border-b">

                  <div>

                    <h2 className="text-xl font-bold">
                      Pharmacy Sales History
                    </h2>

                    <p className="text-sm text-gray-500 mt-1">
                      {
                        selectedHospital.name
                      }
                    </p>

                  </div>


                  <button

                    onClick={() =>
                      setShowSales(
                        false
                      )
                    }

                    className="text-2xl text-gray-500"

                  >
                    ×
                  </button>

                </div>


                {hospitalSales.length ===
                  0 ? (

                  <div className="p-12 text-center text-gray-500">

                    <div className="text-4xl mb-3">
                      🧾
                    </div>

                    No medicine sales yet.

                  </div>

                ) : (

                  <div className="overflow-x-auto">

                    <table className="w-full">

                      <thead className="bg-gray-50">

                        <tr>

                          <th className="text-left px-6 py-4">
                            Sale ID
                          </th>

                          <th className="text-left px-6 py-4">
                            Medicine
                          </th>

                          <th className="text-left px-6 py-4">
                            Patient
                          </th>

                          <th className="text-left px-6 py-4">
                            Quantity
                          </th>

                          <th className="text-left px-6 py-4">
                            Total
                          </th>

                          <th className="text-left px-6 py-4">
                            Prescription
                          </th>

                          <th className="text-left px-6 py-4">
                            Date
                          </th>

                        </tr>

                      </thead>


                      <tbody>

                        {
                          hospitalSales.map(
                            (sale) => (

                              <tr
                                key={
                                  sale.id
                                }
                                className="border-t"
                              >

                                <td className="px-6 py-4 font-semibold text-blue-600">
                                  {
                                    sale.id
                                  }
                                </td>


                                <td className="px-6 py-4 font-medium">
                                  {
                                    sale.medicineName
                                  }
                                </td>


                                <td className="px-6 py-4">
                                  {
                                    sale.patient
                                  }
                                </td>


                                <td className="px-6 py-4">
                                  {
                                    sale.quantity
                                  }
                                </td>


                                <td className="px-6 py-4 font-semibold">
                                  ₹
                                  {
                                    sale.total.toLocaleString(
                                      "en-IN"
                                    )
                                  }
                                </td>


                                <td className="px-6 py-4">

                                  {sale.prescriptionId ? (

                                    <span className="text-blue-600 font-medium">
                                      {
                                        sale.prescriptionId
                                      }
                                    </span>

                                  ) : (

                                    <span className="text-gray-400">
                                      Direct Issue
                                    </span>

                                  )}

                                </td>


                                <td className="px-6 py-4">
                                  {
                                    sale.date
                                  }
                                </td>

                              </tr>

                            )
                          )
                        }

                      </tbody>

                    </table>

                  </div>

                )}


                <div className="p-6 border-t flex justify-end">

                  <button

                    onClick={() =>
                      setShowSales(
                        false
                      )
                    }

                    className="px-5 py-3 bg-gray-800 text-white rounded-xl"

                  >
                    Close
                  </button>

                </div>

              </div>

            </div>

          )}

        </>

      )}

    </div>
  )
}

export default Pharmacy