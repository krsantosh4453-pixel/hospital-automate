import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, describe, expect, it, vi } from "vitest"

// MF-007: suggestions come from the hospital's lists; a list that cannot be
// read offers nothing and never breaks the form. Synthetic data only.
vi.mock("../services/api.js", () => ({
  default: {
    billing: { priceList: { catalogue: vi.fn() } },
    pharmacy: { medicines: { formulary: vi.fn() } },
  },
}))

import api from "../services/api.js"
import { useOrderingCatalogue } from "../hooks/useOrderingCatalogue.js"

globalThis.IS_REACT_ACT_ENVIRONMENT = true
let root
let host
let seen
function Probe({ hospitalId, options }) {
  seen = useOrderingCatalogue(hospitalId, options)
  return null
}
async function render(props) {
  host = document.createElement("div")
  root = createRoot(host)
  await act(async () => root.render(<Probe {...props} />))
  await act(() => new Promise((resolve) => setTimeout(resolve, 0)))
}
afterEach(() => {
  act(() => root.unmount())
  vi.clearAllMocks()
})

describe("useOrderingCatalogue", () => {
  it("reads only the lists asked for, for the hospital given", async () => {
    api.billing.priceList.catalogue.mockResolvedValue([{ name: "Complete Blood Count", category: "laboratory" }])

    await render({ hospitalId: 4, options: { services: true } })

    expect(api.billing.priceList.catalogue).toHaveBeenCalledWith(4)
    expect(api.pharmacy.medicines.formulary).not.toHaveBeenCalled()
    expect(seen.services).toEqual([{ name: "Complete Blood Count", category: "laboratory" }])
    expect(seen.medicines).toEqual([])
  })

  it("offers nothing when a list is refused", async () => {
    api.pharmacy.medicines.formulary.mockRejectedValue(new Error("403"))

    await render({ hospitalId: 4, options: { medicines: true } })

    expect(seen.medicines).toEqual([])
  })

  it("asks nothing without a hospital", async () => {
    await render({ hospitalId: null, options: { services: true, medicines: true } })

    expect(api.billing.priceList.catalogue).not.toHaveBeenCalled()
    expect(api.pharmacy.medicines.formulary).not.toHaveBeenCalled()
  })
})
