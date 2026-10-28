// @vitest-environment node
import { describe, expect, it } from "vitest"
import { canEncode, code39Bars, NARROW, WIDE } from "../utils/code39.js"

// Reads bar/space widths back into characters using the same rules a scanner uses.
function decode({ bars }) {
  const elements = []
  bars.forEach((bar, i) => {
    elements.push(bar.width)
    const next = bars[i + 1]
    if (next) elements.push(next.x - (bar.x + bar.width))
  })
  const chars = []
  for (let i = 0; i < elements.length; i += 10) chars.push(elements.slice(i, i + 9).map((w) => (w === WIDE ? "w" : "n")).join(""))
  return chars
}

describe("Code 39", () => {
  it("frames the value with start/stop characters and puts 3 wide elements in every character", () => {
    const chars = decode(code39Bars("LAB-1"))

    expect(chars).toHaveLength(7)
    expect(chars[0]).toBe("nwnnwnwnn")
    expect(chars.at(-1)).toBe("nwnnwnwnn")
    chars.forEach((pattern) => expect([...pattern].filter((e) => e === "w")).toHaveLength(3))
  })

  it("uses the standard patterns for digits and letters", () => {
    const [, zero, one, a] = decode(code39Bars("01A"))

    expect([zero, one, a]).toEqual(["nnnwwnwnn", "wnnwnnnnw", "wnnnnwnnw"])
  })

  it("separates characters by one narrow gap and accepts lower case", () => {
    const upper = code39Bars("LAB20261028-1-000001")
    const lower = code39Bars("lab20261028-1-000001")

    expect(lower).toEqual(upper)
    expect(upper.width).toBe(22 * (3 * WIDE + 6 * NARROW) + 21 * NARROW)
  })

  it("refuses characters Code 39 cannot carry", () => {
    expect(canEncode("LAB_1")).toBe(false)
    expect(() => code39Bars("A*B")).toThrow()
  })
})
