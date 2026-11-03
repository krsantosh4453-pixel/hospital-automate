import { useState, useMemo, useEffect, useCallback } from "react"
import { usePatient } from "../assets/context/PatientContext.jsx"
import { useRole } from "../assets/context/RoleContext.jsx"
import SuppliersPanel from "../components/inventory/SuppliersPanel.jsx"
import PurchaseOrdersPanel from "../components/inventory/PurchaseOrdersPanel.jsx"
import api from "../services/api.js"
import { Boxes, ClipboardList, Eye, History, Hospital, Package, PackageMinus, PackageX, Pencil, Plus, Trash2, Truck } from "lucide-react"
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
  Tabs,
  Toolbar,
  useConfirm,
} from "../components/ui"
import { useLanguage } from "../assets/context/LanguageContext.jsx"

const STORE_ROLES = ["Admin", "Hospital Manager", "Inventory Staff"]
// Matches the Medicine.reorder_level default on the server.
const DEFAULT_REORDER_LEVEL = 10

function stockStatus(quantity, reorderLevel) {
  const stock = Number(quantity || 0)
  if (stock === 0) return "Out of Stock"
  if (stock <= Number(reorderLevel)) return "Low Stock"
  return "In Stock"
}

/** "MM/YYYY" from the month picker to the first day of that month, or null. */
function expiryDate(monthYear) {
  if (!monthYear) return null
  const [month, year] = monthYear.split("/")
  return `${year}-${month}-01`
}

/** The store settings the item form edits: unit, reorder level and usual supplier. */
function storeSettings(form) {
  return {
    unit: (form.unit || "").trim() || "Unit",
    generic_name: (form.genericName || "").trim(),
    reorder_level: Math.max(0, Number(form.minStock) || 0),
    supplier: form.supplier ? Number(form.supplier) : null,
  }
}

