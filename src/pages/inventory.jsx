import { useState, useMemo, useEffect, useCallback } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import { LoadingSpinner } from "../components/LoadingSpinner.jsx"
import { ClipboardListIcon, HospitalIcon, MapPinIcon, PackageIcon, TriangleAlertIcon } from "lucide-react"
import { useToast } from "../components/Toast.jsx"
import { useConfirm } from "../components/ui"

function Inventory() {
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()

  const { selectedHospital } = usePatient()

  const [medicines, setMedicines] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [purchaseOrders, setPurchaseOrders] = useState([])
  const [grns, setGrns] = useState([])
  const [stockTransactions, setStockTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stockLoading, setStockLoading] = useState(false)

  const fetchAllData = useCallback(async () => {
    if (!selectedHospital) return

    setLoading(true)
    setError(null)
    try {
      const [
        medicinesRes,
        suppliersRes,
        purchasesRes,
        grnsRes,
        stockRes,
      ] = await Promise.all([
        api.pharmacy.medicines.list(selectedHospital.id),
        api.procurement.suppliers.list(selectedHospital.id),
        api.procurement.purchases.list(selectedHospital.id),
        api.procurement.grns.list(selectedHospital.id),
        api.procurement.stockTransactions.list(selectedHospital.id),
      ])

      const meds = medicinesRes?.results || medicinesRes || []
      const mappedMedicines = meds.map((m) => ({
        id: m.id,
        name: m.name || "",
        category: m.category || "General",
        unit: "Piece",
        quantity: Number(m.quantity || 0),
        minStock: 20,
        supplier: "Unknown",
        expiry: m.expiry_date
          ? new Date(m.expiry_date).toLocaleDateString("en-IN", {
              month: "2-digit",
              year: "numeric",
            })
          : "N/A",
        status:
          Number(m.quantity || 0) === 0
            ? "Out of Stock"
            : Number(m.quantity || 0) <= 20
            ? "Low Stock"
            : "In Stock",
        hospitalId: selectedHospital.id,
        apiId: m.id,
        batch: m.batch || "",
        price: Number(m.price || 0),
      }))

      setMedicines(mappedMedicines)
      setSuppliers(suppliersRes?.results || suppliersRes || [])
      setPurchaseOrders(purchasesRes?.results || purchasesRes || [])
      setGrns(grnsRes?.results || grnsRes || [])
      setStockTransactions(stockRes?.results || stockRes || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [selectedHospital?.id])

  useEffect(() => {
    fetchAllData()
  }, [fetchAllData])

  const [transactions, setTransactions] = useState([])

  const [search, setSearch] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("All Categories")
  const [stockFilter, setStockFilter] = useState("All Stock")

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

  const hospitalItems = useMemo(
    () => medicines.filter((item) => item.hospitalId === selectedHospital?.id),
    [medicines, selectedHospital]
  )

  const hospitalTransactions = useMemo(
    () =>
      transactions.filter((t) => t.hospitalId === selectedHospital?.id),
    [transactions, selectedHospital]
  )

  const categories = useMemo(
    () => ["All Categories", ...new Set(hospitalItems.map((i) => i.category))],
    [hospitalItems]
  )

  if (!selectedHospital) {
    return (
      <>{confirmDialog}<div>
        <div className="mb-6">
          <p className="text-blue-600 font-semibold text-sm">
            INVENTORY MANAGEMENT
          </p>
          <h1 className="text-3xl font-bold text-gray-800 mt-1">Inventory</h1>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
          <div className="text-5xl mb-4"><HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <h2 className="text-xl font-bold text-gray-800">Select a Hospital</h2>
          <p className="text-gray-500 mt-2">
            Select a hospital from the header to view its inventory.
          </p>
        </div>
      </div></>
    )
  }

  const totalItems = hospitalItems.length
  const totalQuantity = hospitalItems.reduce(
    (total, item) => total + Number(item.quantity),
    0
  )
  const lowStockItems = hospitalItems.filter(
    (item) =>
      Number(item.quantity) <= Number(item.minStock) && Number(item.quantity) > 0
  ).length
  const outOfStockItems = hospitalItems.filter(
    (item) => Number(item.quantity) === 0
  ).length

  const filteredItems = hospitalItems.filter((item) => {
    const matchesSearch =
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.id.toString().toLowerCase().includes(search.toLowerCase()) ||
      (item.supplier || "").toLowerCase().includes(search.toLowerCase())

    const matchesCategory =
      categoryFilter === "All Categories" || item.category === categoryFilter

    const matchesStock =
      stockFilter === "All Stock" ||
      (stockFilter === "In Stock" && item.quantity > item.minStock) ||
      (stockFilter === "Low Stock" && item.quantity > 0 && item.quantity <= item.minStock) ||
      (stockFilter === "Out of Stock" && item.quantity === 0)

    return matchesSearch && matchesCategory && matchesStock
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData({ ...formData, [name]: value })
  }

  const handleStockChange = (e) => {
    const { name, value } = e.target
    setStockData({ ...stockData, [name]: value })
  }

  const getStatus = (quantity, minStock) => {
    const stock = Number(quantity)
    const minimum = Number(minStock)
    if (stock === 0) return "Out of Stock"
    if (stock <= minimum) return "Low Stock"
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

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedHospital) return

    try {
      const payload = {
        name: formData.name,
        category: formData.category,
        batch: "",
        quantity: Number(formData.quantity),
        price: 0,
        expiry_date: formData.expiry
          ? `${formData.expiry.split("/")[1]}-${formData.expiry.split("/")[0]}-01`
          : null,
        hospital: selectedHospital.id,
      }

      const response = await api.pharmacy.medicines.create(payload)
      const newMed = {
        id: response.id,
        name: response.name,
        category: response.category,
        unit: "Piece",
        quantity: Number(response.quantity),
        minStock: Number(formData.minStock) || 20,
        supplier: formData.supplier,
        expiry: formData.expiry,
        status: getStatus(response.quantity, formData.minStock || 20),
        hospitalId: selectedHospital.id,
        apiId: response.id,
        batch: response.batch,
        price: Number(response.price),
      }
      setMedicines((prev) => [...prev, newMed])
      resetForm()
    } catch (err) {
      toast.error(err.message || "Failed to add medicine")
    }
  }

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

  const handleUpdate = async (e) => {
    e.preventDefault()
    if (!selectedItem) return

    try {
      const payload = {
        name: formData.name,
        category: formData.category,
        batch: selectedItem.batch || "",
        quantity: Number(formData.quantity),
        price: selectedItem.price,
        expiry_date: formData.expiry
          ? `${formData.expiry.split("/")[1]}-${formData.expiry.split("/")[0]}-01`
          : null,
      }

      const response = await api.pharmacy.medicines.update(selectedItem.apiId, payload)
      setMedicines((prev) =>
        prev.map((item) =>
          item.apiId === selectedItem.apiId
            ? {
                ...item,
                name: response.name,
                category: response.category,
                quantity: Number(response.quantity),
                minStock: Number(formData.minStock),
                supplier: formData.supplier,
                expiry: formData.expiry,
                status: getStatus(response.quantity, formData.minStock),
                batch: response.batch,
                price: Number(response.price),
              }
            : item
        )
      )
      resetForm()
    } catch (err) {
      toast.error(err.message || "Failed to update medicine")
    }
  }

  const handleDelete = async (id) => {
    const confirmed = (await confirm("Are you sure you want to delete this medicine?"))
    if (!confirmed) return

    try {
      const item = medicines.find((m) => m.id === id)
      if (item?.apiId) {
        await api.pharmacy.medicines.remove(item.apiId)
      }
      setMedicines((prev) => prev.filter((item) => item.id !== id))
    } catch (err) {
      toast.error(err.message || "Failed to delete medicine")
    }
  }

  const handleView = (item) => {
    setSelectedItem(item)
    setShowView(true)
  }

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
    setStockData({ type: "Add Stock", quantity: "", reason: "" })
    setSelectedItem(null)
    setShowStock(false)
  }

  const handleStockUpdate = async (e) => {
    e.preventDefault()
    if (!selectedItem) return

    const quantity = Number(stockData.quantity)
    if (quantity <= 0) {
      toast.warning("Quantity must be greater than 0.")
      return
    }

    setStockLoading(true)
    try {
      const adjustmentType = stockData.type === "Add Stock" ? "add" : "remove"

      if (adjustmentType === "remove" && quantity > selectedItem.quantity) {
        toast.warning(`Only ${selectedItem.quantity} ${selectedItem.unit} available.`)
        return
      }

      await api.procurement.stockTransactions.adjust({
        medicine: selectedItem.apiId,
        type: adjustmentType,
        quantity,
        reason: stockData.reason || "Manual stock update",
      })

      await fetchAllData()
      toast.warning(`${selectedItem.name} stock updated successfully.`)
      resetStock()
    } catch (err) {
      toast.error(err.message || "Failed to update stock")
    } finally {
      setStockLoading(false)
    }
  }

  const getStatusClass = (status) => {
    if (status === "In Stock") return "bg-green-100 text-green-700"
    if (status === "Low Stock") return "bg-orange-100 text-orange-700"
    return "bg-red-100 text-red-700"
  }

  return (
    <>{confirmDialog}<div>
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
        <div>
          <p className="text-blue-600 font-semibold text-sm">INVENTORY MANAGEMENT</p>
          <h1 className="text-3xl font-bold text-gray-800 mt-1">Inventory</h1>
          <p className="text-gray-500 mt-1">
            Manage supplies and stock for{" "}
            <span className="font-semibold text-gray-700">{selectedHospital.name}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setShowHistory(true)}
            className="px-5 py-3 border border-gray-300 rounded-xl font-medium hover:bg-gray-50"
          >
            <ClipboardListIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> Stock History
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

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl"><HospitalIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
          <div>
            <p className="text-xs text-gray-500">Current Hospital</p>
            <h2 className="font-bold text-gray-800">{selectedHospital.name}</h2>
            <p className="text-sm text-gray-500"><MapPinIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> {selectedHospital.address}</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-4 mb-6 flex items-center justify-between gap-4">
          <p className="text-sm"><TriangleAlertIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /> {error}</p>
          <button onClick={fetchAllData} className="px-4 py-2 bg-red-600 text-white rounded-xl text-sm font-medium hover:bg-red-700">
            Retry
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <p className="text-sm text-gray-500">Total Items</p>
          <h2 className="text-3xl font-bold text-blue-600 mt-3">{totalItems}</h2>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <p className="text-sm text-gray-500">Total Units</p>
          <h2 className="text-3xl font-bold text-green-600 mt-3">{totalQuantity}</h2>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <p className="text-sm text-gray-500">Low Stock</p>
          <h2 className="text-3xl font-bold text-orange-500 mt-3">{lowStockItems}</h2>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <p className="text-sm text-gray-500">Out of Stock</p>
          <h2 className="text-3xl font-bold text-red-600 mt-3">{outOfStockItems}</h2>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search item, ID or supplier..."
            className="hms-input"
          />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="hms-input"
          >
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          <select
            value={stockFilter}
            onChange={(e) => setStockFilter(e.target.value)}
            className="hms-input"
          >
            <option>All Stock</option>
            <option>In Stock</option>
            <option>Low Stock</option>
            <option>Out of Stock</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold text-gray-800">{selectedHospital.name} Inventory</h2>
          <p className="text-sm text-gray-500 mt-1">
            {loading
              ? "Loading medicines…"
              : `${filteredItems.length} item(s) found`}
          </p>
        </div>

        {loading && (
          <div className="p-12 text-center">
            <LoadingSpinner size="lg" />
            <p className="text-gray-500 mt-2">Loading inventory...</p>
          </div>
        )}

        {!loading && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">ID</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Item</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Category</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Unit</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Quantity</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Min Stock</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Supplier</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Status</th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="text-center py-12 text-gray-500">
                      <div className="text-4xl mb-3"><PackageIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
                      <p className="font-semibold">No inventory items found</p>
                      <p className="text-sm mt-1">No matching items in {selectedHospital.name}.</p>
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item) => (
                    <tr key={item.id} className="border-t hover:bg-gray-50">
                      <td className="px-6 py-4 font-semibold text-blue-600">{item.id}</td>
                      <td className="px-6 py-4">
                        <p className="font-semibold text-gray-800">{item.name}</p>
                        <p className="text-xs text-gray-500">
                          Batch: {item.batch || "N/A"} • Expiry: {item.expiry}
                        </p>
                      </td>
                      <td className="px-6 py-4 text-gray-600">{item.category}</td>
                      <td className="px-6 py-4 text-gray-600">{item.unit}</td>
                      <td className="px-6 py-4">
                        <span
                          className={
                            item.quantity <= item.minStock
                              ? "font-bold text-orange-600"
                              : "font-semibold"
                          }
                        >
                          {item.quantity}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-600">{item.minStock}</td>
                      <td className="px-6 py-4 text-gray-600">{item.supplier}</td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusClass(item.status)}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2 flex-wrap">
                          <button onClick={() => handleView(item)} className="px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg">View</button>
                          <button onClick={() => handleEdit(item)} className="px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg">Edit</button>
                          <button onClick={() => openStockModal(item)} className="px-3 py-2 text-sm bg-purple-50 text-purple-700 rounded-lg">Stock</button>
                          <button onClick={() => handleDelete(item.id)} className="px-3 py-2 text-sm bg-red-50 text-red-700 rounded-lg">Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <div>
                <h2 className="text-xl font-bold text-gray-800">
                  {selectedItem ? "Edit Inventory Item" : "Add Inventory Item"}
                </h2>
                <p className="text-sm text-blue-600 mt-1">{selectedHospital.name}</p>
              </div>
              <button onClick={resetForm} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={selectedItem ? handleUpdate : handleSubmit} className="p-6 space-y-4">
              <input type="text" name="name" value={formData.name} onChange={handleChange} required placeholder="Item Name" className="hms-input w-full" />
              <select name="category" value={formData.category} onChange={handleChange} required className="hms-input w-full">
                <option value="">Select Category</option>
                <option>Medical Supplies</option>
                <option>Surgical</option>
                <option>Equipment</option>
                <option>General</option>
              </select>
              <select name="unit" value={formData.unit} onChange={handleChange} required className="hms-input w-full">
                <option value="">Select Unit</option>
                <option>Piece</option>
                <option>Box</option>
                <option>Pack</option>
                <option>Bottle</option>
              </select>
              <input type="number" name="quantity" min="0" value={formData.quantity} onChange={handleChange} required placeholder="Current Quantity" className="hms-input w-full" />
              <input type="number" name="minStock" min="0" value={formData.minStock} onChange={handleChange} required placeholder="Minimum Stock Level" className="hms-input w-full" />
              <input type="text" name="supplier" value={formData.supplier} onChange={handleChange} required placeholder="Supplier Name" className="hms-input w-full" />
              <input type="month" value={formData.expiry ? formData.expiry.split("/").reverse().join("-") : ""} onChange={(e) => {
                if (!e.target.value) {
                  setFormData({ ...formData, expiry: "" })
                  return
                }
                const [year, month] = e.target.value.split("-")
                setFormData({ ...formData, expiry: `${month}/${year}` })
              }} required className="hms-input w-full" />
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={resetForm} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" className="px-5 py-3 bg-blue-600 text-white rounded-xl">{selectedItem ? "Save Changes" : "Add Item"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showStock && selectedItem && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl">
            <div className="flex justify-between items-center p-6 border-b">
              <div>
                <h2 className="text-xl font-bold">Update Stock</h2>
                <p className="text-sm text-blue-600 mt-1">{selectedHospital.name}</p>
                <p className="text-sm text-gray-500">{selectedItem.name}</p>
              </div>
              <button onClick={resetStock} className="text-2xl text-gray-500">×</button>
            </div>
            <form onSubmit={handleStockUpdate} className="p-6 space-y-5">
              <div className="bg-blue-50 rounded-xl p-4">
                <div className="flex justify-between">
                  <span>Current Stock</span>
                  <span className="font-bold">{selectedItem.quantity} {selectedItem.unit}</span>
                </div>
              </div>
              <select name="type" value={stockData.type} onChange={handleStockChange} className="hms-input w-full">
                <option>Add Stock</option>
                <option>Remove Stock</option>
              </select>
              <input type="number" name="quantity" min="1" value={stockData.quantity} onChange={handleStockChange} required placeholder="Enter quantity" className="hms-input w-full" />
              <input type="text" name="reason" value={stockData.reason} onChange={handleStockChange} placeholder="Purchase, damaged, adjustment..." className="hms-input w-full" />
              <div className="flex justify-end gap-3">
                <button type="button" onClick={resetStock} className="px-5 py-3 border border-gray-300 rounded-xl">Cancel</button>
                <button type="submit" disabled={stockLoading} className="px-5 py-3 bg-purple-600 text-white rounded-xl disabled:opacity-50">
                  {stockLoading ? "Updating..." : "Update Stock"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showView && selectedItem && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl">
            <div className="flex justify-between items-center p-6 border-b">
              <div>
                <h2 className="text-xl font-bold">Inventory Details</h2>
                <p className="text-sm text-blue-600">{selectedHospital.name}</p>
              </div>
              <button onClick={() => setShowView(false)} className="text-2xl text-gray-500">×</button>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <p className="text-sm text-gray-500">Item</p>
                <p className="text-lg font-bold">{selectedItem.name}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-xl p-4"><p className="text-xs text-gray-500">Current Stock</p><p className="text-xl font-bold mt-1">{selectedItem.quantity}</p></div>
                <div className="bg-gray-50 rounded-xl p-4"><p className="text-xs text-gray-500">Minimum Stock</p><p className="text-xl font-bold mt-1">{selectedItem.minStock}</p></div>
                <div className="bg-gray-50 rounded-xl p-4"><p className="text-xs text-gray-500">Unit</p><p className="font-semibold mt-1">{selectedItem.unit}</p></div>
                <div className="bg-gray-50 rounded-xl p-4"><p className="text-xs text-gray-500">Expiry</p><p className="font-semibold mt-1">{selectedItem.expiry}</p></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {showHistory && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-4xl rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <div>
                <h2 className="text-xl font-bold">Stock Transaction History</h2>
                <p className="text-sm text-blue-600">{selectedHospital.name}</p>
              </div>
              <button onClick={() => setShowHistory(false)} className="text-2xl text-gray-500">×</button>
            </div>
            <div className="p-6">
              {stockTransactions.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3"><ClipboardListIcon size="1em" aria-hidden="true" className="inline-block shrink-0 align-[-0.125em]" /></div>
                  <p className="font-semibold">No stock transactions found</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Date</th>
                        <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Medicine</th>
                        <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Type</th>
                        <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Quantity</th>
                        <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Reason</th>
                        <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Reference</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stockTransactions.map((tx) => (
                        <tr key={tx.id} className="border-t hover:bg-gray-50">
                          <td className="px-6 py-4 text-gray-600">{new Date(tx.created_at).toLocaleDateString("en-IN")}</td>
                          <td className="px-6 py-4 font-semibold text-gray-800">{tx.medicine_name || "Unknown"}</td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${tx.transaction_type === "IN" ? "bg-green-100 text-green-700" : tx.transaction_type === "OUT" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>{tx.transaction_type}</span>
                          </td>
                          <td className="px-6 py-4 text-gray-600">{tx.quantity}</td>
                          <td className="px-6 py-4 text-gray-600">{tx.reason || "-"}</td>
                          <td className="px-6 py-4 text-gray-600">{tx.reference || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div></>
  )
}

export default Inventory