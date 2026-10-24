import {
  createContext,
  useContext,
  useState,
  useCallback,
} from "react"

import api from "../../services/api.js"

const PharmacyContext = createContext(null)

const num = (value) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const formatDate = (value) => {
  if (!value) return ""
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleDateString("en-IN")
}

const formatExpiry = (value) => {
  if (!value) return ""
  const parts = String(value).split("-")
  if (parts.length < 2) return value
  const [year, month] = parts
  return `${month}/${year}`
}

const mapMedicineFromApi = (record = {}) => {
  const stock = num(record.quantity)
  return {
    id: record.id,
    apiId: record.id,
    name: record.name || "",
    category: record.category || "",
    batch: record.batch || "",
    stock,
    expiry: formatExpiry(record.expiry_date),
    price: num(record.price),
    status: stock <= 20 ? "Low Stock" : "In Stock",
    hospitalId: record.hospital,
  }
}

const mapSaleFromApi = (record = {}) => ({
  id: `SALE${String(record.id).padStart(3, "0")}`,
  apiId: record.id,
  medicineId: record.medicine,
  medicineName: record.medicine_name || "",
  patient: record.patient_name || "",
  quantity: num(record.quantity),
  price: num(record.unit_price),
  total: num(record.total),
  date: formatDate(record.created_at),
  hospitalId: record.hospital,
  prescriptionId: record.prescription ?? null,
})

const mapSupplierFromApi = (record = {}) => ({
  id: record.id,
  name: record.name || "",
  contactPerson: record.contact_person || "",
  phone: record.phone || "",
  email: record.email || "",
  address: record.address || "",
  hospitalId: record.hospital,
  isActive: record.is_active,
  createdAt: record.created_at,
})

const mapPurchaseFromApi = (record = {}) => ({
  id: record.id,
  reference: record.reference || "",
  supplierId: record.supplier,
  supplierName: record.supplier_name || "",
  hospitalId: record.hospital,
  purchaseDate: record.purchase_date,
  status: record.status,
  createdAt: record.created_at,
  items: record.items || [],
})

const mapGRNFromApi = (record = {}) => ({
  id: record.id,
  reference: record.reference || "",
  purchaseId: record.purchase,
  purchaseReference: record.purchase_reference || "",
  supplierId: record.supplier,
  supplierName: record.supplier_name || "",
  hospitalId: record.hospital,
  receiptDate: record.receipt_date,
  receivedBy: record.received_by || "",
  note: record.note || "",
  createdAt: record.created_at,
  items: record.items || [],
})

const mapStockTransactionFromApi = (record = {}) => ({
  id: record.id,
  medicineId: record.medicine,
  medicineName: record.medicine_name || "",
  hospitalId: record.hospital,
  type: record.transaction_type,
  quantity: num(record.quantity),
  reason: record.reason || "",
  reference: record.reference || "",
  date: formatDate(record.created_at),
})

