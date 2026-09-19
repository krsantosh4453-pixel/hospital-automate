import {
  createContext,
  useContext,
  useState,
} from "react"

import api from "../../services/api.js"

const PharmacyContext =
  createContext(null)


// =====================================
// HELPERS
// =====================================

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


export function PharmacyProvider({
  children,
}) {

  const [sales, setSales] =
    useState([])

  const [medicines, setMedicines] =
    useState([])


  // =====================================
  // ADD PHARMACY SALE
  // =====================================

  const addSale = (sale) => {

    const newSale = {

      ...sale,

      id:
        sale.id ||
        `SALE-${Date.now()}`,

      createdAt:
        new Date().toLocaleDateString(
          "en-IN"
        ),

    }


    setSales((prev) => [
      newSale,
      ...prev,
    ])


    return newSale
  }


  // =====================================
  // GET HOSPITAL SALES
  // =====================================

  const getHospitalSales = (
    hospitalId
  ) => {

    if (!hospitalId) {
      return []
    }


    return sales.filter(
      (sale) =>
        sale.hospitalId ===
        hospitalId
    )
  }


  // =====================================
  // GET PRESCRIPTION SALES
  // =====================================

  const getPrescriptionSales = (
    prescriptionId,
    hospitalId
  ) => {

    if (
      !prescriptionId ||
      !hospitalId
    ) {

      return []

    }


    return sales.filter(
      (sale) =>
        sale.prescriptionId ===
        prescriptionId &&
        sale.hospitalId ===
        hospitalId
    )
  }


  // =====================================
  // CALCULATE PRESCRIPTION TOTAL
  // =====================================

  const getPrescriptionTotal = (
    prescriptionId,
    hospitalId
  ) => {

    const prescriptionSales =
      getPrescriptionSales(
        prescriptionId,
        hospitalId
      )


    return prescriptionSales.reduce(
      (
        total,
        sale
      ) =>
        total +
        Number(
          sale.total || 0
        ),

      0
    )
  }


  // =====================================
  // LOAD MEDICINES FROM API
  // =====================================

  const loadMedicines = async (
    hospitalId
  ) => {

    if (!hospitalId) {
      return []
    }


    const response =
      await api.pharmacy.medicines.list(
        hospitalId
      )

    const records =
      response?.results ||
      response ||
      []

    const mapped =
      records.map(
        mapMedicineFromApi
      )


    setMedicines((prev) => [
      ...mapped,
      ...prev.filter(
        (medicine) =>
          medicine.hospitalId !==
          hospitalId
      ),
    ])


    return mapped
  }


  // =====================================
  // CREATE MEDICINE
  // =====================================

  const createMedicine = async (
    payload
  ) => {

    const response =
      await api.pharmacy.medicines.create(
        payload
      )

    const created =
      mapMedicineFromApi(response)


    setMedicines((prev) => [
      created,
      ...prev,
    ])


    return created
  }


  // =====================================
  // UPDATE MEDICINE
  // =====================================

  const updateMedicine = async (
    id,
    payload
  ) => {

    const response =
      await api.pharmacy.medicines.update(
        id,
        payload
      )

    const updated =
      mapMedicineFromApi(response)


    setMedicines((prev) =>
      prev.map((medicine) =>
        String(medicine.id) ===
          String(id)
          ? updated
          : medicine
      )
    )


    return updated
  }


  // =====================================
  // DELETE MEDICINE
  // =====================================

  const deleteMedicine = async (
    id
  ) => {

    await api.pharmacy.medicines.remove(
      id
    )


    setMedicines((prev) =>
      prev.filter(
        (medicine) =>
          String(medicine.id) !==
          String(id)
      )
    )


    return true
  }


  // =====================================
  // LOAD SALES FROM API
  // =====================================

  const loadSales = async (
    hospitalId
  ) => {

    if (!hospitalId) {
      return []
    }


    const response =
      await api.pharmacy.sales.list(
        hospitalId
      )

    const records =
      response?.results ||
      response ||
      []

    const mapped =
      records.map(mapSaleFromApi)


    setSales((prev) => [
      ...mapped,
      ...prev.filter(
        (sale) =>
          sale.hospitalId !==
          hospitalId
      ),
    ])


    return mapped
  }


  // =====================================
  // CREATE SALE (VIA API)
  // =====================================

  const createSale = async (
    payload
  ) => {

    const response =
      await api.pharmacy.sales.create(
        payload
      )

    const created =
      mapSaleFromApi(response)


    setSales((prev) => [
      created,
      ...prev,
    ])


    return created
  }


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

      }}
    >

      {children}

    </PharmacyContext.Provider>

  )
}


// =====================================
// CUSTOM HOOK
// =====================================

export function usePharmacy() {

  const context =
    useContext(
      PharmacyContext
    )


  if (!context) {

    throw new Error(
      "usePharmacy must be used inside PharmacyProvider"
    )

  }


  return context
}