// @vitest-environment node
import { describe, expect, it } from "vitest"
import { defaultBatches, missingBatches, usableBatches } from "../utils/dispenseBatches.js"

const TODAY = new Date(2026, 10, 3)

const stock = [
  { id: 1, name: "Paracetamol", batch: "P-LATE", stock: 100, expiry: "12/2027" },
  { id: 2, name: "paracetamol ", batch: "P-SOON", stock: 5, expiry: "01/2027" },
  { id: 3, name: "Paracetamol", batch: "P-OLD", stock: 50, expiry: "09/2026" },
  { id: 4, name: "Amoxicillin", batch: "A1", stock: 20, expiry: "" },
]

describe("usableBatches", () => {
  it("lists unexpired batches of the same medicine, earliest expiry first", () => {
    const batches = usableBatches(stock, "PARACETAMOL", TODAY)

    expect(batches.map((b) => b.batch)).toEqual(["P-SOON", "P-LATE"])
  })

  it("keeps batches with no expiry, after dated ones", () => {
    expect(usableBatches(stock, "Amoxicillin", TODAY).map((b) => b.id)).toEqual([4])
  })
})

describe("defaultBatches", () => {
  it("picks the earliest-expiring batch that covers the prescribed quantity", () => {
    const items = [
      { id: 10, name: "Paracetamol", quantity: 10 },
      { id: 11, name: "Amoxicillin", quantity: 5 },
    ]

    expect(defaultBatches(items, stock, TODAY)).toEqual({ 10: 1, 11: 4 })
  })

  it("leaves a medicine unselected when no batch has enough stock", () => {
    const items = [{ id: 12, name: "Amoxicillin", quantity: 500 }]

    expect(defaultBatches(items, stock, TODAY)).toEqual({ 12: "" })
  })
})

describe("missingBatches", () => {
  it("names the medicines that still need a batch", () => {
    const items = [
      { id: 10, name: "Paracetamol", quantity: 10 },
      { id: 11, name: "Amoxicillin", quantity: 5 },
    ]

    expect(missingBatches(items, { 10: 1, 11: "" })).toEqual(["Amoxicillin"])
  })
})
