import { useState, useMemo, useEffect, useCallback } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import api from "../services/api.js"
import { Boxes, ClipboardList, Eye, History, Hospital, Package, PackageMinus, PackageX, Pencil, Plus, Trash2 } from "lucide-react"
import { useToast } from "../components/Toast.jsx"
import {
  Alert,
  Button,
  Card,
  DescriptionList,
  EmptyState,
  Field,
  Input,
  Modal,
  PageHeader,
  SearchInput,
  Select,
  SkeletonRows,
  StatTile,
  StatusBadge,
  TableWrap,
  Toolbar,
  useConfirm,
} from "../components/ui"

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
      <>{confirmDialog}<div className="space-y-5">
        <PageHeader title="Inventory" breadcrumbs={[{ label: "Home", to: "/" }, { label: "Inventory" }]} />
        <Card><EmptyState icon={Hospital} title="Select a hospital" description="Choose a hospital in the header to view its stock." /></Card>
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
      toast.success(`${selectedItem.name} stock updated successfully.`)
      resetStock()
    } catch (err) {
      toast.error(err.message || "Failed to update stock")
    } finally {
      setStockLoading(false)
    }
  }

  const LOW_STOCK_AT = 20

  const openNew = () => {
    setSelectedItem(null)
    setFormData({ name: "", category: "", unit: "", quantity: "", minStock: "", supplier: "", expiry: "" })
    setShowForm(true)
  }

  // <input type="month"> works with YYYY-MM; the page stores MM/YYYY.
  const monthValue = formData.expiry && formData.expiry.includes("/") ? formData.expiry.split("/").reverse().join("-") : ""
  const setMonth = (e) => {
    if (!e.target.value) {
      setFormData({ ...formData, expiry: "" })
      return
    }
    const [year, month] = e.target.value.split("-")
    setFormData({ ...formData, expiry: `${month}/${year}` })
  }

  return (
    <>{confirmDialog}<div className="space-y-5">
      <PageHeader
        title="Inventory"
        description={`Stock levels for ${selectedHospital.name}.`}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Inventory" }]}
        actions={
          <>
            <Button variant="secondary" icon={History} onClick={() => setShowHistory(true)}>Stock history</Button>
            <Button icon={Plus} onClick={openNew}>Add item</Button>
          </>
        }
      />

      {error && (
        <Alert tone="danger" action={<Button size="sm" variant="secondary" onClick={fetchAllData}>Retry</Button>}>
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatTile icon={Package} label="Items" value={loading ? null : totalItems} onClick={() => setStockFilter("All Stock")} />
        <StatTile icon={Boxes} tone="success" label="Units in stock" value={loading ? null : totalQuantity.toLocaleString("en-IN")} />
        <StatTile icon={PackageMinus} tone="warning" label="Low stock" hint={`${LOW_STOCK_AT} units or fewer`} value={loading ? null : lowStockItems} onClick={() => setStockFilter("Low Stock")} />
        <StatTile icon={PackageX} tone="danger" label="Out of stock" value={loading ? null : outOfStockItems} onClick={() => setStockFilter("Out of Stock")} />
      </div>

      <Card className="overflow-hidden">
        <Toolbar actions={<span className="text-[13px] text-ink-500">{loading ? "Loading…" : `${filteredItems.length} of ${totalItems} items`}</span>}>
          <SearchInput value={search} onChange={setSearch} placeholder="Item name or ID" label="Search inventory" className="w-full sm:max-w-xs" />
          <Select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} aria-label="Filter by category" className="w-full sm:w-48">
            {categories.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
          </Select>
          <Select value={stockFilter} onChange={(e) => setStockFilter(e.target.value)} aria-label="Filter by stock level" className="w-full sm:w-40">
            <option>All Stock</option>
            <option>In Stock</option>
            <option>Low Stock</option>
            <option>Out of Stock</option>
          </Select>
        </Toolbar>

        {loading ? (
          <SkeletonRows rows={6} />
        ) : filteredItems.length === 0 ? (
          <EmptyState
            icon={Package}
            title={totalItems ? "No items match these filters" : "No inventory items yet"}
            action={!totalItems && <Button icon={Plus} onClick={openNew}>Add item</Button>}
          />
        ) : (
          <TableWrap>
            <table className="hms-table">
              <caption className="sr-only">Inventory at {selectedHospital.name}</caption>
              <thead>
                <tr>
                  <th scope="col">Item</th>
                  <th scope="col">Category</th>
                  <th scope="col">Batch</th>
                  <th scope="col">Expiry</th>
                  <th scope="col" className="num">In stock</th>
                  <th scope="col">Status</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <span className="block font-medium text-ink-900">{item.name}</span>
                      <span className="block text-xs text-ink-500 tabular-nums">ID {item.id}</span>
                    </td>
                    <td className="text-ink-600">{item.category}</td>
                    <td className="tabular-nums text-ink-600">{item.batch || "—"}</td>
                    <td className="tabular-nums text-ink-600">{item.expiry}</td>
                    <td className={`num font-semibold ${item.quantity === 0 ? "text-red-700" : item.quantity <= LOW_STOCK_AT ? "text-amber-700" : "text-ink-900"}`}>{item.quantity}</td>
                    <td><StatusBadge status={item.status} /></td>
                    <td>
                      <div className="flex items-center justify-end gap-1">
                        <Button size="sm" variant="subtle" icon={Boxes} onClick={() => openStockModal(item)}>Adjust</Button>
                        <Button variant="ghost" size="icon-sm" icon={Eye} onClick={() => handleView(item)} aria-label={`View ${item.name}`} title="View" />
                        <Button variant="ghost" size="icon-sm" icon={Pencil} onClick={() => handleEdit(item)} aria-label={`Edit ${item.name}`} title="Edit" />
                        <Button variant="danger-ghost" size="icon-sm" icon={Trash2} onClick={() => handleDelete(item.id)} aria-label={`Delete ${item.name}`} title="Delete" />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Card>

      {/* Add / edit item */}
      <Modal
        open={showForm}
        onClose={resetForm}
        title={selectedItem ? `Edit ${selectedItem.name}` : "Add inventory item"}
        footer={
          <>
            <Button variant="secondary" onClick={resetForm}>Cancel</Button>
            <Button type="submit" form="inventory-form">{selectedItem ? "Save changes" : "Add item"}</Button>
          </>
        }
      >
        <form id="inventory-form" onSubmit={selectedItem ? handleUpdate : handleSubmit} className="space-y-4">
          <Field label="Item name" required>
            <Input name="name" value={formData.name} onChange={handleChange} />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Category" required>
              <Select name="category" value={formData.category} onChange={handleChange}>
                <option value="">Select category</option>
                {["Medical Supplies", "Surgical", "Equipment", "General"].map((c) => <option key={c}>{c}</option>)}
                {formData.category && !["Medical Supplies", "Surgical", "Equipment", "General"].includes(formData.category) && <option>{formData.category}</option>}
              </Select>
            </Field>
            <Field label="Quantity in stock" required>
              <Input type="number" min="0" inputMode="numeric" name="quantity" value={formData.quantity} onChange={handleChange} />
            </Field>
            <Field label="Expiry (month)" required className="sm:col-span-2">
              <Input type="month" value={monthValue} onChange={setMonth} />
            </Field>
          </div>
          <p className="text-xs text-ink-500">
            Items at {LOW_STOCK_AT} units or fewer are flagged as low stock. Use “Adjust” on the list to receive or remove stock with a reason; that keeps the stock ledger.
          </p>
        </form>
      </Modal>

      {/* Adjust stock */}
      <Modal
        open={showStock && Boolean(selectedItem)}
        onClose={resetStock}
        title="Adjust stock"
        description={selectedItem?.name}
        footer={
          <>
            <Button variant="secondary" onClick={resetStock}>Cancel</Button>
            <Button type="submit" form="stock-form" loading={stockLoading}>Save adjustment</Button>
          </>
        }
      >
        {selectedItem && (
          <form id="stock-form" onSubmit={handleStockUpdate} className="space-y-4">
            <div className="flex items-center justify-between rounded-xl bg-ink-50 px-4 py-3 text-sm">
              <span className="text-ink-600">Current stock</span>
              <span className="text-lg font-semibold text-ink-900 tabular-nums">{selectedItem.quantity}</span>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Adjustment">
                <Select name="type" value={stockData.type} onChange={handleStockChange}>
                  <option>Add Stock</option>
                  <option>Remove Stock</option>
                </Select>
              </Field>
              <Field label="Quantity" required>
                <Input type="number" min="1" inputMode="numeric" name="quantity" value={stockData.quantity} onChange={handleStockChange} />
              </Field>
            </div>
            <Field label="Reason" hint="e.g. purchase received, damaged, count correction">
              <Input name="reason" value={stockData.reason} onChange={handleStockChange} />
            </Field>
          </form>
        )}
      </Modal>

      {/* Details */}
      <Modal open={showView && Boolean(selectedItem)} onClose={() => setShowView(false)} title="Inventory item" description={selectedItem?.name}>
        {selectedItem && (
          <DescriptionList
            items={[
              { label: "In stock", value: selectedItem.quantity },
              { label: "Status", value: selectedItem.status },
              { label: "Category", value: selectedItem.category },
              { label: "Batch", value: selectedItem.batch },
              { label: "Expiry", value: selectedItem.expiry },
              { label: "Item ID", value: selectedItem.id },
            ]}
          />
        )}
      </Modal>

      {/* Stock history */}
      <Modal open={showHistory} onClose={() => setShowHistory(false)} size="xl" title="Stock history" description={selectedHospital.name}>
        {stockTransactions.length === 0 ? (
          <EmptyState compact icon={ClipboardList} title="No stock movements recorded yet" />
        ) : (
          <TableWrap className="-mx-5 -my-4">
            <table className="hms-table">
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Item</th>
                  <th scope="col">Type</th>
                  <th scope="col" className="num">Qty</th>
                  <th scope="col">Reason</th>
                  <th scope="col">Reference</th>
                </tr>
              </thead>
              <tbody>
                {stockTransactions.map((tx) => (
                  <tr key={tx.id}>
                    <td className="whitespace-nowrap tabular-nums text-ink-600">{new Date(tx.created_at).toLocaleDateString("en-IN")}</td>
                    <td className="font-medium text-ink-900">{tx.medicine_name || "Unknown item"}</td>
                    <td><StatusBadge status={tx.transaction_type === "IN" ? "received" : tx.transaction_type === "OUT" ? "dispensed" : "pending"} label={tx.transaction_type} /></td>
                    <td className="num">{tx.quantity}</td>
                    <td className="text-ink-600">{tx.reason || "—"}</td>
                    <td className="text-ink-600">{tx.reference || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Modal>
    </div></>
  )
}

export default Inventory
