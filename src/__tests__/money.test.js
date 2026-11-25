import { describe, expect, it } from "vitest"
import { formatRupees, fromPaise, hasBalanceDue, paymentToRecord, toPaise } from "../utils/money.js"

// BUG-002: bills with paise must be payable exactly; money is compared in
// whole paise, never with floating-point rupees.

describe("toPaise", () => {
  it.each([
    ["33.60", 3360], ["33.6", 3360], [33.6, 3360], ["100", 10000], ["0.01", 1],
    ["1,000.99", 100099], [" 250.75 ", 25075], ["0", 0], ["-10.00", -1000], [0.1 + 0.2, 30],
  ])("reads %j as %i paise", (value, paise) => {
    expect(toPaise(value)).toBe(paise)
  })

  it.each([["10.999"], ["1.001"], ["abc"], [""], ["."], ["1.2.3"], [null], [undefined], ["1e3"]])(
    "refuses %j instead of guessing",
    (value) => {
      expect(Number.isNaN(toPaise(value))).toBe(true)
    },
  )
})

describe("fromPaise / formatRupees", () => {
  it("writes exact two-decimal amounts", () => {
    expect(fromPaise(3360)).toBe("33.60")
    expect(fromPaise(1)).toBe("0.01")
    expect(fromPaise(-1000)).toBe("-10.00")
    expect(formatRupees(100099)).toBe("1,000.99")
    expect(formatRupees(3360)).toBe("33.60")
  })

  it("adds many amounts without floating-point drift", () => {
    const sum = Array.from({ length: 10 }, () => toPaise("0.10")).reduce((a, b) => a + b, 0)
    expect(fromPaise(sum)).toBe("1.00")
  })
})

describe("hasBalanceDue (TEST 12: dashboards)", () => {
  it("counts a partially paid bill, using the server's status names", () => {
    expect(hasBalanceDue({ status: "Partially Paid", balance_due: "23.35" })).toBe(true)
    expect(hasBalanceDue({ status: "Partially Paid" })).toBe(true)
    expect(hasBalanceDue({ status: "Unpaid", balance_due: "33.60" })).toBe(true)
  })

  it("does not count paid or cancelled bills, or a zero balance", () => {
    expect(hasBalanceDue({ status: "Paid", balance_due: "0.00" })).toBe(false)
    expect(hasBalanceDue({ status: "Cancelled", balance_due: "33.60" })).toBe(false)
    expect(hasBalanceDue({ status: "Partially Paid", balance_due: "0.00" })).toBe(false)
  })
})

describe("paymentToRecord", () => {
  const bill = (total, alreadyPaid = "0.00") => ({ total, alreadyPaid })

  it("pays a ₹33.60 bill in full with exactly 33.60 (TEST 1)", () => {
    expect(paymentToRecord({ ...bill("33.60"), enteredPaid: "33.60" })).toEqual({ amount: "33.60" })
  })

  it("records only the new money for a partial payment (TEST 2)", () => {
    expect(paymentToRecord({ ...bill("33.60"), enteredPaid: "10.25" })).toEqual({ amount: "10.25" })
    expect(paymentToRecord({ ...bill("33.60", "10.25"), enteredPaid: "33.60" })).toEqual({ amount: "23.35" })
  })

  it("adds up multiple payments to the paisa (TEST 3)", () => {
    expect(paymentToRecord({ ...bill("100.50", "50.50"), enteredPaid: "100.50" })).toEqual({ amount: "50.00" })
  })

  it("refuses more than the bill, even by one paisa (TEST 4)", () => {
    expect(paymentToRecord({ ...bill("33.60"), enteredPaid: "33.61" }).error).toMatch(/more than the bill/i)
  })

  it("refuses zero, negative and unchanged amounts (TEST 5, 6)", () => {
    expect(paymentToRecord({ ...bill("33.60"), enteredPaid: "0" }).error).toMatch(/greater than/i)
    expect(paymentToRecord({ ...bill("33.60"), enteredPaid: "-10.00" }).error).toMatch(/valid amount/i)
    expect(paymentToRecord({ ...bill("33.60", "10.00"), enteredPaid: "10.00" }).info).toBeTruthy()
  })

  it("refuses more than two decimal places instead of rounding (TEST 7)", () => {
    expect(paymentToRecord({ ...bill("33.60"), enteredPaid: "10.999" }).error).toMatch(/2 decimal places/i)
  })

  it("keeps whole-rupee bills working (TEST 8)", () => {
    expect(paymentToRecord({ ...bill("100.00"), enteredPaid: "100" })).toEqual({ amount: "100.00" })
  })

  it("explains that lowering the paid amount needs a refund", () => {
    expect(paymentToRecord({ ...bill("33.60", "20.00"), enteredPaid: "10.00" }).info).toMatch(/refund/i)
  })
})
