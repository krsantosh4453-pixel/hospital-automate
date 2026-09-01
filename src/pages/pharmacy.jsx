import { useState } from "react"

function Pharmacy() {
  const [medicines, setMedicines] = useState([
    {
      id: "M001",
      name: "Paracetamol 500mg",
      category: "Tablet",
      batch: "PCM2026A",
      stock: 250,
      expiry: "12/2027",
      price: 2.5,
      status: "In Stock",
    },
    {
      id: "M002",
      name: "Amoxicillin 500mg",
      category: "Capsule",
      batch: "AMX2026B",
      stock: 85,
      expiry: "08/2027",
      price: 6,
      status: "In Stock",
    },
    {
      id: "M003",
      name: "Azithromycin 500mg",
      category: "Tablet",
      batch: "AZI2026C",
      stock: 18,
      expiry: "05/2027",
      price: 12,
      status: "Low Stock",
    },
    {
      id: "M004",
      name: "Insulin",
      category: "Injection",
      batch: "INS2026D",
      stock: 5,
      expiry: "02/2027",
      price: 450,
      status: "Low Stock",
    },
  ])

  const [sales, setSales] = useState([])

  const [search, setSearch] = useState("")
  const [categoryFilter, setCategoryFilter] =
    useState("All Categories")

  const [stockFilter, setStockFilter] =
    useState("All Stock")

  const [showForm, setShowForm] = useState(false)
  const [showView, setShowView] = useState(false)
  const [showIssue, setShowIssue] = useState(false)
  const [showSales, setShowSales] = useState(false)

  const [selectedMedicine, setSelectedMedicine] =
    useState(null)

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


  /* =========================
     CALCULATIONS
  ========================= */

  const totalMedicines = medicines.length

  const totalUnits = medicines.reduce(
    (total, medicine) =>
      total + Number(medicine.stock),
    0
  )

  const lowStock = medicines.filter(
    (medicine) => medicine.stock <= 20
  ).length

  const totalSales = sales.reduce(
    (total, sale) =>
      total + Number(sale.total),
    0
  )


  /* =========================
     FILTER
  ========================= */

  const filteredMedicines = medicines.filter(
    (medicine) => {

      const matchesSearch =
        medicine.name
          .toLowerCase()
          .includes(search.toLowerCase()) ||
        medicine.id
          .toLowerCase()
          .includes(search.toLowerCase()) ||
        medicine.batch
          .toLowerCase()
          .includes(search.toLowerCase())

      const matchesCategory =
        categoryFilter === "All Categories" ||
        medicine.category === categoryFilter

      const matchesStock =
        stockFilter === "All Stock" ||
        (stockFilter === "In Stock" &&
          medicine.stock > 20) ||
        (stockFilter === "Low Stock" &&
          medicine.stock <= 20)

      return (
        matchesSearch &&
        matchesCategory &&
        matchesStock
      )
    }
  )


  /* =========================
     FORM
  ========================= */

  const handleChange = (e) => {
    const { name, value } = e.target

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
    if (Number(stock) <= 20) {
      return "Low Stock"
    }

    return "In Stock"
  }


  /* =========================
     ADD MEDICINE
  ========================= */

  const handleSubmit = (e) => {
    e.preventDefault()

    const newMedicine = {
      id: `M${String(
        medicines.length + 1
      ).padStart(3, "0")}`,

      name: formData.name,
      category: formData.category,
      batch: formData.batch,
      stock: Number(formData.stock),
      expiry: formData.expiry,
      price: Number(formData.price),

      status: getStatus(formData.stock),
    }

    setMedicines([
      ...medicines,
      newMedicine,
    ])

    resetForm()
  }


  /* =========================
     EDIT
  ========================= */

  const handleEdit = (medicine) => {
    setSelectedMedicine(medicine)

    setFormData({
      name: medicine.name,
      category: medicine.category,
      batch: medicine.batch,
      stock: String(medicine.stock),
      expiry: medicine.expiry,
      price: String(medicine.price),
    })

    setShowForm(true)
  }


  const handleUpdate = (e) => {
    e.preventDefault()

    const updatedMedicines =
      medicines.map((medicine) =>
        medicine.id === selectedMedicine.id
          ? {
            ...medicine,

            name: formData.name,
            category: formData.category,
            batch: formData.batch,
            stock: Number(formData.stock),
            expiry: formData.expiry,
            price: Number(formData.price),

            status: getStatus(
              formData.stock
            ),
          }
          : medicine
      )

    setMedicines(updatedMedicines)

    resetForm()
  }


  /* =========================
     DELETE
  ========================= */

  const handleDelete = (id) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this medicine?"
    )

    if (!confirmed) {
      return
    }

    setMedicines(
      medicines.filter(
        (medicine) =>
          medicine.id !== id
      )
    )
  }


  /* =========================
     VIEW
  ========================= */

  const handleView = (medicine) => {
    setSelectedMedicine(medicine)
    setShowView(true)
  }


  /* =========================
     ISSUE MEDICINE
  ========================= */

  const handleIssueChange = (e) => {
    const { name, value } = e.target

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


  const handleIssueMedicine = (e) => {
    e.preventDefault()

    const medicine = medicines.find(
      (item) =>
        item.id === issueData.medicineId
    )

    if (!medicine) {
      alert("Please select a medicine.")
      return
    }

    const quantity =
      Number(issueData.quantity)

    if (quantity <= 0) {
      alert(
        "Quantity must be greater than 0."
      )
      return
    }

    if (quantity > medicine.stock) {
      alert(
        `Only ${medicine.stock} units are available.`
      )
      return
    }

    const remainingStock =
      medicine.stock - quantity

    /* Automatic stock update */

    const updatedMedicines =
      medicines.map((item) =>
        item.id === medicine.id
          ? {
            ...item,

            stock: remainingStock,

            status:
              getStatus(
                remainingStock
              ),
          }
          : item
      )

    setMedicines(updatedMedicines)


    /* Create sale record */

    const newSale = {
      id: `SALE${String(
        sales.length + 1
      ).padStart(3, "0")}`,

      medicineId: medicine.id,

      medicineName:
        medicine.name,

      patient:
        issueData.patient,

      quantity,

      price: medicine.price,

      total:
        quantity *
        medicine.price,

      date:
        new Date().toLocaleDateString(
          "en-IN"
        ),
    }

    setSales([
      newSale,
      ...sales,
    ])

    alert(
      `${quantity} ${medicine.name} issued successfully.`
    )

    resetIssue()
  }


  /* =========================
     STATUS
  ========================= */

  const getStatusClass = (status) => {

    if (status === "In Stock") {
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

          <h1 className="text-3xl font-bold text-gray-800">
            Pharmacy
          </h1>

          <p className="text-gray-500 mt-1">
            Manage medicines, stock and pharmacy sales
          </p>

        </div>


        <div className="flex flex-wrap gap-3">

          <button
            onClick={() =>
              setShowSales(true)
            }
            className="px-5 py-3 border border-gray-300 rounded-xl font-medium hover:bg-gray-50"
          >
            🧾 Sales History
          </button>


          <button
            onClick={() => {
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
              setSelectedMedicine(null)

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
            ₹{totalSales.toLocaleString("en-IN")}
          </h2>

        </div>

      </div>


      {/* =========================
          SEARCH FILTER
      ========================= */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <input
            type="text"
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
            placeholder="Search medicine, ID or batch..."
            className="border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
          />


          <select
            value={categoryFilter}
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
            value={stockFilter}
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
          MEDICINE TABLE
      ========================= */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

        <div className="p-6 border-b">

          <h2 className="text-xl font-bold text-gray-800">
            Medicine Inventory
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            {filteredMedicines.length} medicine(s) found
          </p>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="bg-gray-50">

              <tr>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  ID
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Medicine
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Category
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Batch
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Stock
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Expiry
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Price
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

              {filteredMedicines.map(
                (medicine) => (

                  <tr
                    key={medicine.id}
                    className="border-t hover:bg-gray-50"
                  >

                    <td className="px-6 py-4 font-semibold text-blue-600">
                      {medicine.id}
                    </td>


                    <td className="px-6 py-4">

                      <p className="font-semibold text-gray-800">
                        {medicine.name}
                      </p>

                    </td>


                    <td className="px-6 py-4 text-gray-600">
                      {medicine.category}
                    </td>


                    <td className="px-6 py-4 text-gray-600">
                      {medicine.batch}
                    </td>


                    <td className="px-6 py-4">

                      <span
                        className={
                          medicine.stock <= 20
                            ? "font-bold text-orange-600"
                            : "font-semibold"
                        }
                      >
                        {medicine.stock}
                      </span>

                    </td>


                    <td className="px-6 py-4 text-gray-600">
                      {medicine.expiry}
                    </td>


                    <td className="px-6 py-4 font-semibold">
                      ₹{medicine.price}
                    </td>


                    <td className="px-6 py-4">

                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                          medicine.status
                        )}`}
                      >
                        {medicine.status}
                      </span>

                    </td>


                    <td className="px-6 py-4">

                      <div className="flex gap-2 flex-wrap">

                        <button
                          onClick={() =>
                            handleIssueMedicine
                          }
                          className="hidden"
                        >
                          Issue
                        </button>


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
                              patient: "",
                              quantity: "",
                            })

                            setShowIssue(true)
                          }}
                          disabled={
                            medicine.stock === 0
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
                  {selectedMedicine
                    ? "Edit Medicine"
                    : "Add Medicine"}
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Medicine information
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
                selectedMedicine
                  ? handleUpdate
                  : handleSubmit
              }
              className="p-6 space-y-4"
            >

              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                placeholder="Medicine Name"
                className="w-full border border-gray-300 rounded-xl px-4 py-3"
              />


              <select
                name="category"
                value={formData.category}
                onChange={handleChange}
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
                value={formData.batch}
                onChange={handleChange}
                required
                placeholder="Batch Number"
                className="w-full border border-gray-300 rounded-xl px-4 py-3"
              />


              <input
                type="number"
                name="stock"
                min="0"
                value={formData.stock}
                onChange={handleChange}
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
                      .slice(0, 7)
                    : ""
                }
                onChange={(e) => {

                  const [year, month] =
                    e.target.value.split("-")

                  setFormData({
                    ...formData,
                    expiry: `${month}/${year}`,
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
                value={formData.price}
                onChange={handleChange}
                required
                placeholder="Price per unit"
                className="w-full border border-gray-300 rounded-xl px-4 py-3"
              />


              <div className="flex justify-end gap-3 pt-4">

                <button
                  type="button"
                  onClick={resetForm}
                  className="px-5 py-3 border border-gray-300 rounded-xl"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-5 py-3 bg-blue-600 text-white rounded-xl"
                >
                  {selectedMedicine
                    ? "Save Changes"
                    : "Add Medicine"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}


      {/* =========================
          ISSUE MEDICINE MODAL
      ========================= */}

      {showIssue && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl">

            <div className="flex justify-between items-center p-6 border-b">

              <div>

                <h2 className="text-xl font-bold text-gray-800">
                  Issue Medicine
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Medicine issue to patient
                </p>

              </div>

              <button
                onClick={resetIssue}
                className="text-2xl text-gray-500"
              >
                ×
              </button>

            </div>


            <form
              onSubmit={
                handleIssueMedicine
              }
              className="p-6 space-y-5"
            >

              {/* Medicine */}

              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Medicine
                </label>

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

                  {medicines
                    .filter(
                      (medicine) =>
                        medicine.stock > 0
                    )
                    .map(
                      (medicine) => (

                        <option
                          key={medicine.id}
                          value={medicine.id}
                        >
                          {medicine.name} — Stock:{" "}
                          {medicine.stock}
                        </option>

                      )
                    )}

                </select>

              </div>


              {/* Patient */}

              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Patient Name
                </label>

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
                  placeholder="Patient name"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3"
                />

              </div>


              {/* Quantity */}

              <div>

                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantity
                </label>

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
                  placeholder="Enter quantity"
                  className="w-full border border-gray-300 rounded-xl px-4 py-3"
                />

              </div>


              {/* Preview */}

              {issueData.medicineId &&
                issueData.quantity && (

                  <div className="bg-blue-50 rounded-xl p-4">

                    {(() => {

                      const medicine =
                        medicines.find(
                          (item) =>
                            item.id ===
                            issueData.medicineId
                        )

                      if (!medicine) {
                        return null
                      }

                      const quantity =
                        Number(
                          issueData.quantity
                        )

                      return (
                        <div>

                          <div className="flex justify-between">

                            <span>
                              Unit Price
                            </span>

                            <span className="font-semibold">
                              ₹
                              {medicine.price}
                            </span>

                          </div>


                          <div className="flex justify-between mt-2">

                            <span>
                              Quantity
                            </span>

                            <span className="font-semibold">
                              {quantity}
                            </span>

                          </div>


                          <div className="flex justify-between border-t mt-3 pt-3">

                            <span className="font-bold">
                              Total
                            </span>

                            <span className="font-bold text-blue-600">
                              ₹
                              {(
                                medicine.price *
                                quantity
                              ).toLocaleString(
                                "en-IN"
                              )}
                            </span>

                          </div>

                        </div>
                      )

                    })()}

                  </div>

                )}


              <div className="flex justify-end gap-3">

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
                  className="px-5 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700"
                >
                  Issue Medicine
                </button>

              </div>

            </form>

          </div>

        </div>

      )}


      {/* =========================
          VIEW MEDICINE MODAL
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
                    {selectedMedicine.id}
                  </p>

                </div>

                <button
                  onClick={() =>
                    setShowView(false)
                  }
                  className="text-2xl text-gray-500"
                >
                  ×
                </button>

              </div>


              <div className="p-6 space-y-4">

                <div>

                  <p className="text-sm text-gray-500">
                    Medicine
                  </p>

                  <p className="font-bold text-lg">
                    {selectedMedicine.name}
                  </p>

                </div>


                <div className="grid grid-cols-2 gap-4">

                  <div className="bg-gray-50 rounded-xl p-4">

                    <p className="text-xs text-gray-500">
                      Stock
                    </p>

                    <p className="font-bold text-lg">
                      {selectedMedicine.stock}
                    </p>

                  </div>


                  <div className="bg-gray-50 rounded-xl p-4">

                    <p className="text-xs text-gray-500">
                      Price
                    </p>

                    <p className="font-bold text-lg">
                      ₹
                      {selectedMedicine.price}
                    </p>

                  </div>


                  <div className="bg-gray-50 rounded-xl p-4">

                    <p className="text-xs text-gray-500">
                      Batch
                    </p>

                    <p className="font-semibold">
                      {selectedMedicine.batch}
                    </p>

                  </div>


                  <div className="bg-gray-50 rounded-xl p-4">

                    <p className="text-xs text-gray-500">
                      Expiry
                    </p>

                    <p className="font-semibold">
                      {selectedMedicine.expiry}
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
                    {selectedMedicine.status}
                  </span>

                </div>

              </div>


              <div className="p-6 border-t flex justify-end">

                <button
                  onClick={() =>
                    setShowView(false)
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
          SALES HISTORY
      ========================= */}

      {showSales && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white w-full max-w-4xl rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">

            <div className="flex justify-between items-center p-6 border-b">

              <div>

                <h2 className="text-xl font-bold">
                  Pharmacy Sales History
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Medicine issue records
                </p>

              </div>

              <button
                onClick={() =>
                  setShowSales(false)
                }
                className="text-2xl text-gray-500"
              >
                ×
              </button>

            </div>


            {sales.length === 0 ? (

              <div className="p-12 text-center text-gray-500">
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
                        Date
                      </th>

                    </tr>

                  </thead>


                  <tbody>

                    {sales.map(
                      (sale) => (

                        <tr
                          key={sale.id}
                          className="border-t"
                        >

                          <td className="px-6 py-4 font-semibold text-blue-600">
                            {sale.id}
                          </td>

                          <td className="px-6 py-4 font-medium">
                            {sale.medicineName}
                          </td>

                          <td className="px-6 py-4">
                            {sale.patient}
                          </td>

                          <td className="px-6 py-4">
                            {sale.quantity}
                          </td>

                          <td className="px-6 py-4 font-semibold">
                            ₹
                            {sale.total.toLocaleString(
                              "en-IN"
                            )}
                          </td>

                          <td className="px-6 py-4">
                            {sale.date}
                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>

              </div>

            )}


            <div className="p-6 border-t flex justify-end">

              <button
                onClick={() =>
                  setShowSales(false)
                }
                className="px-5 py-3 bg-gray-800 text-white rounded-xl"
              >
                Close
              </button>

            </div>

          </div>

        </div>

      )}

    </div>
  )
}

export default Pharmacy