function Inventory() {
  const { t } = useLanguage()
  const toast = useToast()
  const [confirm, confirmDialog] = useConfirm()

  const { selectedHospital } = usePatient()
  const { activeRoleName } = useRole()
  // Only the store changes procurement (procurement/views.py RequiresHospitalScope); pharmacy staff read it.
  const canManageStore = STORE_ROLES.includes(activeRoleName)
  const [tab, setTab] = useState("stock")

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
        unit: m.unit || "Unit",
        genericName: m.generic_name || "",
        quantity: Number(m.quantity || 0),
        minStock: Number(m.reorder_level ?? DEFAULT_REORDER_LEVEL),
        supplier: m.supplier_name || "",
        supplierId: m.supplier || "",
        expiry: m.expiry_date
          ? new Date(m.expiry_date).toLocaleDateString("en-IN", {
              month: "2-digit",
              year: "numeric",
            })
          : "N/A",
        status: stockStatus(m.quantity, m.reorder_level ?? DEFAULT_REORDER_LEVEL),
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
        <PageHeader title={t("Inventory")} breadcrumbs={[{ label: "Home", to: "/" }, { label: "Inventory" }]} />
        <Card><EmptyState icon={Hospital} title={t("Select a hospital")} description="Choose a hospital in the header to view its stock." /></Card>
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
      await api.pharmacy.medicines.create({
        name: formData.name,
        category: formData.category,
        batch: "",
        quantity: Number(formData.quantity),
        price: 0,
        expiry_date: expiryDate(formData.expiry),
        hospital: selectedHospital.id,
        ...storeSettings(formData),
      })
      resetForm()
      await fetchAllData()
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
      supplier: item.supplierId ? String(item.supplierId) : "",
      genericName: item.genericName,
      expiry: item.expiry,
    })
    setShowForm(true)
  }

  const handleUpdate = async (e) => {
    e.preventDefault()
    if (!selectedItem) return

    try {
      await api.pharmacy.medicines.update(selectedItem.apiId, {
        name: formData.name,
        category: formData.category,
        batch: selectedItem.batch || "",
        quantity: Number(formData.quantity),
        price: selectedItem.price,
        expiry_date: expiryDate(formData.expiry),
        ...storeSettings(formData),
      })
      resetForm()
      await fetchAllData()
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
      toast.success(t("{name} stock updated successfully.", { name: selectedItem.name }))
      resetStock()
    } catch (err) {
      toast.error(err.message || "Failed to update stock")
    } finally {
      setStockLoading(false)
    }
  }

  const openNew = () => {
    setSelectedItem(null)
    setFormData({ name: "", category: "", unit: "Unit", quantity: "", minStock: String(DEFAULT_REORDER_LEVEL), supplier: "", genericName: "", expiry: "" })
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
        title={t("Inventory")}
        description={t("Stock levels for {hospital}.", { hospital: selectedHospital.name })}
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Inventory" }]}
        actions={
          <>
            <Button variant="secondary" icon={History} onClick={() => setShowHistory(true)}>{t("Stock history")}</Button>
            <Button icon={Plus} onClick={openNew}>{t("Add item")}</Button>
          </>
        }
      />

      {error && (
        <Alert tone="danger" action={<Button size="sm" variant="secondary" onClick={fetchAllData}>{t("Retry")}</Button>}>
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatTile icon={Package} label="Items" value={loading ? null : totalItems} onClick={() => setStockFilter("All Stock")} />
        <StatTile icon={Boxes} tone="success" label="Units in stock" value={loading ? null : totalQuantity.toLocaleString("en-IN")} />
        <StatTile icon={PackageMinus} tone="warning" label="Low stock" hint="At or below the item's reorder level" value={loading ? null : lowStockItems} onClick={() => setStockFilter("Low Stock")} />
        <StatTile icon={PackageX} tone="danger" label="Out of stock" value={loading ? null : outOfStockItems} onClick={() => setStockFilter("Out of Stock")} />
      </div>

      <Tabs
        label="Inventory sections"
        value={tab}
        onChange={setTab}
        tabs={[
          { id: "stock", label: "Stock", icon: Package },
          { id: "suppliers", label: "Suppliers", icon: Truck, count: suppliers.length },
          { id: "purchases", label: "Purchase orders", icon: ClipboardList, count: purchaseOrders.length },
        ]}
      />

      {tab === "stock" && (
      <Card className="overflow-hidden">
        <Toolbar actions={<span className="text-[13px] text-ink-500">{loading ? t("Loading…") : t("{shown} of {total} items", { shown: filteredItems.length, total: totalItems })}</span>}>
          <SearchInput value={search} onChange={setSearch} placeholder={t("Item name or ID")} label="Search inventory" className="w-full sm:max-w-xs" />
          <Select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} aria-label={t("Filter by category")} className="w-full sm:w-48">
            {categories.map((cat) => <option key={cat} value={cat}>{t(cat)}</option>)}
          </Select>
          <Select value={stockFilter} onChange={(e) => setStockFilter(e.target.value)} aria-label={t("Filter by stock level")} className="w-full sm:w-40">
            <option value="All Stock">{t("All Stock")}</option>
            <option value="In Stock">{t("In Stock")}</option>
            <option value="Low Stock">{t("Low Stock")}</option>
            <option value="Out of Stock">{t("Out of Stock")}</option>
          </Select>
        </Toolbar>

        {loading ? (
          <SkeletonRows rows={6} />
        ) : filteredItems.length === 0 ? (
          <EmptyState
            icon={Package}
            title={totalItems ? t("No items match these filters") : t("No inventory items yet")}
            action={!totalItems && <Button icon={Plus} onClick={openNew}>{t("Add item")}</Button>}
          />
        ) : (
          <TableWrap>
            <table className="hms-table">
              <caption className="sr-only">{t("Inventory at")}{" "}{selectedHospital.name}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("Item")}</th>
                  <th scope="col">{t("Category")}</th>
                  <th scope="col">{t("Batch")}</th>
                  <th scope="col">{t("Expiry")}</th>
                  <th scope="col">{t("Supplier")}</th>
                  <th scope="col" className="num">{t("In stock")}</th>
                  <th scope="col" className="num">{t("Reorder at")}</th>
                  <th scope="col">{t("Status")}</th>
                  <th scope="col"><span className="sr-only">{t("Actions")}</span></th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <span className="block font-medium text-ink-900">{item.name}</span>
                      <span className="block text-xs text-ink-500 tabular-nums">{t("ID")}{" "}{item.id}</span>
                    </td>
                    <td className="text-ink-600">{item.category}</td>
                    <td className="tabular-nums text-ink-600">{item.batch || "—"}</td>
                    <td className="tabular-nums text-ink-600">{item.expiry}</td>
                    <td className="text-ink-600">{item.supplier || "—"}</td>
                    <td className={`num font-semibold ${item.quantity === 0 ? "text-red-700" : item.quantity <= item.minStock ? "text-amber-700" : "text-ink-900"}`}>
                      {item.quantity} <span className="text-xs font-normal text-ink-500">{item.unit}</span>
                    </td>
                    <td className="num text-ink-600">{item.minStock}</td>
                    <td><StatusBadge status={item.status} /></td>
                    <td>
                      <div className="flex items-center justify-end gap-1">
                        <Button size="sm" variant="subtle" icon={Boxes} onClick={() => openStockModal(item)}>{t("Adjust")}</Button>
                        <Button variant="ghost" size="icon-sm" icon={Eye} onClick={() => handleView(item)} aria-label={`View ${item.name}`} title={t("View")} />
                        <Button variant="ghost" size="icon-sm" icon={Pencil} onClick={() => handleEdit(item)} aria-label={`Edit ${item.name}`} title={t("Edit")} />
                        <Button variant="danger-ghost" size="icon-sm" icon={Trash2} onClick={() => handleDelete(item.id)} aria-label={`Delete ${item.name}`} title={t("Delete")} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Card>
      )}

      {tab === "suppliers" && (
        <Card className="overflow-hidden">
          {loading ? <SkeletonRows rows={4} /> : (
            <SuppliersPanel hospital={selectedHospital} suppliers={suppliers} canEdit={canManageStore} onChanged={fetchAllData} />
          )}
        </Card>
      )}

      {tab === "purchases" && (
        <Card className="overflow-hidden">
          {loading ? <SkeletonRows rows={4} /> : (
            <PurchaseOrdersPanel
              hospital={selectedHospital}
              orders={purchaseOrders}
              suppliers={suppliers}
              medicines={hospitalItems}
              canEdit={canManageStore}
              onChanged={fetchAllData}
            />
          )}
        </Card>
      )}

      {/* Add / edit item */}
      <Modal
        open={showForm}
        onClose={resetForm}
        title={selectedItem ? `Edit ${selectedItem.name}` : t("Add inventory item")}
        footer={
          <>
            <Button variant="secondary" onClick={resetForm}>{t("Cancel")}</Button>
            <Button type="submit" form="inventory-form">{selectedItem ? t("Save changes") : t("Add item")}</Button>
          </>
        }
      >
        <form id="inventory-form" onSubmit={selectedItem ? handleUpdate : handleSubmit} className="space-y-4">
          <Field label="Item name" required>
            <Input name="name" value={formData.name} onChange={handleChange} />
          </Field>
          <Field label="Salt (generic name)" hint="e.g. ibuprofen, or paracetamol, caffeine for a combination. Used by the prescription safety check.">
            <Input name="genericName" value={formData.genericName || ""} onChange={handleChange} />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Category" required>
              <Select name="category" value={formData.category} onChange={handleChange}>
                <option value="">{t("Select category")}</option>
                {["Medical Supplies", "Surgical", "Equipment", "General"].map((c) => <option value={c} key={c}>{t(c)}</option>)}
                {formData.category && !["Medical Supplies", "Surgical", "Equipment", "General"].includes(formData.category) && <option>{formData.category}</option>}
              </Select>
            </Field>
            <Field label="Quantity in stock" required>
              <Input type="number" min="0" inputMode="numeric" name="quantity" value={formData.quantity} onChange={handleChange} />
            </Field>
            <Field label="Unit" hint="e.g. Tablet, Box, Bottle, Piece">
              <Input name="unit" value={formData.unit} onChange={handleChange} />
            </Field>
            <Field label="Reorder level" hint="Flagged as low stock at or below this">
              <Input type="number" min="0" inputMode="numeric" name="minStock" value={formData.minStock} onChange={handleChange} />
            </Field>
            <Field label="Usual supplier">
              <Select name="supplier" value={formData.supplier} onChange={handleChange}>
                <option value="">{t("None")}</option>
                {suppliers.filter((s) => s.is_active || String(s.id) === formData.supplier).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </Field>
            <Field label="Expiry (month)" required>
              <Input type="month" value={monthValue} onChange={setMonth} />
            </Field>
          </div>
          <p className="text-xs text-ink-500">
            {t("Use “Adjust” on the list to add or remove stock with a reason, or receive a purchase order; both keep the stock ledger.")}
          </p>
        </form>
      </Modal>

      {/* Adjust stock */}
      <Modal
        open={showStock && Boolean(selectedItem)}
        onClose={resetStock}
        title={t("Adjust stock")}
        description={selectedItem?.name}
        footer={
          <>
            <Button variant="secondary" onClick={resetStock}>{t("Cancel")}</Button>
            <Button type="submit" form="stock-form" loading={stockLoading}>{t("Save adjustment")}</Button>
          </>
        }
      >
        {selectedItem && (
          <form id="stock-form" onSubmit={handleStockUpdate} className="space-y-4">
            <div className="flex items-center justify-between rounded-xl bg-ink-50 px-4 py-3 text-sm">
              <span className="text-ink-600">{t("Current stock")}</span>
              <span className="text-lg font-semibold text-ink-900 tabular-nums">{selectedItem.quantity}</span>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Adjustment">
                <Select name="type" value={stockData.type} onChange={handleStockChange}>
                  <option value="Add Stock">{t("Add Stock")}</option>
                  <option value="Remove Stock">{t("Remove Stock")}</option>
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
      <Modal open={showView && Boolean(selectedItem)} onClose={() => setShowView(false)} title={t("Inventory item")} description={selectedItem?.name}>
        {selectedItem && (
          <DescriptionList
            items={[
              { label: "In stock", value: `${selectedItem.quantity} ${selectedItem.unit}` },
              { label: "Reorder level", value: selectedItem.minStock },
              { label: "Usual supplier", value: selectedItem.supplier || "—" },
              { label: "Salt (generic name)", value: selectedItem.genericName || "—" },
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
      <Modal open={showHistory} onClose={() => setShowHistory(false)} size="xl" title={t("Stock history")} description={selectedHospital.name}>
        {stockTransactions.length === 0 ? (
          <EmptyState compact icon={ClipboardList} title={t("No stock movements recorded yet")} />
        ) : (
          <TableWrap className="-mx-5 -my-4">
            <table className="hms-table">
              <thead>
                <tr>
                  <th scope="col">{t("Date")}</th>
                  <th scope="col">{t("Item")}</th>
                  <th scope="col">{t("Type")}</th>
                  <th scope="col" className="num">{t("Qty")}</th>
                  <th scope="col">{t("Reason")}</th>
                  <th scope="col">{t("Reference")}</th>
                </tr>
              </thead>
              <tbody>
                {stockTransactions.map((tx) => (
                  <tr key={tx.id}>
                    <td className="whitespace-nowrap tabular-nums text-ink-600">{new Date(tx.created_at).toLocaleDateString("en-IN")}</td>
                    <td className="font-medium text-ink-900">{tx.medicine_name || t("Unknown item")}</td>
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
