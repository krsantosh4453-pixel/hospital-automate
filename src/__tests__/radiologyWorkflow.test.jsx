import React, { act } from "react"
import { createRoot } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Prompt 5: imaging images (MF-005), order-visit links (INT-002) and the
// Radiology Staff menu (MF-004).
vi.mock("../services/api.js", () => ({
  default: {
    imaging: { images: vi.fn(), uploadImage: vi.fn(), imageBlob: vi.fn() },
    visits: { forPatient: vi.fn() },
  },
}))

import api from "../services/api.js"
import { LanguageProvider } from "../assets/context/LanguageProvider.jsx"
import StudyImages from "../components/radiology/StudyImages.jsx"
import VisitSelect from "../components/clinical/VisitSelect.jsx"
import { visibleStaffNav } from "../config/navigation.js"
import { DEFAULT_ROLES } from "../assets/context/RoleContext.jsx"

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let host
let root
const flush = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)))
const text = () => document.body.textContent

async function render(node) {
  await act(async () => root.render(<LanguageProvider>{node}</LanguageProvider>))
  await flush()
}

beforeEach(() => {
  vi.clearAllMocks()
  host = document.createElement("div")
  document.body.appendChild(host)
  root = createRoot(host)
})
afterEach(() => {
  act(() => root.unmount())
  host.remove()
})

const PERFORMED = { id: 4, status: "Performed" }

describe("StudyImages", () => {
  it("lists images and uploads a new one through the study (TEST 11)", async () => {
    api.imaging.images.mockResolvedValueOnce([]).mockResolvedValueOnce([
      { id: 9, title: "Chest PA", file_size: 2048, uploaded_at: "2026-11-24T10:00:00Z", url: "/api/laboratory/imaging/4/images/9/" }])
    api.imaging.uploadImage.mockResolvedValue({ id: 9 })
    await render(<StudyImages study={PERFORMED} canUpload />)
    expect(text()).toContain("No images attached")

    const input = document.body.querySelector("#study-image-4")
    const file = new File([new Uint8Array([137, 80, 78, 71])], "chest.png", { type: "image/png" })
    Object.defineProperty(input, "files", { value: [file] })
    await act(async () => input.dispatchEvent(new Event("change", { bubbles: true })))
    await flush()

    expect(api.imaging.uploadImage).toHaveBeenCalledWith(4, file)
    expect(text()).toContain("Chest PA")
    expect(text()).toContain("2 KB")
  })

  it("shows the server's refusal of an unsafe file", async () => {
    api.imaging.images.mockResolvedValue([])
    api.imaging.uploadImage.mockRejectedValue(new Error("Upload a PNG, JPEG, DICOM (.dcm) or PDF file."))
    await render(<StudyImages study={PERFORMED} canUpload />)
    const input = document.body.querySelector("#study-image-4")
    Object.defineProperty(input, "files", { value: [new File(["MZ"], "scan.exe")] })
    await act(async () => input.dispatchEvent(new Event("change", { bubbles: true })))
    await flush()
    expect(text()).toContain("Upload a PNG, JPEG, DICOM (.dcm) or PDF file.")
  })

  it("offers no upload on a signed study or to a role that may not upload", async () => {
    api.imaging.images.mockResolvedValue([])
    await render(<StudyImages study={{ id: 5, status: "Reported" }} canUpload />)
    expect(document.body.querySelector("#study-image-5")).toBeNull()
    expect(text()).toContain("takes no more images")
    await render(<StudyImages study={PERFORMED} canUpload={false} />)
    expect(document.body.querySelector("#study-image-4")).toBeNull()
  })
})

describe("VisitSelect", () => {
  it("lists this patient's visits and picks the open one (TEST 13)", async () => {
    api.visits.forPatient.mockResolvedValue({ results: [
      { id: 3, patient: 7, visit_type: "OPD", status: "Completed", visit_date: "2026-11-20T10:00:00Z" },
      { id: 8, patient: 7, visit_type: "OPD", status: "In Consultation", visit_date: "2026-11-24T10:00:00Z" },
      { id: 99, patient: 12, visit_type: "OPD", status: "Waiting", visit_date: "2026-11-24T10:00:00Z" },
    ] })
    const onChange = vi.fn()
    await render(<VisitSelect hospitalId={1} patientId={7} value="" onChange={onChange} />)

    expect(api.visits.forPatient).toHaveBeenCalledWith(1, 7)
    const options = [...document.body.querySelectorAll("#order-visit option")].map((o) => o.value)
    expect(options).toEqual(["", "3", "8"])
    expect(onChange).toHaveBeenCalledWith("8")
  })

  it("hides itself for a role that may not list visits", async () => {
    api.visits.forPatient.mockRejectedValue(Object.assign(new Error("Forbidden"), { status: 403 }))
    await render(<VisitSelect hospitalId={1} patientId={7} value="" onChange={vi.fn()} />)
    expect(document.body.querySelector("#order-visit")).toBeNull()
  })
})

describe("Radiology Staff menu", () => {
  const role = DEFAULT_ROLES.find((r) => r.name === "Radiology Staff")
  const canView = (module) => Boolean(role.permissions[module]?.includes("View"))

  it("shows Radiology but not the Laboratory page (TEST 10)", () => {
    const links = visibleStaffNav(canView, "Radiology Staff").flatMap((g) => g.items.map((i) => i.to))
    expect(links).toContain("/radiology")
    expect(links).not.toContain("/laboratory")
    expect(links).not.toContain("/billing")
    expect(links).not.toContain("/patients")
  })

  it("leaves Lab Staff's menu as it was", () => {
    const lab = DEFAULT_ROLES.find((r) => r.name === "Lab Staff")
    const links = visibleStaffNav((m) => Boolean(lab.permissions[m]?.includes("View")), "Lab Staff").flatMap((g) => g.items.map((i) => i.to))
    expect(links).toEqual(expect.arrayContaining(["/laboratory", "/radiology"]))
  })
})