export function PharmacyProvider({ children }) {
  const [sales, setSales] = useState([])
  const [medicines, setMedicines] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [purchaseOrders, setPurchaseOrders] = useState([])
  const [grns, setGrns] = useState([])
  const [stockTransactions, setStockTransactions] = useState([])

  const addSale = useCallback((sale) => {
    const newSale = {
      ...sale,
      id: sale.id || `SALE-${Date.now()}`,
      createdAt: new Date().toLocaleDateString("en-IN"),
    }
    setSales((prev) => [newSale, ...prev])
    return newSale
  }, [])

  const getHospitalSales = useCallback(
    (hospitalId) => {
      if (!hospitalId) return []
      return sales.filter((sale) => sale.hospitalId === hospitalId)
    },
    [sales]
  )

  const getPrescriptionSales = useCallback(
    (prescriptionId, hospitalId) => {
      if (!prescriptionId || !hospitalId) return []
      return sales.filter(
        (sale) =>
          sale.prescriptionId === prescriptionId && sale.hospitalId === hospitalId
      )
    },
    [sales]
  )

  const getPrescriptionTotal = useCallback(
    (prescriptionId, hospitalId) => {
      const prescriptionSales = getPrescriptionSales(prescriptionId, hospitalId)
      return prescriptionSales.reduce(
        (total, sale) => total + Number(sale.total || 0),
        0
      )
    },
    [getPrescriptionSales]
  )

  const loadMedicines = useCallback(async (hospitalId) => {
    if (!hospitalId) return []
    const response = await api.pharmacy.medicines.list(hospitalId)
    const records = response?.results || response || []
    const mapped = records.map(mapMedicineFromApi)
    setMedicines((prev) => [
      ...mapped,
      ...prev.filter((medicine) => medicine.hospitalId !== hospitalId),
    ])
    return mapped
  }, [])

  const createMedicine = useCallback(async (payload) => {
    const response = await api.pharmacy.medicines.create(payload)
    const created = mapMedicineFromApi(response)
    setMedicines((prev) => [created, ...prev])
    return created
  }, [])

  const updateMedicine = useCallback(async (id, payload) => {
    const response = await api.pharmacy.medicines.update(id, payload)
    const updated = mapMedicineFromApi(response)
    setMedicines((prev) =>
      prev.map((medicine) =>
        String(medicine.id) === String(id) ? updated : medicine
      )
    )
    return updated
  }, [])

  const deleteMedicine = useCallback(async (id) => {
    await api.pharmacy.medicines.remove(id)
    setMedicines((prev) =>
      prev.filter((medicine) => String(medicine.id) !== String(id))
    )
    return true
  }, [])

  const loadSales = useCallback(async (hospitalId) => {
    if (!hospitalId) return []
    const response = await api.pharmacy.sales.list(hospitalId)
    const records = response?.results || response || []
    const mapped = records.map(mapSaleFromApi)
    setSales((prev) => [
      ...mapped,
      ...prev.filter((sale) => sale.hospitalId !== hospitalId),
    ])
    return mapped
  }, [])

  const createSale = useCallback(async (payload) => {
    const response = await api.pharmacy.sales.create(payload)
    const created = mapSaleFromApi(response)
    setSales((prev) => [created, ...prev])
    return created
  }, [])

  // =====================================
  // PROCUREMENT APIs
  // =====================================

  const loadSuppliers = useCallback(async (hospitalId) => {
    if (!hospitalId) return []
    const response = await api.procurement.suppliers.list(hospitalId)
    const records = response?.results || response || []
    const mapped = records.map(mapSupplierFromApi)
    setSuppliers((prev) => [
      ...mapped,
      ...prev.filter((s) => s.hospitalId !== hospitalId),
    ])
    return mapped
  }, [])

  const createSupplier = useCallback(async (payload) => {
    const response = await api.procurement.suppliers.create(payload)
    const created = mapSupplierFromApi(response)
    setSuppliers((prev) => [created, ...prev])
    return created
  }, [])

  const updateSupplier = useCallback(async (id, payload) => {
    const response = await api.procurement.suppliers.update(id, payload)
    const updated = mapSupplierFromApi(response)
    setSuppliers((prev) =>
      prev.map((s) => (String(s.id) === String(id) ? updated : s))
    )
    return updated
  }, [])

  const deleteSupplier = useCallback(async (id) => {
    await api.procurement.suppliers.delete(id)
    setSuppliers((prev) => prev.filter((s) => String(s.id) !== String(id)))
    return true
  }, [])

  const loadPurchases = useCallback(async (hospitalId) => {
    if (!hospitalId) return []
    const response = await api.procurement.purchases.list(hospitalId)
    const records = response?.results || response || []
    const mapped = records.map(mapPurchaseFromApi)
    setPurchaseOrders((prev) => [
      ...mapped,
      ...prev.filter((p) => p.hospitalId !== hospitalId),
    ])
    return mapped
  }, [])

  const createPurchase = useCallback(async (payload) => {
    const response = await api.procurement.purchases.create(payload)
    const created = mapPurchaseFromApi(response)
    setPurchaseOrders((prev) => [created, ...prev])
    return created
  }, [])

  const receivePurchase = useCallback(async (purchaseId, payload) => {
    const response = await api.procurement.purchases.receive(purchaseId, payload)
    return response
  }, [])

  const loadGRNs = useCallback(async (hospitalId, purchaseId) => {
    if (!hospitalId) return []
    const response = await api.procurement.grns.list(hospitalId, purchaseId)
    const records = response?.results || response || []
    const mapped = records.map(mapGRNFromApi)
    setGrns((prev) => [
      ...mapped,
      ...prev.filter((g) => g.hospitalId !== hospitalId),
    ])
    return mapped
  }, [])

  const loadStockTransactions = useCallback(
    async (hospitalId, medicineId) => {
      if (!hospitalId) return []
      const response = await api.procurement.stockTransactions.list(
        hospitalId,
        medicineId
      )
      const records = response?.results || response || []
      const mapped = records.map(mapStockTransactionFromApi)
      setStockTransactions((prev) => [
        ...mapped,
        ...prev.filter((t) => t.hospitalId !== hospitalId),
      ])
      return mapped
    },
    []
  )

  const adjustStock = useCallback(async (payload) => {
    const response = await api.procurement.stockTransactions.adjust(payload)
    return response
  }, [])

  return (
    <PharmacyContext.Provider
      value={{
        sales,
        addSale,
        getHospitalSales,
        getPrescriptionSales,
        getPrescriptionTotal,
        medicines,
        loadMedicines,
        createMedicine,
        updateMedicine,
        deleteMedicine,
        loadSales,
        createSale,
        suppliers,
        loadSuppliers,
        createSupplier,
        updateSupplier,
        deleteSupplier,
        purchaseOrders,
        loadPurchases,
        createPurchase,
        receivePurchase,
        grns,
        loadGRNs,
        stockTransactions,
        loadStockTransactions,
        adjustStock,
      }}
    >
      {children}
    </PharmacyContext.Provider>
  )
}

export function usePharmacy() {
  const context = useContext(PharmacyContext)
  if (!context) {
    throw new Error("usePharmacy must be used inside PharmacyProvider")
  }
  return context
}