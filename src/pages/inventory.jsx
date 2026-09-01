import { useState } from "react"

function Inventory() {
  const [items, setItems] = useState([
    {
      id: "INV001",
      name: "Surgical Gloves",
      category: "Medical Supplies",
      unit: "Box",
      quantity: 120,
      minStock: 30,
      supplier: "MedSupply India",
      expiry: "12/2027",
      status: "In Stock",
    },
    {
      id: "INV002",
      name: "Face Masks",
      category: "Medical Supplies",
      unit: "Box",
      quantity: 45,
      minStock: 50,
      supplier: "HealthCare Supplies",
      expiry: "08/2028",
      status: "Low Stock",
    },
    {
      id: "INV003",
      name: "IV Cannula 20G",
      category: "Surgical",
      unit: "Piece",
      quantity: 250,
      minStock: 50,
      supplier: "MediTech",
      expiry: "06/2029",
      status: "In Stock",
    },
    {
      id: "INV004",
      name: "Syringe 5ml",
      category: "Medical Supplies",
      unit: "Box",
      quantity: 20,
      minStock: 25,
      supplier: "SafeMed",
      expiry: "10/2028",
      status: "Low Stock",
    },
  ])

  const [transactions, setTransactions] = useState([])

  const [search, setSearch] = useState("")
  const [categoryFilter, setCategoryFilter] =
    useState("All Categories")

  const [stockFilter, setStockFilter] =
    useState("All Stock")

  const [showForm, setShowForm] = useState(false)
  const [showView, setShowView] = useState(false)
  const [showStock, setShowStock] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  const [selectedItem, setSelectedItem] = useState(null)

  const [formData, setFormData] = useState({
    name: "",
    category: "",
    unit: "",
    quantity: "",
    minStock: "",
    supplier: "",
    expiry: "",
  })

  const [stockData, setStockData] = useState({
    type: "Add Stock",
    quantity: "",
    reason: "",
  })

  // =========================
  // STATISTICS
  // =========================

  const totalItems = items.length

  const totalQuantity = items.reduce(
    (total, item) =>
      total + Number(item.quantity),
    0
  )

  const lowStockItems = items.filter(
    (item) =>
      Number(item.quantity) <=
      Number(item.minStock)
  ).length

  const outOfStockItems = items.filter(
    (item) => Number(item.quantity) === 0
  ).length

  // =========================
  // FILTER
  // =========================

  const filteredItems = items.filter((item) => {
    const matchesSearch =
      item.name
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      item.id
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      item.supplier
        .toLowerCase()
        .includes(search.toLowerCase())

    const matchesCategory =
      categoryFilter === "All Categories" ||
      item.category === categoryFilter

    const matchesStock =
      stockFilter === "All Stock" ||
      (stockFilter === "In Stock" &&
        item.quantity > item.minStock) ||
      (stockFilter === "Low Stock" &&
        item.quantity > 0 &&
        item.quantity <= item.minStock) ||
      (stockFilter === "Out of Stock" &&
        item.quantity === 0)

    return (
      matchesSearch &&
      matchesCategory &&
      matchesStock
    )
  })

  // =========================
  // FORM
  // =========================

  const handleChange = (e) => {
    const { name, value } = e.target

    setFormData({
      ...formData,
      [name]: value,
    })
  }

  const handleStockChange = (e) => {
    const { name, value } = e.target

    setStockData({
      ...stockData,
      [name]: value,
    })
  }

  const getStatus = (quantity, minStock) => {
    const stock = Number(quantity)
    const minimum = Number(minStock)

    if (stock === 0) {
      return "Out of Stock"
    }

    if (stock <= minimum) {
      return "Low Stock"
    }

    return "In Stock"
  }

  const resetForm = () => {
    setFormData({
      name: "",
      category: "",
      unit: "",
      quantity: "",
      minStock: "",
      supplier: "",
      expiry: "",
    })

    setSelectedItem(null)
    setShowForm(false)
  }

  // =========================
  // ADD ITEM
  // =========================

  const handleSubmit = (e) => {
    e.preventDefault()

    const newItem = {
      id: `INV${String(
        items.length + 1
      ).padStart(3, "0")}`,

      name: formData.name,
      category: formData.category,
      unit: formData.unit,
      quantity: Number(formData.quantity),
      minStock: Number(formData.minStock),
      supplier: formData.supplier,
      expiry: formData.expiry,

      status: getStatus(
        formData.quantity,
        formData.minStock
      ),
    }

    setItems([
      ...items,
      newItem,
    ])

    resetForm()
  }

  // =========================
  // EDIT ITEM
  // =========================

  const handleEdit = (item) => {
    setSelectedItem(item)

    setFormData({
      name: item.name,
      category: item.category,
      unit: item.unit,
      quantity: String(item.quantity),
      minStock: String(item.minStock),
      supplier: item.supplier,
      expiry: item.expiry,
    })

    setShowForm(true)
  }

  const handleUpdate = (e) => {
    e.preventDefault()

    const updatedItems = items.map(
      (item) =>
        item.id === selectedItem.id
          ? {
            ...item,

            name: formData.name,
            category: formData.category,
            unit: formData.unit,
            quantity: Number(
              formData.quantity
            ),
            minStock: Number(
              formData.minStock
            ),
            supplier: formData.supplier,
            expiry: formData.expiry,

            status: getStatus(
              formData.quantity,
              formData.minStock
            ),
          }
          : item
    )

    setItems(updatedItems)

    resetForm()
  }

  // =========================
  // DELETE
  // =========================

  const handleDelete = (id) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this inventory item?"
    )

    if (!confirmed) {
      return
    }

    setItems(
      items.filter(
        (item) => item.id !== id
      )
    )
  }

  // =========================
  // VIEW
  // =========================

  const handleView = (item) => {
    setSelectedItem(item)
    setShowView(true)
  }

  // =========================
  // STOCK UPDATE
  // =========================

  const openStockModal = (item) => {
    setSelectedItem(item)

    setStockData({
      type: "Add Stock",
      quantity: "",
      reason: "",
    })

    setShowStock(true)
  }

  const resetStock = () => {
    setStockData({
      type: "Add Stock",
      quantity: "",
      reason: "",
    })

    setSelectedItem(null)
    setShowStock(false)
  }

  const handleStockUpdate = (e) => {
    e.preventDefault()

    if (!selectedItem) {
      return
    }

    const quantity =
      Number(stockData.quantity)

    if (quantity <= 0) {
      alert(
        "Quantity must be greater than 0."
      )
      return
    }

    let newQuantity

    if (
      stockData.type === "Add Stock"
    ) {
      newQuantity =
        Number(selectedItem.quantity) +
        quantity
    } else {
      if (
        quantity >
        Number(selectedItem.quantity)
      ) {
        alert(
          `Only ${selectedItem.quantity} ${selectedItem.unit} available.`
        )
        return
      }

      newQuantity =
        Number(selectedItem.quantity) -
        quantity
    }

    const updatedItems = items.map(
      (item) =>
        item.id === selectedItem.id
          ? {
            ...item,

            quantity: newQuantity,

            status: getStatus(
              newQuantity,
              item.minStock
            ),
          }
          : item
    )

    setItems(updatedItems)

    // Transaction history
    const newTransaction = {
      id: `TRX${String(
        transactions.length + 1
      ).padStart(3, "0")}`,

      itemId: selectedItem.id,

      itemName: selectedItem.name,

      type: stockData.type,

      quantity,

      reason:
        stockData.reason ||
        "Manual stock update",

      date:
        new Date().toLocaleDateString(
          "en-IN"
        ),
    }

    setTransactions([
      newTransaction,
      ...transactions,
    ])

    alert(
      `${selectedItem.name} stock updated successfully.`
    )

    resetStock()
  }

  // =========================
  // STATUS STYLE
  // =========================

  const getStatusClass = (status) => {
    if (status === "In Stock") {
      return "bg-green-100 text-green-700"
    }

    if (status === "Low Stock") {
      return "bg-orange-100 text-orange-700"
    }

    return "bg-red-100 text-red-700"
  }

  return (
    <div>

      {/* =========================
          HEADER
      ========================= */}

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">

        <div>

          <h1 className="text-3xl font-bold text-gray-800">
            Inventory
          </h1>

          <p className="text-gray-500 mt-1">
            Manage hospital supplies, equipment and stock
          </p>

        </div>

        <div className="flex flex-wrap gap-3">

          <button
            onClick={() =>
              setShowHistory(true)
            }
            className="px-5 py-3 border border-gray-300 rounded-xl font-medium hover:bg-gray-50"
          >
            📋 Stock History
          </button>

          <button
            onClick={() => {
              setSelectedItem(null)

              setFormData({
                name: "",
                category: "",
                unit: "",
                quantity: "",
                minStock: "",
                supplier: "",
                expiry: "",
              })

              setShowForm(true)
            }}
            className="px-5 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700"
          >
            + Add Item
          </button>

        </div>

      </div>

      {/* =========================
          STATISTICS
      ========================= */}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-6">

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Total Items
          </p>

          <h2 className="text-3xl font-bold text-blue-600 mt-3">
            {totalItems}
          </h2>

        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Total Units
          </p>

          <h2 className="text-3xl font-bold text-green-600 mt-3">
            {totalQuantity}
          </h2>

        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Low Stock
          </p>

          <h2 className="text-3xl font-bold text-orange-500 mt-3">
            {lowStockItems}
          </h2>

        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">

          <p className="text-sm text-gray-500">
            Out of Stock
          </p>

          <h2 className="text-3xl font-bold text-red-600 mt-3">
            {outOfStockItems}
          </h2>

        </div>

      </div>

      {/* =========================
          SEARCH & FILTER
      ========================= */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          <input
            type="text"
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
            placeholder="Search item, ID or supplier..."
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
              Medical Supplies
            </option>

            <option>
              Surgical
            </option>

            <option>
              Equipment
            </option>

            <option>
              General
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

            <option>
              Out of Stock
            </option>

          </select>

        </div>

      </div>

      {/* =========================
          INVENTORY TABLE
      ========================= */}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

        <div className="p-6 border-b">

          <h2 className="text-xl font-bold text-gray-800">
            Inventory Items
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            {filteredItems.length} item(s) found
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
                  Item
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Category
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Unit
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Quantity
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Min Stock
                </th>

                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  Supplier
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

              {filteredItems.length === 0 ? (

                <tr>

                  <td
                    colSpan="9"
                    className="text-center py-12 text-gray-500"
                  >
                    No inventory items found
                  </td>

                </tr>

              ) : (

                filteredItems.map(
                  (item) => (

                    <tr
                      key={item.id}
                      className="border-t hover:bg-gray-50"
                    >

                      <td className="px-6 py-4 font-semibold text-blue-600">
                        {item.id}
                      </td>

                      <td className="px-6 py-4">

                        <p className="font-semibold text-gray-800">
                          {item.name}
                        </p>

                        <p className="text-xs text-gray-500">
                          Expiry: {item.expiry}
                        </p>

                      </td>

                      <td className="px-6 py-4 text-gray-600">
                        {item.category}
                      </td>

                      <td className="px-6 py-4 text-gray-600">
                        {item.unit}
                      </td>

                      <td className="px-6 py-4">

                        <span
                          className={
                            item.quantity <=
                              item.minStock
                              ? "font-bold text-orange-600"
                              : "font-semibold"
                          }
                        >
                          {item.quantity}
                        </span>

                      </td>

                      <td className="px-6 py-4 text-gray-600">
                        {item.minStock}
                      </td>

                      <td className="px-6 py-4 text-gray-600">
                        {item.supplier}
                      </td>

                      <td className="px-6 py-4">

                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                            item.status
                          )}`}
                        >
                          {item.status}
                        </span>

                      </td>

                      <td className="px-6 py-4">

                        <div className="flex gap-2 flex-wrap">

                          <button
                            onClick={() =>
                              handleView(item)
                            }
                            className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg"
                          >
                            View
                          </button>

                          <button
                            onClick={() =>
                              handleEdit(item)
                            }
                            className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg"
                          >
                            Edit
                          </button>

                          <button
                            onClick={() =>
                              openStockModal(item)
                            }
                            className="px-3 py-2 text-sm bg-purple-50 text-purple-700 rounded-lg"
                          >
                            Stock
                          </button>

                          <button
                            onClick={() =>
                              handleDelete(
                                item.id
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
                  {selectedItem
                    ? "Edit Inventory Item"
                    : "Add Inventory Item"}
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Enter inventory details
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
                selectedItem
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
                placeholder="Item Name"
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
                  Medical Supplies
                </option>

                <option>
                  Surgical
                </option>

                <option>
                  Equipment
                </option>

                <option>
                  General
                </option>

              </select>

              <select
                name="unit"
                value={formData.unit}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 rounded-xl px-4 py-3"
              >

                <option value="">
                  Select Unit
                </option>

                <option>
                  Piece
                </option>

                <option>
                  Box
                </option>

                <option>
                  Pack
                </option>

                <option>
                  Bottle
                </option>

              </select>

              <input
                type="number"
                name="quantity"
                min="0"
                value={formData.quantity}
                onChange={handleChange}
                required
                placeholder="Current Quantity"
                className="w-full border border-gray-300 rounded-xl px-4 py-3"
              />

              <input
                type="number"
                name="minStock"
                min="0"
                value={formData.minStock}
                onChange={handleChange}
                required
                placeholder="Minimum Stock Level"
                className="w-full border border-gray-300 rounded-xl px-4 py-3"
              />

              <input
                type="text"
                name="supplier"
                value={formData.supplier}
                onChange={handleChange}
                required
                placeholder="Supplier Name"
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
                    : ""
                }
                onChange={(e) => {

                  if (!e.target.value) {
                    setFormData({
                      ...formData,
                      expiry: "",
                    })

                    return
                  }

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
                  {selectedItem
                    ? "Save Changes"
                    : "Add Item"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

      {/* =========================
          STOCK MODAL
      ========================= */}

      {showStock &&
        selectedItem && (

          <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

            <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl">

              <div className="flex justify-between items-center p-6 border-b">

                <div>

                  <h2 className="text-xl font-bold text-gray-800">
                    Update Stock
                  </h2>

                  <p className="text-sm text-gray-500 mt-1">
                    {selectedItem.name}
                  </p>

                </div>

                <button
                  onClick={resetStock}
                  className="text-2xl text-gray-500"
                >
                  ×
                </button>

              </div>

              <form
                onSubmit={handleStockUpdate}
                className="p-6 space-y-5"
              >

                <div className="bg-blue-50 rounded-xl p-4">

                  <div className="flex justify-between">

                    <span>
                      Current Stock
                    </span>

                    <span className="font-bold">
                      {selectedItem.quantity}{" "}
                      {selectedItem.unit}
                    </span>

                  </div>

                </div>

                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Operation
                  </label>

                  <select
                    name="type"
                    value={stockData.type}
                    onChange={
                      handleStockChange
                    }
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  >

                    <option>
                      Add Stock
                    </option>

                    <option>
                      Remove Stock
                    </option>

                  </select>

                </div>

                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Quantity
                  </label>

                  <input
                    type="number"
                    name="quantity"
                    min="1"
                    value={
                      stockData.quantity
                    }
                    onChange={
                      handleStockChange
                    }
                    required
                    placeholder="Enter quantity"
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  />

                </div>

                <div>

                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Reason
                  </label>

                  <input
                    type="text"
                    name="reason"
                    value={
                      stockData.reason
                    }
                    onChange={
                      handleStockChange
                    }
                    placeholder="Purchase, damaged, adjustment..."
                    className="w-full border border-gray-300 rounded-xl px-4 py-3"
                  />

                </div>

                <div className="flex justify-end gap-3">

                  <button
                    type="button"
                    onClick={resetStock}
                    className="px-5 py-3 border border-gray-300 rounded-xl"
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="px-5 py-3 bg-purple-600 text-white rounded-xl"
                  >
                    Update Stock
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
        selectedItem && (

          <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

            <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">

              <div className="flex justify-between items-center p-6 border-b">

                <div>

                  <h2 className="text-xl font-bold">
                    Inventory Details
                  </h2>

                  <p className="text-sm text-blue-600">
                    {selectedItem.id}
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

              <div className="p-6 space-y-5">

                <div>

                  <p className="text-sm text-gray-500">
                    Item
                  </p>

                  <p className="text-lg font-bold">
                    {selectedItem.name}
                  </p>

                </div>

                <div className="grid grid-cols-2 gap-4">

                  <div className="bg-gray-50 rounded-xl p-4">

                    <p className="text-xs text-gray-500">
                      Current Stock
                    </p>

                    <p className="text-xl font-bold mt-1">
                      {selectedItem.quantity}
                    </p>

                  </div>

                  <div className="bg-gray-50 rounded-xl p-4">

                    <p className="text-xs text-gray-500">
                      Minimum Stock
                    </p>

                    <p className="text-xl font-bold mt-1">
                      {selectedItem.minStock}
                    </p>

                  </div>

                  <div className="bg-gray-50 rounded-xl p-4">

                    <p className="text-xs text-gray-500">
                      Unit
                    </p>

                    <p className="font-semibold mt-1">
                      {selectedItem.unit}
                    </p>

                  </div>

                  <div className="bg-gray-50 rounded-xl p-4">

                    <p className="text-xs text-gray-500">
                      Expiry
                    </p>

                    <p className="font-semibold mt-1">
                      {selectedItem.expiry}
                    </p>

                  </div>

                </div>

                <div>

                  <p className="text-sm text-gray-500">
                    Supplier
                  </p>

                  <p className="font-semibold">
                    {selectedItem.supplier}
                  </p>

                </div>

                <div>

                  <p className="text-sm text-gray-500">
                    Status
                  </p>

                  <span
                    className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(
                      selectedItem.status
                    )}`}
                  >
                    {selectedItem.status}
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
          STOCK HISTORY MODAL
      ========================= */}

      {showHistory && (

        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">

          <div className="bg-white w-full max-w-4xl rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">

            <div className="flex justify-between items-center p-6 border-b">

              <div>

                <h2 className="text-xl font-bold">
                  Stock History
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Inventory stock transactions
                </p>

              </div>

              <button
                onClick={() =>
                  setShowHistory(false)
                }
                className="text-2xl text-gray-500"
              >
                ×
              </button>

            </div>

            {transactions.length === 0 ? (

              <div className="p-12 text-center text-gray-500">
                No stock transactions yet.
              </div>

            ) : (

              <div className="overflow-x-auto">

                <table className="w-full">

                  <thead className="bg-gray-50">

                    <tr>

                      <th className="text-left px-6 py-4">
                        Transaction
                      </th>

                      <th className="text-left px-6 py-4">
                        Item
                      </th>

                      <th className="text-left px-6 py-4">
                        Operation
                      </th>

                      <th className="text-left px-6 py-4">
                        Quantity
                      </th>

                      <th className="text-left px-6 py-4">
                        Reason
                      </th>

                      <th className="text-left px-6 py-4">
                        Date
                      </th>

                    </tr>

                  </thead>

                  <tbody>

                    {transactions.map(
                      (transaction) => (

                        <tr
                          key={
                            transaction.id
                          }
                          className="border-t"
                        >

                          <td className="px-6 py-4 font-semibold text-blue-600">
                            {transaction.id}
                          </td>

                          <td className="px-6 py-4 font-medium">
                            {transaction.itemName}
                          </td>

                          <td className="px-6 py-4">

                            <span
                              className={
                                transaction.type ===
                                  "Add Stock"
                                  ? "text-green-600 font-semibold"
                                  : "text-red-600 font-semibold"
                              }
                            >
                              {transaction.type}
                            </span>

                          </td>

                          <td className="px-6 py-4 font-semibold">
                            {transaction.quantity}
                          </td>

                          <td className="px-6 py-4 text-gray-600">
                            {transaction.reason}
                          </td>

                          <td className="px-6 py-4 text-gray-600">
                            {transaction.date}
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
                  setShowHistory(false)
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

export default Inventory