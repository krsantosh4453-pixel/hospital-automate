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

describe("substitutes and partial dispensing", () => {
  const shelf = [
    { id: 1, name: "Crocin 500", genericName: "Paracetamol", batch: "C1", stock: 2, expiry: "12/2027" },
    { id: 2, name: "Dolo 500", genericName: " paracetamol", batch: "D1", stock: 50, expiry: "12/2027" },
    { id: 3, name: "Brufen 400", genericName: "Ibuprofen", batch: "B1", stock: 50, expiry: "12/2027" },
  ]
  const item = { id: 9, name: "Crocin 500", quantity: 10, dispensed: 4 }

  it("offers only other brands of the same salt as substitutes", async () => {
    const { substituteBatches } = await import("../utils/dispenseBatches.js")
    expect(substituteBatches(shelf, "Crocin 500", TODAY).map((b) => b.id)).toEqual([2])
    expect(substituteBatches([{ ...shelf[0], genericName: "" }, shelf[1]], "Crocin 500", TODAY)).toEqual([])
  })

  it("starts from the remaining quantity and sends a partial request when less is given", async () => {
    const { buildDispenseRequest, defaultLines } = await import("../utils/dispenseBatches.js")
    expect(defaultLines([item], shelf, TODAY)[9].quantity).toBe(6)
    const lines = { 9: { batch: 1, quantity: 2, reason: "" } }
    expect(buildDispenseRequest(5, [item], lines, shelf)).toEqual({
      body: { prescription: 5, partial: true, lines: [{ item: 9, medicine: 1, quantity: 2 }] },
    })
  })

  it("needs a reason for a substitute and refuses more than is owed", async () => {
    const { buildDispenseRequest } = await import("../utils/dispenseBatches.js")
    const result = buildDispenseRequest(5, [item], { 9: { batch: 2, quantity: 7, reason: "" } }, shelf)
    expect(result.problems).toEqual(["Crocin 500: at most 6", "Crocin 500: give the reason for the substitute"])
  })
})
